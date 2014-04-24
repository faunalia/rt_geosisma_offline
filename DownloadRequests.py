import os, json, traceback, time
from qgis.core import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *

from DlgWaiting import DlgWaiting
from GeosismaWindow import GeosismaWindow as gw

# SpatiaLite imports
from pyspatialite import dbapi2 as db

class DownloadRequests(DlgWaiting):
    
    # signals
    done = pyqtSignal(bool)
    singleDone = pyqtSignal(bool)
    message = pyqtSignal(str, int)

    def __init__(self, parent=None):
        DlgWaiting.__init__(self, parent)
        self.singleFinished = True
        self.allFinished = True
        
        self.jsonRequests = None
        
        self.manager = QgsNetworkAccessManager.instance()
        # clean listeners to avoid overlap 
        try:
            self.manager.authenticationRequired.disconnect()
        except:
            pass
        try:
            self.manager.finished.disconnect()
        except:
            pass
        # add new listeners
        self.manager.finished.connect(self.replyFinished)
        self.manager.authenticationRequired.connect(self.authenticationRequired)

        #self.setWindowModality(Qt.ApplicationModal)
    
    def __del__(self):
        try:
            self.manager.finished.disconnect(self.replyFinished)
            self.manager.authenticationRequired.disconnect(self.authenticationRequired)
        except Exception:
            pass
    
    def run(self):
        try:
            #self.requestsApi = gw.instance().downloadedRequestsApi
            self.downloadedTeams = gw.instance().downloadedTeams
            self.downloadedRequests = gw.instance().downloadedRequests
            
            # count how many download
            numDownload = 0
            for team in self.downloadedTeams:
                for request in team["requests"]:
                    numDownload += 1
            
            # init progress bar
            self.reset()
            self.setWindowTitle( self.tr("Scarica le schede Sopralluogo del Team") )
            self.setRange( 0, numDownload )
            QApplication.setOverrideCursor(Qt.WaitCursor)

            # set semaphores
            self.done.connect(self.setAllFinished)
            self.singleDone.connect(self.setSingleFinished)

            # for each request api
            self.allFinished = False

            #for requestApi in self.requestsApi:
            for index,team in enumerate(self.downloadedTeams):
                
                for requestApi in team["requests"]:
            
                    # create db
                    self.jsonRequest = None
                    self.singleFinished = False
                    self.downloadRequests(requestApi)
                    
                    # whait end of single request
                    while (not self.singleFinished):
                        qApp.processEvents()
                        time.sleep(0.1)
                    
                    # archive request in self.downloadedTeams
                    self.downloadedTeams[index]["downloadedRequests"][requestApi] = self.jsonRequests
                    self.downloadedRequests.append(self.jsonRequests)
                    
                    self.onProgress()
                    
                    # some other emitted done signal
                    if (self.allFinished):
                        return
            
            gw.instance().downloadedTeams = self.downloadedTeams
            gw.instance().downloadedRequests = self.downloadedRequests
            
            self.done.emit(True)
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            try:
                traceback.print_exc()
            except:
                pass
            self.done.emit(False)
            self.message.emit(e.message, QgsMessageLog.CRITICAL)
            raise e
        finally:
            QApplication.restoreOverrideCursor()

    def setSingleFinished(self, success):
        self.singleFinished = True

    def setAllFinished(self, success):
        self.allFinished = True

    def downloadRequests(self, requestApi):
        
        # get connection conf
        settings = QSettings()
        self.baseApiUrl = settings.value("/rt_geosisma_offline/baseApiUrl", "http://geosisma-test.faunalia.it/")

        # for each request api
        message = self.tr("Download Richiesta %s" % requestApi)
        self.message.emit(message, QgsMessageLog.INFO)
        
        request = QNetworkRequest()
        url = QUrl(self.baseApiUrl + requestApi)
        url.addQueryItem("format", "json")
        request.setUrl(url)
        
        # start download
        self.manager.get(request)
        
        # wait request finish to go to the next
        self.singleFinished = False

    def authenticationRequired(self, reply, authenticator ):
        if self is None:
            return
        # check if reached mas retry
        gw.instance().authenticationRetryCounter += 1
        if (gw.instance().authenticationRetryCounter % gw.instance().maxAuthenticationError) == 0:
            gw.instance().authenticationRetryCounter = 0 # reset counter
            message = self.tr("Autenticazione fallita piu' di %d volte" % gw.instance().maxAuthenticationError)
            self.message.emit(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, gw.MESSAGELOG_CLASS, message)
            # abort continuing request
            reply.abort()
            self.done.emit(False)
            return
        # if not authenticated ask credentials
        if not gw.instance().autenthicated:
            (ok, gw.instance().user, gw.instance().pwd) = QgsCredentials.instance().get("", gw.instance().user, gw.instance().pwd, self.tr("Inserisci User e PWD della tua utenza Geosisma"))
            if not ok: # MEANS PRESED CANCEL
                gw.instance().authenticationRetryCounter = 0
                reply.abort()
                message = self.tr("Mancata autenticazione")
                self.message.emit(message, QgsMessageLog.WARNING)
                self.done.emit(False)
                return
        # do authentication
        authenticator.setUser(gw.instance().user)
        authenticator.setPassword(gw.instance().pwd)

    def replyFinished(self, reply):
        if self is None:
            return
        
        # need auth
        if reply.error() == QNetworkReply.AuthenticationRequiredError:
            gw.instance().autenthicated = False
            # do again until authenticated or reached max retry
            self.manager.get(reply.request())
            return
        
        # received error
        if reply.error():
            message = self.tr("Errore nella HTTP Request: %d - %s" % (reply.error(), reply.errorString()) )
            self.message.emit(message, QgsMessageLog.WARNING)
            self.done.emit(False)
            return
        
        # well authenticated :)
        gw.instance().autenthicated = True
        gw.instance().authenticationRetryCounter = 0

        from json import loads
        raw = reply.readAll()
        try:
            self.jsonRequests = loads(raw.data())
        except Exception as e:
            try:
                traceback.print_exc()
            except:
                pass
            self.done.emit(False)
            return
        
        #gw.instance().downloadedRequests.append(jsonRequests)
        
        # successfully end
        self.singleDone.emit(True)
