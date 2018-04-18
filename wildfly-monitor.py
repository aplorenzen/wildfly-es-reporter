from datetime import datetime
import signal
import logging
import time
import requests
from requests.auth import HTTPDigestAuth
import os
import sys
from elasticsearch import Elasticsearch

monitorName = os.getenv("MONITOR_NAME", "wildfly-monitor")

# From: https://docs.python.org/3/howto/logging-cookbook.html
logger = logging.getLogger(monitorName)
logLevelString = os.getenv('LOG_LEVEL', 'INFO')

logLevel = logging.getLevelName(logLevelString)

if logLevel is None:
    logLevel = logging.INFO

logger.setLevel(logLevel)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)

scriptStartTime = time.time()
lastBeanNameUpdateTime = 0
# Set last stats reports time to be 5 minutes in the future
lastRequestStatsReportTime = 0  # time.time()


# Retrieve the environment variables that should be set to configure the Wildfly endpoint to monitor
wildflyProtocol = os.getenv('WILDFLY_PROTOCOL', 'http')
wildflyHost = os.getenv('WILDFLY_HOST', 'localhost')
wildflyPort = os.getenv('WILDFLY_PORT', '9990')
wildflyDeployment = os.getenv('WILDFLY_DEPLOYMENT', 'etel.ear')
wildflySubDeployment = os.getenv('WILDFLY_SUBDEPLOYMENT', 'etel-ejb-1.0-SNAPSHOT.jar')
wildflyUser = os.getenv('WILDFLY_USER', 'etel')
wildflyPassword = os.getenv('WILDFLY_PASS', 'etel')

# Compose the target Wildfly mangement HTTP endpoint that we are targeting
wildflyHostUrl = (wildflyProtocol + '://' +
                  wildflyHost + ':' +
                  wildflyPort)

wildflyBaseUrl = (wildflyHostUrl +
                  '/management/deployment/' + wildflyDeployment +
                  '/subdeployment/' + wildflySubDeployment)

# Retrieve the environment variables that should be set to configure the Elasticsearch endpoint we are reporting to
esProtocol = os.getenv('ES_PROTOCOL', 'http')
esHost = os.getenv('ES_HOST', 'localhost')
esPort = os.getenv('ES_PORT', '9200')
esIndex = os.getenv('ES_INDEX', 'etel')
esDocType = os.getenv('ES_DOCTYPE', 'stats')

# Compose the target Wildfly mangement HTTP endpoint that we are targeting
esHostUrl = (esProtocol + '://' +
             esHost + ':' +
             esPort)

# Initiate the elasticsearch client
esClient = Elasticsearch(hosts=[{'host': esHost, 'port': esPort}])

# Initiate a dictionary for holding the names of the beans that we will monitor	
beanMonitors = dict()

# Define how long the monitor should sleep, if it has some type of connection issue
errorSleepTime = 20

# Set up global request counters
wildflyRequestCounter = 0
esRequestCounter = 0


# Set up method to handle exit signal
def sigint_handler(signal, frame):
    logger.info("Received SIGINT, exiting. Signal: {0} Frame: {1}".format(signal, frame))
    sys.exit(0)


def sigterm_handler(signal, frame):
    logger.info("Received SIGTERM, exiting. Signal: {0} Frame: {1}".format(signal, frame))
    sys.exit(0)


def timestampMillisec64():
    return int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000)


