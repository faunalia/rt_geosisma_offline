'''
# -*- coding: utf-8 -*-
# Copyright (C) 2013 Luigi Pirelli (luipir@gmail.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
Created on Oct 7, 2013

@author: Luigi Pirelli (luipir@gmail.com)
'''
import traceback
import json
import time
import os
from qgis.core import QgsLogger, QgsMessageLog, QgsCredentials
from qgis.core import QgsNetworkAccessManager
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *

from GeosismaWindow import GeosismaWindow as gw
from DlgWaiting import DlgWaiting

class UploadManager(DlgWaiting):
    
    # signals
    done = pyqtSignal(bool)
    singleSafetyUploadDone = pyqtSignal(bool)
    singleSafetyDownloadDone = pyqtSignal(bool)
    singleSopralluoghiDownloadDone = pyqtSignal(bool)
    singleSopralluoghiUpdateDone = pyqtSignal(bool)
    message = pyqtSignal(str, int)

    def __init__(self, parent=None):
        DlgWaiting.__init__(self, parent)
        self.safeties = None
        self.updatedSafeties = None
        self.saved_id = None
        self.saved_number = None
        self.saved_sopralluoghi = None
        self.manager = QgsNetworkAccessManager.instance();
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
        self.manager.authenticationRequired.connect(self.authenticationRequired)
        # get connection conf
        settings = QSettings()
        self.safetyUrl = settings.value("/rt_geosisma_offline/safetyUrl", "/api/v1/safety/")
        self.sopralluoghiUrl = settings.value("/rt_geosisma_offline/sopralluoghiUrl", "/api/v1/sopralluoghi/")
        self.baseApiUrl = settings.value("/rt_geosisma_offline/baseApiUrl", "http://geosisma-test.faunalia.it/")
        self.teamUrl = settings.value("/rt_geosisma_offline/teamUrl", "/api/v1/team/")
        self.requestUrl = settings.value("/rt_geosisma_offline/requestUrl", "/api/v1/request/")

    def initSafeties(self, safeties):
        self.safeties = safeties
        self.updatedSafeties = []
    
    def run(self):
        try:
            if self.safeties is None or len(self.safeties) == 0:
                return
            # init progress bar
            self.reset()
            self.setRange( 0, len(self.safeties) )
            QApplication.setOverrideCursor(Qt.WaitCursor)

            # set semaphores
            self.done.connect(self.setAllFinished)
            self.singleSafetyUploadDone.connect(self.setSingleSafetyUploadFinished)
            self.singleSafetyDownloadDone.connect(self.setSingleSafetyDownloadFinished)
            self.singleSopralluoghiDownloadDone.connect(self.setSingleSopralluoghiDownloadFinished)
            self.singleSopralluoghiUpdateDone.connect(self.setSingleSopralluoghiUpdateFinished)
            self.allFinished = False

            # upload safeties
            for safety in self.safeties:
                # check if safety already uploaded
                if str(safety["id"]) != "-1":
                    continue
                
                self.setWindowTitle( self.tr("Upload della scheda n: %d" % safety["number"]) )
                # save safety to a temp safety because of need of modification befor to upload
                safetyToUpload = safety.copy()
                
                # save plygon data to be saved after saving current safety
                the_geom = safetyToUpload.pop("the_geom")
                gids = safetyToUpload.pop("gid_catasto")
                local_id = safetyToUpload.pop("local_id")
                id = safetyToUpload.pop("id")
                number = safetyToUpload.pop("number")
                
                # prepare safety to send
                if "team_id" in safety:
                    safetyToUpload["team"] = self.teamUrl + str(safety["team_id"]) + "/"
                    safetyToUpload.pop("team_id")
                if "request_id" in safety:
                    safetyToUpload["request"] = self.requestUrl + str(safety["request_id"]) + "/"
                    safetyToUpload.pop("request_id")
                
                # set semaphore status for a single safety management
                self.singleSafetyUploadFinished = False
                self.singleSafetyDownloadFinished = False
                self.singleSopralluoghiDownloadFinished = False
                self.singleSopralluoghiUpdateFinished = False

                # upload
                self.saved_id = None
                self.saved_number = None
                self.saved_sopralluoghi = None
                self.uploadSafety(safetyToUpload)
            
                # whait end of single request
                while (not self.singleSafetyUploadFinished and not self.allFinished):
                    qApp.processEvents()
                    time.sleep(0.1)
                    
                # some other emitted done signal
                if (self.allFinished):
                    break
                    
                if self.saved_id is None:
                    message = self.tr("Non riesco a determinare l'id della scheda appena caricata sul server - numero provvisorio: %d" % number)
                    self.message.emit(message, QgsMessageLog.CRITICAL)
                    self.done.emit(False)
                    break
                
                # update current saved safety with new id
                safety["id"] = self.saved_id
                
                # get uploaded safety to update the offline version (mainly safety number)
                self.downloadRemoteSafety(safety["id"])

                # whait end of single request
                while (not self.singleSafetyDownloadFinished and not self.allFinished):
                    qApp.processEvents()
                    time.sleep(0.1)
                    
                # some other emitted done signal
                if (self.allFinished):
                    break
                    
                if self.saved_number is None:
                    message = self.tr("Non riesco a determinare il Number della scheda appena caricata sul server - numero provvisorio: %d" % number)
                    self.message.emit(message, QgsMessageLog.WARNING)
                else:
                    # update current saved safety with new id
                    safety["number"] = self.saved_number
                
                # now download geometry to allow it's update... I can't use
                # HTTP patch to update field because seems it's not supported by QNetworkAccessManager
                # do this only if the_geom  is not None
                if the_geom != None:
                    self.downloadRemoteSopralluoghi(safety["id"])
    
                    # whait end of single request
                    while (not self.singleSopralluoghiDownloadFinished and not self.allFinished):
                        qApp.processEvents()
                        time.sleep(0.1)
                        
                    if self.saved_sopralluoghi is None:
                        message = self.tr("Non riesco a scaricare la geometria dei sopralluoghi della scheda con id: %s" % safety["id"])
                        self.message.emit(message, QgsMessageLog.CRITICAL)
                        self.done.emit(False)
                        break
    
                    # some other emitted done signal
                    if (self.allFinished):
                        break
                    
                    # now update geometry related to the saved safety (based on self.saved_id)
                    self.saved_sopralluoghi["the_geom"] = the_geom
                    self.updateSopralluoghi(self.saved_sopralluoghi)
                
                    # whait end of single request
                    while (not self.singleSopralluoghiUpdateFinished and not self.allFinished):
                        qApp.processEvents()
                        time.sleep(0.1)
                        
                    # some other emitted done signal
                    if (self.allFinished):
                        break
                
                # notify successful upload of a safety
                message = self.tr("Upload con successo della scheda con local_id: %s - Numero definitivo: %s" % (str(safety["local_id"]), str(safety["number"])))
                self.message.emit(message, QgsMessageLog.CRITICAL)
                
                self.updatedSafeties.append(safety.copy())
                self.onProgress()
 
            if not self.allFinished:
                self.done.emit(True)
            
        except Exception as e:
            traceback.print_exc()
            self.done.emit(False)
            self.message.emit(e.message, QgsMessageLog.CRITICAL)
            QApplication.restoreOverrideCursor()
            raise e
        finally:
            QApplication.restoreOverrideCursor()
    
    def setSingleSafetyUploadFinished(self, success):
        self.singleSafetyUploadFinished = True

    def setSingleSafetyDownloadFinished(self, success):
        self.singleSafetyDownloadFinished = True

    def setSingleSopralluoghiDownloadFinished(self, success):
        self.singleSopralluoghiDownloadFinished = True

    def setSingleSopralluoghiUpdateFinished(self, success):
        self.singleSopralluoghiUpdateFinished = True

    def setAllFinished(self, success):
        self.allFinished = True

    def uploadSafety(self, safety):
        request = QNetworkRequest()
        request.setRawHeader("Content-Type", "application/json");
        url = QUrl(self.baseApiUrl + self.safetyUrl)
        
        request.setUrl(url)
        
        # register response manager
        try:
            self.manager.finished.disconnect()
        except:
            pass
        self.manager.finished.connect(self.replyUploadSafetyFinished)

        # start upload
        self.singleSafetyUploadFinished = False
        self.manager.post(request, json.dumps(safety) )

    def downloadRemoteSafety(self, safety_id):
        # register response manager
        try:
            self.manager.finished.disconnect()
        except:
            pass
        self.manager.finished.connect(self.replyDownloadSafetyFinished)

        # build request
        request = QNetworkRequest()
        request.setRawHeader("Content-Type", "application/json");
        url = QUrl(self.baseApiUrl + self.safetyUrl + safety_id + "/")
        url.addQueryItem("format", "json")
        
        request.setUrl(url)
        
        # start download
        self.singleSafetyDownloadFinished = False
        self.manager.get(request)

    def downloadRemoteSopralluoghi(self, safety_id):
        # register response manager
        try:
            self.manager.finished.disconnect()
        except:
            pass
        self.manager.finished.connect(self.replyDownloadSopralluoghiFinished)

        # build request
        request = QNetworkRequest()
        request.setRawHeader("Content-Type", "application/json");
        url = QUrl(self.baseApiUrl + self.sopralluoghiUrl)
        url.addQueryItem("id_scheda", safety_id)
        url.addQueryItem("format", "json")
        
        request.setUrl(url)
        
        # start download
        self.singleSopralluoghiDownloadFinished = False
        self.manager.get(request)

    def updateSopralluoghi(self, sopralluoghi):
        request = QNetworkRequest()
        request.setRawHeader("Content-Type", "application/json");
        url = QUrl(self.baseApiUrl + self.sopralluoghiUrl + str(sopralluoghi["gid"]))
        
        request.setUrl(url)
        
        # register response manager
        self.manager.finished.connect(self.replyUpdateSopralluoghiFinished)

        # start update
        self.singleSopralluoghiUpdateFinished = False
        sopralluoghi.pop("gid")
        self.manager.put(request, json.dumps(sopralluoghi) )

    def authenticationRequired(self, reply, authenticator ):
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
            if not ok: # MEANS PRESSED CANCEL
                gw.instance().authenticationRetryCounter = 0
                reply.abort()
                self.done.emit(False)
                return
        # do authentication
        authenticator.setUser(gw.instance().user)
        authenticator.setPassword(gw.instance().pwd)

    def replyUploadSafetyFinished(self, reply):
        # need auth. If this code is reached means that server is not asking auth
        # to generare authenticationRequired signal
        if reply.error() == QNetworkReply.AuthenticationRequiredError:
            gw.instance().autenthicated = False
            # do again until authenticated or reached max retry
            # need to add post data again?
            self.manager.post(reply.request())
            return
        
        # disconnect current reply callback
        self.manager.finished.disconnect(self.replyUploadSafetyFinished)
        
        # received error
        if reply.error():
            message = self.tr("Errore nella HTTP Request: %d - %s" % (reply.error(), reply.errorString()) )
            self.message.emit(message, QgsMessageLog.WARNING)
            self.done.emit(False)
            return
        
        # well authenticated :)
        gw.instance().autenthicated = True
        gw.instance().authenticationRetryCounter = 0

        #print reply.rawHeader()
        headerKeys = reply.rawHeaderList()
        if not ("Location" in headerKeys):
            message = self.tr("Errore nella HTTP reply header. Location is not set" )
            self.message.emit(message, QgsMessageLog.CRITICAL)
            self.done.emit(False)
            return
        
        for elem in reply.rawHeaderPairs():
            k,v = elem
            if k != "Location":
                continue
            location = str(v)
            break
        
        # get id of the archived safety
        self.saved_id = os.path.split(os.path.split( location )[0])[1]

        message = self.tr("self.saved_id: %s - %s" % (self.saved_id, location) )
        self.message.emit(message, QgsMessageLog.INFO)
        
        # successfully end
        self.singleSafetyUploadDone.emit(True)

    def replyDownloadSafetyFinished(self, reply):
        # need auth. If this code is reached means that server is not asking auth
        # to generare authenticationRequired signal
        if reply.error() == QNetworkReply.AuthenticationRequiredError:
            gw.instance().autenthicated = False
            # do again until authenticated or reached max retry
            self.manager.get(reply.request())
            return
        
        # disconnect current reply callback
        self.manager.finished.disconnect(self.replyDownloadSafetyFinished)
        
        # received error
        if reply.error():
            message = self.tr("Errore nella HTTP Request: %d - %s" % (reply.error(), reply.errorString()) )
            self.message.emit(message, QgsMessageLog.WARNING)
            return
        
        # well authenticated :)
        gw.instance().autenthicated = True
        gw.instance().authenticationRetryCounter = 0

        from json import loads
        raw = reply.readAll()
        try:
            jsonRequest = loads(raw.data())
        except Exception:
            traceback.print_exc()
            self.done.emit(False)
            return
        QgsLogger.debug("replyDownloadSafetyFinished received request %s" % json.dumps(jsonRequest),2 )
        
        # get number of the archived safety
        self.saved_number = jsonRequest["number"]

        message = self.tr("self.saved_number: %s" % self.saved_number )
        self.message.emit(message, QgsMessageLog.INFO)
        
        # successfully end
        self.singleSafetyDownloadDone.emit(True)
        
    def replyDownloadSopralluoghiFinished(self, reply):
        # need auth. If this code is reached means that server is not asking auth
        # to generare authenticationRequired signal
        if reply.error() == QNetworkReply.AuthenticationRequiredError:
            gw.instance().autenthicated = False
            # do again until authenticated or reached max retry
            self.manager.get(reply.request())
            return
        
        # disconnect current reply callback
        self.manager.finished.disconnect(self.replyDownloadSopralluoghiFinished)
        
        # received error
        if reply.error():
            message = self.tr("Errore nella HTTP Request: %d - %s" % (reply.error(), reply.errorString()) )
            self.message.emit(message, QgsMessageLog.CRITICAL)
            self.done.emit(False)
            return
        
        # well authenticated :)
        gw.instance().autenthicated = True
        gw.instance().authenticationRetryCounter = 0

        from json import loads
        raw = reply.readAll()
        try:
            jsonRequest = loads(raw.data())
        except Exception:
            traceback.print_exc()
            self.done.emit(False)
            return
        QgsLogger.debug("replyDownloadSopralluoghiFinished received request %s" % json.dumps(jsonRequest),2 )
        
        # check if return more than 20 elements (e.g. for the super user)
        if "objects" in jsonRequest:
            jsonSopralluoghi = jsonRequest["objects"] # get array of dicts
        else:
            jsonSopralluoghi = [jsonRequest]
        
        # get number of the archived safety
        if len(jsonSopralluoghi) == 0:
            message = self.tr("Errore nel record sopralluoghi appena scaricato: %s" % json.dumps(jsonSopralluoghi) )
            self.message.emit(message, QgsMessageLog.CRITICAL)
            self.done.emit(False)
            return
            
        self.saved_sopralluoghi = jsonSopralluoghi[0]

        message = self.tr("self.saved_sopralluoghi: %s" % json.dumps(self.saved_sopralluoghi) )
        self.message.emit(message, QgsMessageLog.INFO)
        
        # successfully end
        self.singleSopralluoghiDownloadDone.emit(True)
        
    def replyUpdateSopralluoghiFinished(self, reply):
        # need auth. If this code is reached means that server is not asking auth
        # to generare authenticationRequired signal
        if reply.error() == QNetworkReply.AuthenticationRequiredError:
            gw.instance().autenthicated = False
            # do again until authenticated or reached max retry
            self.manager.put(reply.request())
            return
        
        # disconnect current reply callback
        self.manager.finished.disconnect(self.replyUpdateSopralluoghiFinished)
        
        # received error
        if reply.error() and reply.error() != 204:
            message = self.tr("Errore nella HTTP Request: %d - %s" % (reply.error(), reply.errorString()) )
            self.message.emit(message, QgsMessageLog.CRITICAL)
            self.done.emit(False)
            return
        
        # well authenticated :)
        gw.instance().autenthicated = True
        gw.instance().authenticationRetryCounter = 0
        
        # successfully end
        self.singleSopralluoghiUpdateDone.emit(True)
