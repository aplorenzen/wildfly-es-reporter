import requests
from requests.auth import HTTPDigestAuth
import os
import sys

# Retrieve the environment variables that should be set to configure the monitor
targetHost = os.getenv('WILDFLY_HOST', 'localhost')
targetPort = os.getenv('WILDFLY_PORT', '9990')
targetDeployment = os.getenv('WILDFLY_DEPLOYMENT', 'etel.ear')
targetSubDeployment = os.getenv('WILDFLY_SUBDEPLOYMENT', 'etel-ejb-1.0-SNAPSHOT.jar')
targetUser = os.getenv('WILDFLY_USER', 'etel')
targetPassword = os.getenv('WILDFLY_PASS', 'etel')

# Compose the target Wildfly mangement HTTP endpoint that we are targetting
targetBaseUrl = ('http://' +
	targetHost + ':' +
	targetPort +
	'/management/deployment/' + targetDeployment +
	'/subdeployment/' + targetSubDeployment)

# Initiate a dictionary for holding the names of the beans that we will monitor	
beanMonitors = dict()

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
    print('Getting all bean names')
    url = (targetBaseUrl + 
        '/subsystem/ejb3/stateless-session-bean/')
    response = requests.get(url, auth=HTTPDigestAuth('etel', 'etel'))
    responseJson = response.json()
    beanNames = responseJson['stateless-session-bean'].keys()
    return beanNames


print('Starting monitoring')

try:
    beanNames = getBeanNames()
except ConnectionError:
    print('An error occurred when establishing a connection to... ')
except:
    print('An error occurred when retrieving the beans to monitor from the host: ...')
    sys.exit(1)

# print(beanNames)

print("Found %d beans to monitor" % (len(beanNames)))



for key in beanNames:
    beanMonitors[key] = BeanMonitor(key)

print(beanMonitors)
	
for value in beanMonitors.values():
    
	print(value.getExecutionTime())





