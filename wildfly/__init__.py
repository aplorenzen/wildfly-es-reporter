import os
import logging
import requests
from requests.auth import HTTPDigestAuth


monitorName = os.getenv("MONITOR_NAME", "wildfly-monitor")
logPath = "wildfly"
logger = logging.getLogger(monitorName + "." + logPath)


class Wildfly(object):
    def __init__(self, host, port, deployment, sub_deployment, user, password, alias="wildfly", protocol="http"):
        self._host = host
        self._port = port
        self._wildfly_deployment = deployment
        self._wildfly_sub_deployment = sub_deployment
        self._wildfly_user = user
        self._wildfly_password = password
        self._alias = alias
        self._protocol = protocol

        self._bean_monitors = dict()
        self._request_counter = 0

        # Compose the target Wildfly mangement HTTP endpoint that we are targeting
        self._wildfly_host_url = (self.protocol + "://" + self.host + ":" + self.port)

        self._wildfly_management_url = (self._wildfly_host_url + "/management")

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def wildflyDeployment(self):
        return self._wildfly_deployment

    @property
    def wildflySubdeployment(self):
        return self._wildfly_sub_deployment

    @property
    def wildflyUser(self):
        return self._wildfly_user

    @property
    def wildflyPassword(self):
        return self._wildfly_password

    @property
    def alias(self):
        return self._alias

    @property
    def protocol(self):
        return self._protocol

    @property
    def wildflyHostUrl(self):
        return self._wildfly_host_url

    @property
    def wildflyManagementUrl(self):
        return self._wildfly_management_url

    def _perform_management_request(self, request_body):
        try:
            # TODO: TRACE log
            response = requests.post(self.wildflyManagementUrl, json=request_body, auth=HTTPDigestAuth(self.wildflyUser, self.wildflyPassword))
            self._request_counter += 1
            # TODO: Debug log response

            if response.status_code == requests.codes.ok:

                responseJson = response.json()
                # TODO: Debug log responseJson

                # "outcome": "failed"
                # "outcome": "success"

                if "outcome" in responseJson:
                    if responseJson["outcome"] == "success":
                        if "result" in responseJson:
                            # TODO: TRACE log what happened
                            return True, responseJson["result"]
                        else:
                            # TODO: Consider what to return in this scenation, success was given, but no result? Is this a valid scenario? Log something.
                            # TODO: Debug log what happend
                            return True, responseJson
                    else:
                        # TODO: Debug log what happened
                        return False, None
                else:
                    # TODO: Debug log what happened
                    return False, None
            else:
                # TODO: Debug log what happened
                return False, None

        except Exception as exception:
            # TODO: Error log what happened
            return False, None

    def refreshBeanNames(self):

        request_body = {
            "operation": "read-resource",
            "address": [
                "deployment", self.wildflyDeployment, "subdeployment", self.wildflySubdeployment, "subsystem", "ejb3"
            ],
            "json.pretty": 1
        }

        request_success, response_json = self._perform_management_request(request_body)

        if request_success:
            bean_names = response_json["stateless-session-bean"].keys()

            for key in bean_names:
                if key not in self._bean_monitors.keys():
                    self._bean_monitors[key] = BeanMonitor(key)




