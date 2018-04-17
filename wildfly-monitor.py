from datetime import datetime
import signal
import logging
import time
import requests
from requests.auth import HTTPDigestAuth
import os
import sys
from elasticsearch import Elasticsearch

# From: https://docs.python.org/3/howto/logging-cookbook.html
logger = logging.getLogger('wildfly-monitor')
logger.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)

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

esClient = Elasticsearch(hosts=[{'host': esHost, 'port': esPort}])

# Initiate a dictionary for holding the names of the beans that we will monitor	
beanMonitors = dict()


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


def updateBeanNames():
    global beanMonitors

    logger.info('Updating all bean names')
    url = (wildflyBaseUrl +
           '/subsystem/ejb3/stateless-session-bean/')
    try:
        response = requests.get(url, auth=HTTPDigestAuth(wildflyUser, wildflyPassword))
        responseJson = response.json()
        beanNames = responseJson['stateless-session-bean'].keys()

        logger.info("Found %d beans to monitor" % (len(beanNames)))

        for key in beanNames:
            if key not in beanMonitors.keys():
                beanMonitors[key] = BeanMonitor(key)

    except ConnectionError as conError:
        logger.error("A ConnectionError occurred when connecting to the host %s" % wildflyHostUrl)
        logger.error("The error: ", conError)
    except Exception as exception:
        logger.error("An error occurred when retrieving the beans to monitor from the host %s" % wildflyHostUrl)
        logger.error("The exception: ", exception)


def updateBeanStatistics(beanMonitor):
    logger.info("Getting statistics for the bean %s" % beanMonitor.getBeanName())
    url = (wildflyBaseUrl +
           "/subsystem/ejb3/stateless-session-bean/%s/read-resource?include-runtime=true&recursive=true"
           % beanMonitor.getBeanName())

    try:
        logger.debug("Requesting bean statistics from {0}".format(url))
        response = requests.get(url, auth=HTTPDigestAuth(wildflyUser, wildflyPassword))
        logger.debug("Received response from {0}: {1}".format(url, response))
        responseJson = response.json()
        logger.debug("Response json: {1}".format(url, responseJson))

        beanMonitor.updateStats(responseJson)

        # TODO: Need to add method level logging here, think of a good solution

    except ConnectionError as conError:
        logger.error("A ConnectionError occurred when connecting to the host %s" % wildflyHostUrl)
        logger.error("The error: ", conError)
    except Exception as exception:
        logger.error("An error occurred when retrieving the beans to monitor from the host %s" % wildflyHostUrl)
        logger.error("The exception: ", exception)


def dispatchStatisticsToElasticSearch(beanMonitor):
    logger.info("Sending statistics for the bean %s to elasticsearch" % beanMonitor.getBeanName())

    doc = {
        'beanName': beanMonitor.getBeanName(),
        'invocations': beanMonitor.getInvocationCount(),
        'invocations-since-last-sample': beanMonitor.getInvocationsSinceLastSample(),
        'invocations-pr-second': beanMonitor.getInvocationsPrSecond(),
        'execution-time': beanMonitor.getExecutionTime(),
        'execution-time-since-last-sample': beanMonitor.getExecutionTimeSinceLastSample(),
        'executions-pr-second': beanMonitor.getExecutionsPrSecond(),
        'sample-time': int(beanMonitor.getLastSampleTime()),
        'timestamp': timestampMillisec64(),
    }

    logger.debug("Dispaching document to elasticsearch: {0}".format(doc))

    res = esClient.index(index=esIndex, doc_type=esDocType, body=doc)
    logger.debug("Received response from elasticsearch: {0}".format(res))

# Start the main script here
logger.info("Starting monitoring of %s" % wildflyHostUrl)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sigterm_handler)
    # Hook up the exit signal handler
    signal.signal(signal.SIGINT, sigint_handler)

    try:
        while True:
            updateBeanNames()

            # Pull the bean status some stats
            # TODO, handle the scenario where the ejb3 stats logging is not enabled on wildfly
            for value in beanMonitors.values():
                # Update the statistics for the bean
                updateBeanStatistics(value)
                # Dispatch the stats to elasticsearch for the bean
                dispatchStatisticsToElasticSearch(value)

            # Take a nap
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Script interrupted by keyboard, exiting...")
        sys.exit(0)
    finally:
        logger.info("Exiting...")