# BeanMonitor is the class that we will use for holding information about a bean
#   that we are monitoring.
class BeanMonitor(object):
    def __init__(self, beanName):
        self.beanName = beanName
        self.executionTime = 0
        self.invocationCount = 0
        self.invocationsSinceLastSample = 0
        self.executionTimeSinceLastSample = 0
        self.invocationsDelta = 0
        self.executionsDelta = 0
        self.lastSampleTime = 0

    def getExecutionTime(self):
        return self.executionTime

    def setExecutionTime(self, value):
        self.executionTime = value;

    def getInvocationCount(self):
        return self.invocationCount

    def setInvocationCount(self, value):
        self.invocationCount = value

    def getBeanName(self):
        return self.beanName

    def getLastSampleTime(self):
        return self.lastSampleTime

    def getInvocationsSinceLastSample(self):
        return self.invocationsSinceLastSample

    def getExecutionTimeSinceLastSample(self):
        return self.executionTimeSinceLastSample

    def getInvocationsPrSecond(self):
        return self.invocationsDelta

    def getExecutionsPrSecond(self):
        return self.executionsDelta

    def updateStats(self, responseJson):
        currentTimeInMilli = timestampMillisec64()

        # int(round(time.time() * 1000))

        if self.lastSampleTime == 0:
            self.lastSampleTime = currentTimeInMilli

        deltaTime = currentTimeInMilli - self.lastSampleTime
        logger.debug("Bean {0}, deltaTime: {1}".format(self.beanName, deltaTime))

        logger.debug("Bean {0}, self.invocationCount: {1}".format(self.beanName, self.invocationCount))
        logger.debug("Bean {0}, responseJson[\"invocations\"]: {1}".format(self.beanName, responseJson["invocations"]))
        self.invocationsSinceLastSample = responseJson["invocations"] - self.invocationCount
        logger.debug("Bean {0}, invocationsSinceLastSample: {1}".format(self.beanName, self.invocationsSinceLastSample))

        logger.debug("Bean {0}, self.executionTime: {1}".format(self.beanName, self.executionTime))
        logger.debug(
            "Bean {0}, responseJson[\"execution-time\"]: {1}".format(self.beanName, responseJson["execution-time"]))
        self.executionTimeSinceLastSample = responseJson["execution-time"] - self.executionTime
        logger.debug(
            "Bean {0}, executionTimeSinceLastSample: {1}".format(self.beanName, self.executionTimeSinceLastSample))

        if deltaTime > 0:
            self.invocationsDelta = self.invocationsSinceLastSample / (deltaTime / 1000)
            logger.debug("Bean {0}, invocationsDelta: {1}".format(self.beanName, self.invocationsDelta))
            self.executionsDelta = self.executionTimeSinceLastSample / (deltaTime / 1000)
            logger.debug("Bean {0}, executionsDelta: {1}".format(self.beanName, self.executionsDelta))
        else:
            self.invocationsDelta = 0
            self.executionsDelta = 0

        self.lastSampleTime = currentTimeInMilli


def updateBeanNames(beanMonitors):
    global wildflyRequestCounter

    url = (wildflyBaseUrl +
           "/subsystem/ejb3/stateless-session-bean/")

    logger.info("Updating all bean names")

    try:
        logger.debug("Requesting all beans from {0}".format(url))
        response = requests.get(url, auth=HTTPDigestAuth(wildflyUser, wildflyPassword))
        logger.debug("Received response from {0}: {1}".format(url, response))

        wildflyRequestCounter += 1

        responseJson = response.json()
        logger.debug("Response json: {1}".format(url, responseJson))
        beanNames = responseJson['stateless-session-bean'].keys()

        logger.info("Found {0} beans to monitor".format(len(beanNames)))

        for key in beanNames:
            if key not in beanMonitors.keys():
                beanMonitors[key] = BeanMonitor(key)

    except ConnectionError as conError:
        logger.error("A ConnectionError occurred when connecting to the host {0}".format(wildflyHostUrl))
        logger.info("Sleeping {0}...".format(errorSleepTime))
        logger.error("The error: ", conError)
        time.sleep(errorSleepTime)
    except Exception as exception:
        logger.error("An error occurred when retrieving the beans to monitor from the host {0}".format(wildflyHostUrl))
        logger.info("Sleeping {0}...".format(errorSleepTime))
        logger.error("The exception: ", exception)
        time.sleep(errorSleepTime)


def updateBeanStatistics(beanMonitor):
    global wildflyRequestCounter

    logger.debug("Getting statistics for the bean {0}".format(beanMonitor.getBeanName()))
    url = (wildflyBaseUrl +
           "/subsystem/ejb3/stateless-session-bean/{0}/read-resource?include-runtime=true&recursive=true"
           .format(beanMonitor.getBeanName()))

    try:
        logger.debug("Requesting bean statistics from {0}".format(url))
        response = requests.get(url, auth=HTTPDigestAuth(wildflyUser, wildflyPassword))
        logger.debug("Received response from {0}: {1}".format(url, response))

        wildflyRequestCounter += 1

        responseJson = response.json()
        logger.debug("Response json: {1}".format(url, responseJson))

        beanMonitor.updateStats(responseJson)

        # TODO: Need to add method level logging here, think of a good solution

    except ConnectionError as conError:
        logger.error(
            "A ConnectionError occurred when getting bean statistics for {0}, connecting to the host {1}".format(
                beanMonitor.getBeanName(), wildflyHostUrl))
        logger.info("Sleeping {0}...".format(errorSleepTime))
        logger.error("The error: ", conError)
        time.sleep(errorSleepTime)
    except Exception as exception:
        logger.error(
            "An error occurred when retrieving bean statistics for the bean {0}, from the wildfly host {1}".format(
                beanMonitor.getBeanName(), wildflyHostUrl))
        logger.info("Sleeping {0}...".format(errorSleepTime))
        logger.error("The exception: ", exception)
        time.sleep(errorSleepTime)