# {
#     "outcome": "success",
#     "result": {
#         "entity-bean": null,
#         "message-driven-bean": null,
#         "singleton-bean": {
#             "GjensidigePreswapSentCustomerScheduler": null,
#             "GjensidigeTwoDayNotPaidScheduler": null,
#             "StartupBean": null,
#             "PackageTrackingScheduler": null,
#             "GjensidigeNotReturnedDeviceScheduler": null,
#             "SamsungWIPReportScheduler": null,
#             "WillisHandlerScheduler": null,
#             "MonduxEnrichmentScheduler": null,
#             "ServerSideConstants": null,
#             "GjensidigePaidNotSentReminderScheduler": null,
#             "MasterDataCacheBean": null,
#             "GjensidigeTwoDayOrderScheduler": null,
#             "EhfTransfterScheduler": null,
#             "GjensidigeFourDayOrderScheduler": null,
#             "MonduxScheduler": null,
#             "DatainfoReturnDeviceReminderScheduler": null,
#             "MailQHandlerScheduler": null
#         },
#         "stateful-session-bean": null,
#         "stateless-session-bean": {
#             "ContactBean": null,
#             "NokiaHMDProcessReturnRepairBean": null,
#             "OrderCheckBean": null,
#             "EventBean": null,
#             "InternalInvoiceBean": null,
#             "OrderPrintBean": null,
#             "ScreeningBean": null,
#             "CaterpillarServiceBean": null,
#             "I18nBean": null,
#             "ZteBean": null,
#             "FmipBean": null,
#             "HelpBean": null,
#             "CreateOrderSamsungBean": null,
#             "AdminOrderstatusBean": null,
#             "SolidBean": null,
#             "Hi3GStatusSnapServiceBean": null,
#             "OFSBean": null,
#             "CurrencyBean": null,
#             "HelloWorld": null,
#             "PayableServicesServiceBean": null,
#             "OrderMessageBean": null,
#             "GpsBean": null,
#             "UpdateOrderBean": null,
#             "TimeBean": null,
#             "ApplicationEnvironmentBean": null,
#             "FinalizeOrderBean": null,
#             "MailQHandler": null,
#             "PackageDeviationBean": null,
#             "NokiaBean": null,
#             "OrderingBean": null,
#             "CreateReturnInitialBean": null,
#             "HibernateBean": null,
#             "AccountServiceBean": null,
#             "AccountBean": null,
#             "InvoiceBean": null,
#             "PostBean": null,
#             "ProcessReturnGenerateQuoteBean": null,
#             "PoAvailabilitySamsungBean": null,
#             "EstimateReplyApi16Bean": null,
#             "ScreeningSwapstockBean": null,
#             "OnePlusBean": null,
#             "UtilityBean": null,
#             "ServicePortalAdminBean": null,
#             "UpdateOrderApiBean": null,
#             "ProcessReturnRepairBean": null,
#             "DocumentBean": null,
#             "NMSBean": null,
#             "AdminTemplateBean": null,
#             "NokiaHMDProcessReturnGenerateQuoteBean": null,
#             "HelloWorldBean": null,
#             "LoanBean": null,
#             "HelperBean": null,
#             "OrderCommentApi16Bean": null,
#             "NotifyShipmentBean": null,
#             "IGSPNBean": null,
#             "StatusActionBean": null,
#             "NotificationBean": null,
#             "PreprocessBean": null,
#             "TatInvoiceBean": null,
#             "AppleBean": null,
#             "UpdatedOrdersServiceBean": null,
#             "ShipmentApi16Bean": null,
#             "EstimateReplyBean": null,
#             "PackageServiceBean": null,
#             "StorageBean": null,
#             "SecuredPartsBean": null,
#             "PayableServicesBean": null,
#             "WillisBean": null,
#             "MasterDataBean": null,
#             "CheckCostproposalBean": null,
#             "AlcatelClaimBean": null,
#             "NokiaEbuilderCommunicationBean": null,
#             "ElectronicInvoiceBean": null,
#             "NetsBean": null,
#             "ConstantsEtelBean": null,
#             "EhfInvoiceBean": null,
#             "ServicePortalBean": null,
#             "ReportBean": null,
#             "EdiBean": null,
#             "InvoiceStorageBean": null,
#             "MultiLoginServiceBean": null,
#             "UpdateEventBean": null,
#             "FinalTestBean": null,
#             "NokiaHMDProcessReturnWaitBean": null,
#             "SubStatusBean": null,
#             "IncomingCallsBean": null,
#             "OpenVisionBean": null,
#             "ProcessReturnForwardBean": null,
#             "Sos_StockTransferBean": null,
#             "InternalStatusBean": null,
#             "SomosBean": null,
#             "BestillingBean": null,
#             "InvoiceOrderBean": null,
#             "ProcessReturnWaitBean": null,
#             "BuybackReportBean": null,
#             "InvoiceGeneratingBean": null,
#             "SonyEricssonBean": null,
#             "BuybackBean": null,
#             "HTCBean": null,
#             "MarshallBean": null,
#             "ConsignorBean": null,
#             "AlcatelBean": null,
#             "TermsBean": null,
#             "NokiaHMDSynchronizeStocksBean": null,
#             "StorageArticleCountBean": null,
#             "TestBean": null,
#             "SupportBean": null,
#             "ArticleTemplateBean": null,
#             "MarshallInvoiceBean": null,
#             "SynchronizeStocksBean": null,
#             "EstimateDeliveryTimeBean": null,
#             "OrderStatusContactBean": null,
#             "NextbaseBean": null,
#             "ClaimHuaweiBean": null,
#             "OrderSummaryBean": null,
#             "MessagingBean": null,
#             "CreateReturnInitialStockProcessingBean": null,
#             "CreateOrderSamsungApiBean": null,
#             "StatusesBean": null,
#             "InvoiceReportingBean": null,
#             "PaymentBean": null,
#             "TomTomBean": null,
#             "QualityBean": null,
#             "NokiaHMDProcessReturnCancelBean": null,
#             "CreateOrderServiceBean": null,
#             "VismaExportBean": null,
#             "SoAttachSwCreateBean": null,
#             "EdiSSCCPackageIDCalculatorBean": null,
#             "ExtraServiceBean": null,
#             "SonyEbuilderCommunicationBean": null,
#             "PartOrderBean": null,
#             "PoCreateSamsungBean": null,
#             "MicrosoftBean": null,
#             "NokiaHMDCreateReturnReceiveBean": null,
#             "AppleModelBean": null,
#             "MonduxBean": null,
#             "ConfigServiceBean": null,
#             "CreateReturnReceiveBean": null,
#             "OrderStatusUpdateRulesEngine": null,
#             "OrderCommentBean": null,
#             "PreswapBean": null,
#             "OnePlusClaimBean": null,
#             "StatusApi16Bean": null,
#             "AdminStorageBean": null,
#             "DroolsBean": null,
#             "ServiceOrderBean": null,
#             "SamsungBean": null,
#             "DataUpdateBean": null,
#             "AddDocumentServiceBean": null,
#             "MessageBean": null,
#             "ProcessReturnCancelBean": null,
#             "CreateOrderApi16Bean": null,
#             "ProcessReturnDismantleBean": null,
#             "RetailerBean": null,
#             "StatusBean": null,
#             "ContactServiceBean": null,
#             "PackageBean": null,
#             "ClientLoaderBean": null,
#             "EstimatedTimeBean": null,
#             "KazamBean": null,
#             "StatisticsBean": null,
#             "DisplayOrderBean": null,
#             "OrderStorageBean": null,
#             "ArrivalRegNotificationBean": null,
#             "InvoiceJournalBean": null,
#             "InvoiceConfigBean": null,
#             "ValidateImeiServiceBean": null,
#             "MotorolaBean": null,
#             "AutomationBean": null,
#             "DoroBean": null,
#             "ModelsLinkBean": null,
#             "GroupBean": null,
#             "TaskBean": null,
#             "ProductReturnBean": null,
#             "CheckMendBean": null,
#             "UpdateEtelOrderBean": null,
#             "ReportingBean": null,
#             "RedmineBean": null,
#             "CreateOrderBean": null,
#             "SonyCareBean": null,
#             "PartDeleteBean": null,
#             "AdminBean": null,
#             "LoginRoleBean": null,
#             "LjungbyBean": null,
#             "EmporiaTelmeBean": null,
#             "AppleTatBean": null,
#             "HuaweiBean": null,
#             "StoragePriceOverrideBean": null,
#             "CustomerTextBean": null,
#             "DataUpdateApi16Bean": null,
#             "OrderPriceBean": null,
#             "MessageServiceBean": null,
#             "ReportCodeBean": null,
#             "AudioProBean": null,
#             "PriceEstimateServiceBean": null,
#             "FaultyStockBean": null,
#             "FactoringBean": null,
#             "ProcessReturnExternalUpdateBean": null,
#             "IGSPNApiBean": null,
#             "SonimBean": null,
#             "OrderBean": null,
#             "NokiaHMDCreateReturnInitialBean": null,
#             "BluefrontBean": null,
#             "DealerLabelBean": null,
#             "SwapstockBean": null,
#             "MonitoringBean": null,
#             "PreAlertReceiveBean": null,
#             "ShipmentBean": null,
#             "PackageTrackingBean": null
#         }
#     }
# }