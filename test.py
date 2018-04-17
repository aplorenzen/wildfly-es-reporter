import signal
import logging
import time
import requests
from requests.auth import HTTPDigestAuth
import os
import sys

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

# Retrieve the environment variables that should be set to configure the monitor
targetProtocol = os.getenv('WILDFLY_PROTOCOL', 'http')
targetHost = os.getenv('WILDFLY_HOST', 'localhost')
targetPort = os.getenv('WILDFLY_PORT', '9990')
targetDeployment = os.getenv('WILDFLY_DEPLOYMENT', 'test.ear')
targetSubDeployment = os.getenv('WILDFLY_SUBDEPLOYMENT', 'test-1.0-SNAPSHOT.jar')
targetUser = os.getenv('WILDFLY_USER', 'user')
targetPassword = os.getenv('WILDFLY_PASS', 'password')

# Compose the target Wildfly mangement HTTP endpoint that we are targetting
targetHostUrl = (targetProtocol + '://' +
                 targetHost + ':' +
                 targetPort)

targetBaseUrl = (targetHostUrl +
                 '/management/deployment/' + targetDeployment +
                 '/subdeployment/' + targetSubDeployment)

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


def updateBeanNames():
    global beanMonitors

    logger.info('Updating all bean names')
    url = (targetBaseUrl +
           '/subsystem/ejb3/stateless-session-bean/')
    try:
        response = requests.get(url, auth=HTTPDigestAuth('etel', 'etel'))
        responseJson = response.json()
        beanNames = responseJson['stateless-session-bean'].keys()

        logger.info("Found %d beans to monitor" % (len(beanNames)))

        for key in beanNames:
            if key not in beanMonitors.keys():
                beanMonitors[key] = BeanMonitor(key)

    except ConnectionError as conError:
        logger.error("Found %d beans to monitor" % (len(beanNames)))
        logger.error("The error: ", conError)
    except Exception as exception:
        logger.error("An error occurred when retrieving the beans to monitor from the host %s" % (targetHostUrl))
        logger.error("The exception: ", exception)


# Start the main script here
logger.info("Starting monitoring of %s" % (targetHostUrl))

try:
    while True:
        updateBeanNames()




        time.sleep(10)
except KeyboardInterrupt:
    logger.info("Script interrupted by keyboard, exiting...")
    sys.exit(0)




# for value in beanMonitors.values():
#    print(value.getExecutionTime())