def dispatchStatisticsToElasticSearch(beanMonitor):
    global esRequestCounter

    logger.debug("Sending statistics for the bean {0}".format(beanMonitor.getBeanName()))

    try:
        doc = {
            'beanName': beanMonitor.getBeanName(),
            'invocations': beanMonitor.getInvocationCount(),
            'invocations-since-last-sample': beanMonitor.getInvocationsSinceLastSample(),
            'invocations-pr-second': beanMonitor.getInvocationsPrSecond(),
            'execution-time': beanMonitor.getExecutionTime(),
            'execution-time-since-last-sample': beanMonitor.getExecutionTimeSinceLastSample(),
            'executions-pr-second': beanMonitor.getExecutionsPrSecond(),
            'sample-time': int(beanMonitor.getLastSampleTime()),
            'time': datetime.utcnow().isoformat(" ", "milliseconds"),
        }

        logger.info("Dispaching document to elasticsearch: {0}".format(doc))

        res = esClient.index(index=esIndex, doc_type=esDocType, body=doc)
        logger.debug("Received response from elasticsearch: {0}".format(res))

        esRequestCounter += 1

    except ConnectionError as conError:
        logger.error("A ConnectionError occurred when connecting to the elasticsearch host {0}".format(esHostUrl))
        logger.info("Sleeping {0}...".format(errorSleepTime))
        logger.error("The error: ", conError)
        time.sleep(errorSleepTime)
    except Exception as exception:
        logger.error("An error occurred when pushing statistics to elasticsearch at {0}".format(esHostUrl))
        logger.info("Sleeping {0}...".format(errorSleepTime))
        logger.error("The exception: ", exception)
        time.sleep(errorSleepTime)


def updateDeploymentUpStatus():
    global wildflyRequestCounter

    logger.debug("Getting server upstatus from {0}".format(wildflyBaseUrl))
    url = (wildflyBaseUrl +
           '/management/deployment/' + wildflyDeployment +
           "/read-attribute?name=status")

    try:
        logger.debug("Requesting deployment upstatus from {0}".format(url))
        response = requests.get(url, auth=HTTPDigestAuth(wildflyUser, wildflyPassword))
        logger.debug("Received response from {0}: {1}".format(url, response))

        wildflyRequestCounter += 1

        responseJson = response.json()
        logger.debug("Response json: {1}".format(url, responseJson))

        # TODO: Store the result somewhere before dispatching to ES
    except ConnectionError as conError:
        logger.error("A ConnectionError occurred when connecting to the wildfly host {0}".format(wildflyHostUrl))
        logger.info("Sleeping {0}...".format(errorSleepTime))
        logger.error("The error: ", conError)
        time.sleep(errorSleepTime)
    except Exception as exception:
        logger.error("An error occurred when retrieving the beans to monitor from the host {0}".format(wildflyHostUrl))
        logger.info("Sleeping {0}...".format(errorSleepTime))
        logger.error("The exception: ", exception)
        time.sleep(errorSleepTime)


def printRequestStatistics():
    global lastRequestStatsReportTime

    wildflyRequestAverage = (wildflyRequestCounter / (time.time() - scriptStartTime))
    esRequestAverage = (esRequestCounter / (time.time() - scriptStartTime))

    logger.info("Request stats: Processed a total of {0} wildfly requests, average {1:.3f} pr. second"
                .format(wildflyRequestCounter, wildflyRequestAverage))
    logger.info("Request stats: Processed a total of {0} elasticsearch requests, average {1:.3f} pr. second"
                .format(esRequestCounter, esRequestAverage))

    lastRequestStatsReportTime = time.time()


def getMinutesAndSecondsDiff(startTime, endTime):
    minutes = divmod(endTime - startTime, 60)
    seconds = divmod(minutes[1], 1)
    return "{0:.0f} minutes and {1:.0f} seconds".format(minutes[0], seconds[0])


