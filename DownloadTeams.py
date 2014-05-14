import os, json, traceback, time
from qgis.core import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *

from DlgWaiting import DlgWaiting
from GeosismaWindow import GeosismaWindow as gw

# SpatiaLite imports
from pyspatialite import dbapi2 as db

class DownloadTeams(DlgWaiting):
    
    # signals
    done = pyqtSignal(bool)
    message = pyqtSignal(str, int)

    def __init__(self, parent=None):
        DlgWaiting.__init__(self, parent)
        self.singleFinished = True
        #self.setWindowModality(Qt.ApplicationModal)
    
    def __del__(self):
        try:
            self.manager.finished.disconnect(self.replyFinished)
            self.manager.authenticationRequired.disconnect(self.authenticationRequired)
        except Exception:
            pass
    
    def run(self):
        try:
            # init progress bar
            self.reset()
            self.setRange( 0, 0 )
            
            self.setWindowTitle( self.tr("Scarica le Richieste sopralluoghi associati ai Team") )
            QApplication.setOverrideCursor(Qt.WaitCursor)

            # create db
            self.downloadTeams()
            
            # wait end of download
            self.done.connect(self.setFinished)
            while (not self.singleFinished):
                qApp.processEvents()
                time.sleep(0.1)
            
        except Exception as e:
            try:
                traceback.print_exc()
            except:
                pass
            self.done.emit(False)
            self.message.emit(e.message, QgsMessageLog.CRITICAL)
            raise e
        finally:
            QApplication.restoreOverrideCursor()

    def setFinished(self, success):
        self.singleFinished = True

    def downloadTeams(self):
        
        # get connection conf
        settings = QSettings()
        teamUrl = settings.value("/rt_geosisma_offline/teamUrl", "/api/v1/team/")
        self.baseApiUrl = settings.value("/rt_geosisma_offline/baseApiUrl", "http://geosisma-test.faunalia.it/")

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

        request = QNetworkRequest()
        url = QUrl(self.baseApiUrl + teamUrl)
        url.addQueryItem("format", "json")
        request.setUrl(url)
        
        # start download
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.manager.get(request)

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
            json = loads(raw.data())
        except Exception as e:
            try:
                traceback.print_exc()
            except:
                pass
            self.done.emit(False)
            return
        # check if return more than 20 elements (e.g. for the super user)
        if "objects" in json:
            jsonTeams = json["objects"] # get array of dicts
        else:
            jsonTeams = [json]
        for team in jsonTeams:
            gw.instance().downloadedTeams.append(team)
        
        # manage get of other elements if available 
        if "meta" in json:
            if "next" in json["meta"]:
                nextUrl = json["meta"]["next"]
                if nextUrl:
                    self.message.emit(nextUrl, QgsMessageLog.INFO)
                    
                    request = QNetworkRequest()
                    url = QUrl(self.baseApiUrl + nextUrl)
                    request.setUrl(url)
                    
                    self.manager.get(request)
                    return
        
        # successfully end
        self.manager.finished.disconnect(self.replyFinished)
        self.manager.authenticationRequired.disconnect(self.authenticationRequired)
        
        self.done.emit(True)
