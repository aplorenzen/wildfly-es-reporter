import os
import json
import logging

reportRawJson = os.getenv("REPORT_RAW", False)


class Monitor(object):
    def __init__(self, name, loggerName="wmon"):
        self.logger = logging.getLogger(loggerName + "." + name)

        self._name = name
        self._executionTime = 0
        self._invocationCount = 0
        self._waitTime = 0
        self._lastSampleTime = 0

        self._invocationsSinceLastSample = 0
        self._executionTimeSinceLastSample = 0
        self._waitTimeSinceLastSample = 0
        self._invocationsPerSecond = 0
        self._executionTimePerSecond = 0
        self._waitTimePerSecond = 0
        self._reportToElasticsearch = False
        self._lastResponse = ""

        self._activityOnLastSample = False

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def executionTime(self):
        return self._executionTime

    @executionTime.setter
    def executionTime(self, value):
        self._executionTime = value

    @property
    def invocationCount(self):
        return self._invocationCount

    @invocationCount.setter
    def invocationCount(self, value):
        self._invocationCount = value

    @property
    def waitTime(self):
        return self._waitTime

    @waitTime.setter
    def waitTime(self, value):
        self._waitTime = value

    @property
    def lastSampleTime(self):
        return self._lastSampleTime

    @lastSampleTime.setter
    def lastSampleTime(self, value):
        self._lastSampleTime = value

    @property
    def invocationsSinceLastSample(self):
        return self._invocationsSinceLastSample

    @invocationsSinceLastSample.setter
    def invocationsSinceLastSample(self, value):
        self._invocationsSinceLastSample = value

    @property
    def executionTimeSinceLastSample(self):
        return self._executionTimeSinceLastSample

    @executionTimeSinceLastSample.setter
    def executionTimeSinceLastSample(self, value):
        self._executionTimeSinceLastSample = value

    @property
    def waitTimeSinceLastSample(self):
        return self._waitTimeSinceLastSample

    @waitTimeSinceLastSample.setter
    def waitTimeSinceLastSample(self, value):
        self._waitTimeSinceLastSample = value

    @property
    def invocationsPerSecond(self):
        return self._invocationsPerSecond

    @invocationsPerSecond.setter
    def invocationsPerSecond(self, value):
        self._invocationsPerSecond = value

    @property
    def executionTimePerSecond(self):
        return self._executionTimePerSecond

    @executionTimePerSecond.setter
    def executionTimePerSecond(self, value):
        self._executionTimePerSecond = value

    @property
    def waitTimePerSecond(self):
        return self._waitTimePerSecond

    @waitTimePerSecond.setter
    def waitTimePerSecond(self, value):
        self._waitTimePerSecond = value

    @property
    def reportToElasticsearch(self):
        return self._reportToElasticsearch

    @reportToElasticsearch.setter
    def reportToElasticsearch(self, value):
        self._reportToElasticsearch = value

    @property
    def lastResponse(self):
        return self._lastResponse

    @lastResponse.setter
    def lastResponse(self, value):
        self._lastResponse = value

    @property
    def activityOnLastSample(self):
        return self._activityOnLastSample

    @activityOnLastSample.setter
    def activityOnLastSample(self, value):
        self._activityOnLastSample = value

    def updateStats(self, responseJson, sampleTime):
        self._lastResponse = responseJson

        executionTime = 0
        invocationCount = 0
        waitTime = 0

        # TODO: Make helper method
        if "execution-time" in responseJson:
            executionTime = responseJson["execution-time"]

        if "invocations" in responseJson:
            invocationCount = responseJson["invocations"]

        if "wait-time" in responseJson:
            waitTime = responseJson["wait-time"]

        # If we are in the first pass for this bean, do not calc the avareges and so on
        if self.lastSampleTime == 0:
            self.reportToElasticsearch = True
            self.activityOnLastSample = False
        else:
            if (self.executionTime == executionTime) and (self.invocationCount == invocationCount) and (
                    self.waitTime == waitTime):
                # TODO: No change in bean data, do not report - consider controlling this with an ENV var

                # Last data point was reported, this data point is identical - we will report this one aswell, with the
                # zero activity that it has had. This is in order to drop the stats that are charted in Kibana to "0"
                if self.activityOnLastSample:
                    self._calculateStats(executionTime, invocationCount, waitTime, sampleTime)
                    self.reportToElasticsearch = True
                else:
                    self.reportToElasticsearch = False

                self.activityOnLastSample = False

            elif (self.executionTime > executionTime) or (self.invocationCount > invocationCount) or (
                    self.waitTime > waitTime):
                # This is the scenario is when a wildfly instance restarts. The counters will go back down.
                # We could mark a restart here!
                self.reportToElasticsearch = True
                # Reset all stats
                self.invocationsSinceLastSample = 0
                self.invocationsPerSecond = 0
                self.executionTimeSinceLastSample = 0
                self.executionTimePerSecond = 0
                self.waitTimeSinceLastSample = 0
                self.waitTimePerSecond = 0
                self.activityOnLastSample = True

            else:
                self.reportToElasticsearch = True
                self.activityOnLastSample = True

                self._calculateStats(executionTime, invocationCount, sampleTime, waitTime)

        self.executionTime = executionTime
        self.invocationCount = invocationCount
        self.waitTime = waitTime
        self.lastSampleTime = sampleTime

    def _calculateStats(self, executionTime, invocationCount, waitTime, sampleTime):
        deltaTimeMilliseconds = int((sampleTime - self.lastSampleTime).total_seconds() * 1000)
        self.logger.debug("Bean {0}, deltaTime: {1} ms".format(self.name, deltaTimeMilliseconds))
        # invocations stats
        self.logger.debug("Bean {0}, self.invocationCount: {1}".format(self.name, self.invocationCount))
        self.logger.debug("Bean {0}, responseJson[\"invocations\"]: {1}".format(self.name, invocationCount))
        self.invocationsSinceLastSample = invocationCount - self.invocationCount
        self.logger.debug(
            "Bean {0}, invocationsSinceLastSample: {1}".format(self.name, self.invocationsSinceLastSample))
        # execution time stats
        self.logger.debug("Bean {0}, self.executionTime: {1}".format(self.name, self.executionTime))
        self.logger.debug(
            "Bean {0}, responseJson[\"execution-time\"]: {1}".format(self.name, executionTime))
        self.executionTimeSinceLastSample = executionTime - self.executionTime
        self.logger.debug(
            "Bean {0}, executionTimeSinceLastSample: {1}".format(self.name, self.executionTimeSinceLastSample))
        # wait time stats
        self.logger.debug("Bean {0}, self.waitTime: {1}".format(self.name, self.waitTime))
        self.logger.debug("Bean {0}, responseJson[\"wait-time\"]: {1}".format(self.name, waitTime))
        self.waitTimeSinceLastSample = waitTime - self.waitTime
        self.logger.debug(
            "Bean {0}, waitTimeSinceLastSample: {1}".format(self.name, self.waitTimeSinceLastSample))
        if deltaTimeMilliseconds > 0:
            # Calculate delta in pr. minute (millisecs / 60 / 1000)
            self.invocationsPerSecond = self.invocationsSinceLastSample / (deltaTimeMilliseconds / 1000)
            self.logger.debug("Bean {0}, invocationsDelta: {1}".format(self.name, self.invocationsPerSecond))
            self.executionTimePerSecond = self.executionTimeSinceLastSample / (deltaTimeMilliseconds / 1000)
            self.logger.debug("Bean {0}, executionsDelta: {1}".format(self.name, self.executionTimePerSecond))
            self.waitTimePerSecond = self._waitTimeSinceLastSample / (deltaTimeMilliseconds / 1000)
            self.logger.debug("Bean {0}, waitTimeDelta: {1}".format(self.name, self.waitTimePerSecond))
        else:
            self.invocationsPerSecond = 0
            self.executionTimePerSecond = 0
            self.waitTimePerSecond = 0

    def getMonitorStats(self, prefix=""):
        jsondoc = {
            prefix + "invocations": self._invocationCount,
            prefix + "invocations-since-last-sample": self._invocationsSinceLastSample,
            prefix + "invocations-per-second": self._invocationsPerSecond,
            prefix + "execution-time": self._executionTime,
            prefix + "execution-time-since-last-sample": self._executionTimeSinceLastSample,
            prefix + "execution-time-per-second": self._executionTimePerSecond,
            prefix + "wait-time": self._waitTime,
            prefix + "wait-time-since-last-sample": self._waitTimeSinceLastSample,
            prefix + "wait-time-per-second": self._waitTimePerSecond
        }

        if reportRawJson:
            jsondoc["raw-json"] = json.dumps(self._lastResponse)

        return jsondoc