def getUptime():
    days = divmod(time.time() - scriptStartTime, 86400)
    hours = divmod(days[1], 3600)
    minutes = divmod(hours[1], 60)
    seconds = divmod(minutes[1], 1)
    return "{0:.0f} days, {1:.0f} hours, {2:.0f} minutes and {3:.0f} seconds".format(days[0], hours[0], minutes[0],
                                                                                     seconds[0])


def logUptimeStatistics():
    logger.info("Uptime is {0}".format(getUptime()))


def waitForWildflyToBeUp():
    wildflyUp = False

    url = (wildflyHostUrl +
           "/management/deployment/" + wildflyDeployment +
           "/read-attribute?name=status")
           # http: // localhost:9990 / management / deployment / etel.ear / read-attribute?name=status
    while not wildflyUp:
        try:
            logger.info("Waiting for wildfly instance at {0} to be available".format(wildflyHostUrl))
            logger.debug("Requesting status from {0}".format(url))

            response = requests.get(url, auth=HTTPDigestAuth(wildflyUser, wildflyPassword))

            if response.status_code == requests.codes.ok:
                wildflyUp = True
                logger.info("Wildfly instance at {0} is ready".format(wildflyHostUrl))

            if not wildflyUp:
                logger.debug("Was not able to reach the wildfly instance at {0}, napping for 2 seconds...".format(url))
                time.sleep(2)

        except Exception as exception:
            logger.error("Unable to reach wildfly instance at {0}".format(wildflyHostUrl))


def waitForElasticsearchToBeUp():
    elasticsearchUp = False

    while not elasticsearchUp:
        try:
            logger.info("Waiting for elasticseach instance at {0} to be available".format(esHostUrl))

            logger.debug("Checking if elasticseach at {0} is available".format(esHostUrl))

            if esClient.ping:
                elasticsearchUp = True
                logger.info("Elasticsearch instance at {0} is ready".format(esHostUrl))

            if not elasticsearchUp:
                logger.debug("Was not able to reach the elasticsearch instance at {0}, napping for 2 seconds...".format(esHostUrl))
                time.sleep(2)

        except Exception as exception:
            logger.error("Unable to reach wildfly instance at {0}".format(esHostUrl))


# Start the main script here
logger.info("Starting monitoring of {0}".format(wildflyHostUrl))
logger.info("Shipping statistics to {0}".format(esHostUrl))

if __name__ == "__main__":
    # Hook up the exit signal handlers for SIGTERM and SIGINT
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigint_handler)

    # Need to check that the wildfly instance and elasticsearch instances are available
    waitForWildflyToBeUp()
    waitForElasticsearchToBeUp()

    try:
        while True:

            # Update bean names every hour, in case of a deploy with new beans
            if (time.time() - lastBeanNameUpdateTime) > 3600:
                updateBeanNames(beanMonitors)
                lastBeanNameUpdateTime = time.time()

            logger.info("Running bean statistics collection and dispatch for {0} beans".format(len(beanMonitors)))

            beanStatisticsCollectionStartTime = time.time()

            # Pull the bean status some stats
            # TODO, handle the scenario where the ejb3 stats logging is not enabled on wildfly
            for value in beanMonitors.values():
                # Update the statistics for the bean
                updateBeanStatistics(value)
                # Dispatch the stats to elasticsearch for the bean
                dispatchStatisticsToElasticSearch(value)
                # Take a powernap, before doing the next bean poll
                time.sleep(0.1)

            logger.info("Collected statistics for {0} beans in {1}".format(len(beanMonitors), getMinutesAndSecondsDiff(
                beanStatisticsCollectionStartTime, time.time())))

            # Report request stats every 5 minutes
            if (time.time() - lastRequestStatsReportTime) > 300:
                printRequestStatistics()

            # Take a nap before doing the next full poll cycle
            time.sleep(5)

    except KeyboardInterrupt:
        logger.info("Script interrupted by keyboard, exiting...")
        sys.exit(0)
    except Exception as exception:
        logger.info("Exception in the main loop, exiting...")
        logger.error("The exception: ", exception)
        sys.exit(0)
    finally:
        scriptEndTime = time.time()
        logger.info("Exiting...")
        logger.info("Uptime was {0}".format(getUptime()))
