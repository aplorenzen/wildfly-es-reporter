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
def signal_handler(signal, frame):
    logger.info("Received SIGINT, exiting gracefully...")
    sys.exit(0)

# Hook up the exit signal handler
signal.signal(signal.SIGINT, signal_handler)


# BeanMonitor is the class that we will use for holding information about a bean
#   that we are monitoring.
class BeanMonitor(object):
    def __init__(self, beanName):
        self.beanName = beanName
        self.executionTime = 0
        self.invocationCount = 0

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
        response = requests.get(url, auth=HTTPDigestAuth(wildflyUser, wildflyPassword))
        responseJson = response.json()

        logger.debug("Setting executionTime on %s monitor to %s" %
                     (beanMonitor.getBeanName(), responseJson["execution-time"]))
        beanMonitor.setExecutionTime(responseJson["execution-time"])

        logger.debug("Setting invocationCount on %s monitor to %s" %
                     (beanMonitor.getBeanName(), responseJson["invocations"]))
        beanMonitor.setInvocationCount(responseJson["invocations"])

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
        'author': 'kimchy',
        'text': 'Elasticsearch: cool. bonsai cool.',
        'timestamp': datetime.now(),
    }

    res = esClient.index(index=esIndex, doc_type=esDocType, body=doc)
    print(res)


# Start the main script here
logger.info("Starting monitoring of %s" % wildflyHostUrl)

try:
    while True:
        updateBeanNames()

        # Pull the bean status some stats
        # TODO, handle the scenario where the ejb3 stats logging is not enabled on wildfly
        for value in beanMonitors.values():
            updateBeanStatistics(value)
            dispatchStatisticsToElasticSearch(value)



        # print(value.getExecutionTime())

        # report the stats


        time.sleep(10)
except KeyboardInterrupt:
    logger.info("Script interrupted by keyboard, exiting...")
    sys.exit(0)




# for value in beanMonitors.values():
#    print(value.getExecutionTime())
