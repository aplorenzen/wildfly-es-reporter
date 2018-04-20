import logging


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
        else:
            if (self.executionTime == executionTime) and (self.invocationCount == invocationCount) and (
                    self.waitTime == waitTime):
                # No change in bean data, do not report - consider controlling this with an ENV var
                self.reportToElasticsearch = False
            else:
                self.reportToElasticsearch = True

                deltaTimeMilliseconds = int((sampleTime - self.lastSampleTime).total_seconds() * 1000)
                self.logger.debug("Bean {0}, deltaTime: {1} ms".format(self.name, deltaTimeMilliseconds))

                self.logger.debug("Bean {0}, self.invocationCount: {1}".format(self.name, self.invocationCount))
                self.logger.debug(
                    "Bean {0}, responseJson[\"invocations\"]: {1}".format(self.name, responseJson["invocations"]))
                self.invocationsSinceLastSample = invocationCount - self.invocationCount
                self.logger.debug(
                    "Bean {0}, invocationsSinceLastSample: {1}".format(self.name, self.invocationsSinceLastSample))

                self.logger.debug("Bean {0}, self.executionTime: {1}".format(self.name, self.executionTime))
                self.logger.debug(
                    "Bean {0}, responseJson[\"execution-time\"]: {1}".format(self.name,
                                                                             responseJson["execution-time"]))
                self.executionTimeSinceLastSample = executionTime - self.executionTime
                self.logger.debug(
                    "Bean {0}, executionTimeSinceLastSample: {1}".format(self.name, self.executionTimeSinceLastSample))

                if deltaTimeMilliseconds > 0:
                    # Calculate delta in pr. minute (millisecs / 60 / 1000)
                    self.invocationsPerSecond = self.invocationsSinceLastSample / (deltaTimeMilliseconds / 1000)
                    self.logger.debug("Bean {0}, invocationsDelta: {1}".format(self.name, self.invocationsPerSecond))
                    self.executionTimePerSecond = self.executionTimeSinceLastSample / (deltaTimeMilliseconds / 1000)
                    self.logger.debug("Bean {0}, executionsDelta: {1}".format(self.name, self.executionTimePerSecond))
                else:
                    self.invocationsPerSecond = 0
                    self.executionTimePerSecond = 0

        self.executionTime = executionTime
        self.invocationCount = invocationCount
        self.waitTime = waitTime
        self.lastSampleTime = sampleTime

    def getMonitorStats(self):
        jsondoc = {
            'invocations': self._invocationCount,
            'invocations-since-last-sample': self._invocationsSinceLastSample,
            'invocations-per-second': self._invocationsPerSecond,
            'execution-time': self._executionTime,
            'execution-time-since-last-sample': self._executionTimeSinceLastSample,
            'execution-time-per-second': self._executionTimePerSecond,
            'wait-time': self._waitTime,
            'wait-time-since-last-sample': self._waitTimeSinceLastSample,
            'wait-time-per-second': self._waitTimePerSecond,
            # "raw-json": self._lastResponse
        }

        return jsondoc
