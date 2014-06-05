# -*- coding: utf-8 -*-
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
import ast # used to convert string indict because json.loads could fail
from qgis.core import QgsLogger, QgsMessageLog
from qgis.core import QgsNetworkAccessManager
from qgis.core import QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsGeometry
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *

from GeosismaWindow import GeosismaWindow as gw
from ArchiveManager import ArchiveManager
from DlgWaiting import DlgWaiting

class UploadManager(DlgWaiting):
    
    # signals
    done = pyqtSignal(bool)
    singleSafetyUploadDone = pyqtSignal(bool)
    singleSafetyUpdateDone = pyqtSignal(bool)
    singleSafetyDuplicationError = pyqtSignal()
    singleAttachmentUploadDone = pyqtSignal(bool)
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
            self.manager.finished.disconnect()
        except:
            pass
        # get connection conf
        settings = QSettings()
        self.safetyUrl = settings.value("/rt_geosisma_offline/safetyUrl", "/api/v1/safety/")
        self.sopralluoghiUrl = settings.value("/rt_geosisma_offline/sopralluoghiUrl", "/api/v1/sopralluoghi/")
        self.baseApiUrl = settings.value("/rt_geosisma_offline/baseApiUrl", "http://geosisma.faunalia.it/")
        self.teamUrl = settings.value("/rt_geosisma_offline/teamUrl", "/api/v1/team/")
        self.requestUrl = settings.value("/rt_geosisma_offline/requestUrl", "/api/v1/request/")
        self.attachmentUrl = settings.value("/rt_geosisma_offline/attachmentUrl", "/api/v1/attachment/")
        self.staffUrl = settings.value("/rt_geosisma_offline/staffUrl", "/api/v1/staff/")

    def initSafeties(self, safeties):
        self.safeties = safeties
        self.updatedSafeties = []
    
    def run(self):
        # in this code I'll try to use semaphorese instead to event to manage sequence of actions
        # as you can see the code is less readable in terms of lenght but it follow a linear workflow
        # using event can crate a more modular and robust code but not linear to read
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
            self.singleSafetyUpdateDone.connect(self.setSingleSafetyUpdateFinished)
            self.singleSafetyDuplicationError.connect(self.setSingleSafetyDuplicationError)
            self.singleAttachmentUploadDone.connect(self.setSingleAttachmentUploadFinished)
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
                #number = safetyToUpload.pop("number")
                number = safetyToUpload["number"]
                
                # prepare safety to send
                if "team_id" in safety:
                    safetyToUpload["team"] = self.teamUrl + str(safety["team_id"]) + "/"
                    safetyToUpload.pop("team_id")
                if "request_id" in safety and safety["request_id"] != "" and safety["request_id"] != None:
                    safetyToUpload["request"] = self.requestUrl + str(safety["request_id"]) + "/"
                    safetyToUpload.pop("request_id")
                else:
                    safetyToUpload["request"] = None
                
                # set semaphore status for a single safety management
                self.singleSafetyUploadFinished = False
                self.singleSafetyUpdateFinished = False
                self.singleSafetyDuplicationErrorReceived = False
                self.singleSafetyDownloadFinished = False
                self.singleSopralluoghiDownloadFinished = False
                self.singleSopralluoghiUpdateFinished = False

                # upload
                self.saved_id = None
                self.saved_number = None
                self.saved_sopralluoghi = None
                
                while (not self.singleSafetyUploadFinished and not self.allFinished):
                    self.uploadSafety(safetyToUpload)
                
                    # wait end of single request
                    # or error or dulication safety error
                    while (not self.singleSafetyUploadFinished and not self.allFinished and not self.singleSafetyDuplicationErrorReceived):
                        qApp.processEvents()
                        time.sleep(0.1)
                        
                    # some other emitted done signal
                    if (self.allFinished):
                        break
                    
                    # received a duplication error => remove safey number to allow server to set it then upload again
                    if self.singleSafetyDuplicationErrorReceived:
                        self.singleSafetyDuplicationErrorReceived = False
                        
                        # remove safety number from the record and from the subsafety
                        safetyToUpload.pop("number")
                        self.saved_id = None
                        self.saved_number = None
                        
                        subSafetyDict = ast.literal_eval( safetyToUpload["safety"] )
                        if "number" in subSafetyDict:
                            subSafetyDict["number"]  = None
                        safetyToUpload["safety"] = json.dumps(subSafetyDict)

                
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

                # wait end of single request
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
                    currentSafetyDict = json.loads( safety["safety"] )
                    currentSafetyDict["number"] = self.saved_number
                    safety["safety"] = json.dumps(currentSafetyDict)
                    
                    # prepare safety toi upload in case necessary to upload it again
                    safetyToUpload["id"] = safety["id"]
                    safetyToUpload["number"] = self.saved_number
                    safetyToUpload["safety"] = json.dumps(currentSafetyDict)
                    
                # upload again the safety if number has been changed
                if number != self.saved_number:
                    self.updateSafety(safetyToUpload)
                
                    # wait end of single request
                    # or error or dulication safety error
                    while (not self.singleSafetyUpdateFinished and not self.allFinished):
                        qApp.processEvents()
                        time.sleep(0.1)
                        
                    # some other emitted done signal
                    if (self.allFinished):
                        break
                    
                # now download geometry to allow it's update... I can't use
                # HTTP patch to update field because seems it's not supported by QNetworkAccessManager
                # do this only if the_geom  is not None
                if the_geom != None and the_geom != "":
                    self.downloadRemoteSopralluoghi(safety["id"])
    
                    # wait end of single request
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
                    
                    # convert the_geom from default srid to geodb srid
                    geom = QgsGeometry().fromWkt(the_geom)
                    if not geom:
                        message = self.tr(u"Errore nella conversione della WKT in geometria - %s" % the_geom)
                        self.showMessage(message, QgsMessageLog.WARNING)
                        return
                    defaultCrs = QgsCoordinateReferenceSystem(gw.instance().DEFAULT_SRID)  # WGS 84 / UTM zone 33N
                    geoDbCrs = QgsCoordinateReferenceSystem(gw.instance().GEODBDEFAULT_SRID)  # WGS 84 / UTM zone 33N
                    xform = QgsCoordinateTransform(defaultCrs, geoDbCrs)
                    if geom.transform(xform):
                        message = self.tr(u"Errore nella conversione della geometria da SRID $d a SRID %d" % (gw.instance().DEFAULT_SRID, gw.instance().GEODBDEFAULT_SRID))
                        self.showMessage(message, QgsMessageLog.WARNING)
                        return
                    the_geom = geom.exportToWkt()
                    
                    # now update geometry related to the saved safety (based on self.saved_id)
                    self.saved_sopralluoghi["the_geom"] = the_geom
                    self.updateSopralluoghi(self.saved_sopralluoghi)
                
                    # wait end of single request
                    while (not self.singleSopralluoghiUpdateFinished and not self.allFinished):
                        qApp.processEvents()
                        time.sleep(0.1)
                        
                    # some other emitted done signal
                    if (self.allFinished):
                        break
                
                # now upload attachments
                attachments = ArchiveManager.instance().loadAttachments(safety["local_id"])
                for attachment in attachments:
                    message = self.tr("Caricando l'allegato: %s" % attachment["attached_file"])
                    self.message.emit(message, QgsMessageLog.INFO)
                    
                    self.uploadAttachment(safety["id"], attachment)
                    
                    # wait end of upload
                    while (not self.singleAttachmentUploadFinished and not self.allFinished):
                        qApp.processEvents()
                        time.sleep(0.1)
                    # some other emitted done signal
                    if (self.allFinished):
                        break
                if (self.allFinished):
                    break
                
                # if safety related to a request set it as done
                
                # notify successful upload of a safety
                message = self.tr("Upload con successo della scheda con local_id: %s - Numero definitivo: %s" % (str(safety["local_id"]), str(safety["number"])))
                self.message.emit(message, QgsMessageLog.CRITICAL)
                
                self.updatedSafeties.append(safety.copy())
                self.onProgress()
 
            if not self.allFinished:
                self.done.emit(True)
            
        except Exception as ex:
            try:
                traceback.print_exc()
            except:
                pass
            self.done.emit(False)
            self.message.emit(ex.message, QgsMessageLog.CRITICAL)
            QApplication.restoreOverrideCursor()
            raise ex
        finally:
            QApplication.restoreOverrideCursor()
    
    def setSingleSafetyUploadFinished(self, success):
        QgsLogger.debug("setSingleSafetyUploadFinished finished with %s" % success, 2 )
        self.singleSafetyUploadFinished = True

    def setSingleSafetyUpdateFinished(self, success):
        QgsLogger.debug("setSingleSafetyUpdateFinished finished with %s" % success, 2 )
        self.singleSafetyUpdateFinished = True

    def setSingleSafetyDuplicationError(self):
        QgsLogger.debug("setSingleSafetyDuplicationError", 2 )
        self.singleSafetyDuplicationErrorReceived = True

    def setSingleAttachmentUploadFinished(self, success):
        QgsLogger.debug("setSingleAttachmentUploadFinished finished with %s" % success, 2 )
        self.singleAttachmentUploadFinished = True

    def setSingleSafetyDownloadFinished(self, success):
        QgsLogger.debug("setSingleSafetyDownloadFinished finished with %s" % success, 2 )
        self.singleSafetyDownloadFinished = True

    def setSingleSopralluoghiDownloadFinished(self, success):
        QgsLogger.debug("setSingleSopralluoghiDownloadFinished finished with %s" % success, 2 )
        self.singleSopralluoghiDownloadFinished = True

    def setSingleSopralluoghiUpdateFinished(self, success):
        QgsLogger.debug("setSingleSopralluoghiUpdateFinished finished with %s" % success, 2 )
        self.singleSopralluoghiUpdateFinished = True

    def setAllFinished(self, success):
        QgsLogger.debug("setAllFinished finished with %s" % success, 2 )
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
        self.currentSafetyUploading = safety
        self.manager.post(request, json.dumps(safety) )
        
        QgsLogger.debug("uploadSafety to url %s with safety %s" % (url.toString(), json.dumps(safety)) ,2 )
        for headerName in request.rawHeaderList():
            QgsLogger.debug("Request header %s = %s" % (headerName, request.rawHeader(headerName)) ,2 )

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
        QgsLogger.debug("downloadRemoteSafety from url %s" % url.toString() ,2 )
        for headerName in request.rawHeaderList():
            QgsLogger.debug("Request header %s = %s" % (headerName, request.rawHeader(headerName)) ,2 )

    def updateSafety(self, safety):
        request = QNetworkRequest()
        request.setRawHeader("Content-Type", "application/json");
        url = QUrl(self.baseApiUrl + self.safetyUrl + str(safety["id"]) + "/")
        
        request.setUrl(url)
        
        # register response manager
        self.manager.finished.connect(self.replyUpdateSafetyFinished)

        # start update
        self.singleSopralluoghiUpdateFinished = False
        safety.pop("id")
        self.manager.put(request, json.dumps(safety) )
        QgsLogger.debug("updateSafety to url %s with safety %s" % (url.toString(), json.dumps(safety)) ,2 )
        for headerName in request.rawHeaderList():
            QgsLogger.debug("Request header %s = %s" % (headerName, request.rawHeader(headerName)) ,2 )

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
        QgsLogger.debug("downloadRemoteSopralluoghi from url %s" % url.toString() ,2 )
        for headerName in request.rawHeaderList():
            QgsLogger.debug("Request header %s = %s" % (headerName, request.rawHeader(headerName)) ,2 )

    def updateSopralluoghi(self, sopralluoghi):
        request = QNetworkRequest()
        request.setRawHeader("Content-Type", "application/json");
        url = QUrl(self.baseApiUrl + self.sopralluoghiUrl + str(sopralluoghi["gid"]) + "/")
        
        request.setUrl(url)
        
        # register response manager
        self.manager.finished.connect(self.replyUpdateSopralluoghiFinished)

        # start update
        self.singleSopralluoghiUpdateFinished = False
        sopralluoghi.pop("gid")
        self.manager.put(request, json.dumps(sopralluoghi) )
        QgsLogger.debug("updateSopralluoghi to url %s with sopralluoghi %s" % (url.toString(), json.dumps(sopralluoghi)) ,2 )
        for headerName in request.rawHeaderList():
            QgsLogger.debug("Request header %s = %s" % (headerName, request.rawHeader(headerName)) ,2 )

    def uploadAttachment(self, safetyRemoteId, attachment):
        
        tempAttachment = attachment.copy()
        # modify attachment values to be as requested by server records
        tempAttachment["safety"] = self.safetyUrl + str(safetyRemoteId) + "/"
        tempAttachment["attached_file"] = os.path.basename(tempAttachment["attached_file"])
        tempAttachment.pop("id")
        tempAttachment.pop("attached_by_id")
        tempAttachment.pop("safety_id")
        
        QgsLogger.debug("uploadAttachment upload of %s" % json.dumps(tempAttachment),2 )

        boundary = "Boundary_.oOo._83uncb3yc7y83yb4ybi93u878278bx7b8789"
        datas = QByteArray()
        # add parameters
        datas += "--" + boundary + "\r\n"
        for name, value in tempAttachment.iteritems():
            if name == "attached_file":
                continue
            datas += 'Content-Disposition: form-data; name="%s"\r\n' % name;
            datas += 'Content-Type: text/plain; charset=utf-8\r\n';
            datas += "\r\n"
            datas += str(value).encode('utf-8')
            datas += "\r\n"
            datas += "--" + boundary + "\r\n"
        
        # add file
        fd = QFile(tempAttachment["attached_file"])
        fd.open(QIODevice.ReadOnly)
        datas += 'Content-Disposition: form-data; name="attached_file"; filename="%s"\r\n' % tempAttachment["attached_file"];
        datas += 'Content-Type: application/octet-stream\r\n';
        datas += "\r\n"
        datas += fd.readAll()
        datas += "\r\n"
        datas += "--" + boundary + "\r\n"
        fd.close()
        
        # build request
        request = QNetworkRequest()
        url = QUrl(self.baseApiUrl + self.attachmentUrl)
        request.setUrl(url)
        request.setRawHeader("Host", url.host())
        request.setRawHeader("Content-type", "multipart/form-data; boundary=%s" % boundary)
        request.setRawHeader("Content-Length", str(datas.size()))
        
        # register response manager
        try:
            self.manager.finished.disconnect()
        except:
            pass
        self.manager.finished.connect(self.replyUploadAttachmentFinished)

        # start upload
#         print "dump request-----------------------------------------------"
#         for headerKey in request.rawHeaderList():
#             print headerKey, request.rawHeader(headerKey)
#         print datas
        self.singleAttachmentUploadFinished = False
        self.manager.post(request, datas)
        QgsLogger.debug("uploadAttachment to url %s with datas %s" % (url.toString(), str(datas)) ,2 )
        for headerName in request.rawHeaderList():
            QgsLogger.debug("Request header %s = %s" % (headerName, request.rawHeader(headerName)) ,2 )
        
    def replyUploadSafetyFinished(self, reply):
        # disconnect current reply callback
        self.manager.finished.disconnect(self.replyUploadSafetyFinished)
        
        # dump headers
        headerKeys = reply.rawHeaderList()
        for headerName in headerKeys:
            QgsLogger.debug("Response header %s = %s" % (headerName, reply.rawHeader(headerName)) ,2 )

        # received error
        if reply.error():
            # check if error is 299 in this case is IntegrityError due the fact that 
            # number+date+team are not unique
            # better dump of error message
            for headerName, rawData in reply.rawHeaderPairs():
                QgsLogger.debug("Reply raw header[%s]: %s" % (headerName, rawData), 2)

            if int(reply.error()) == 299:
                message = self.tr(u"Errore di univocità la scheda con numero %d è già stata usata in questo giorno dallo stesso team") % self.currentSafetyUploading["number"]
                
                # successfully end
                self.singleSafetyDuplicationError.emit()
                return
            else:
                message = self.tr("Errore nella HTTP Request: %d - %s" % (reply.error(), reply.errorString()) )
            self.message.emit(message, QgsMessageLog.WARNING)

            self.done.emit(False)
            return
        
        # well authenticated :)
        gw.instance().autenthicated = True
        gw.instance().authenticationRetryCounter = 0

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
        # disconnect current reply callback
        self.manager.finished.disconnect(self.replyDownloadSafetyFinished)
        
        # dump headers
        headerKeys = reply.rawHeaderList()
        for headerName in headerKeys:
            QgsLogger.debug("Response header %s = %s" % (headerName, reply.rawHeader(headerName)) ,2 )

        # received error
        if reply.error():
            message = self.tr("Errore nella HTTP Request: %d - %s" % (reply.error(), reply.errorString()) )
            self.message.emit(message, QgsMessageLog.WARNING)
            return
        
        # well authenticated :)
        gw.instance().autenthicated = True
        gw.instance().authenticationRetryCounter = 0

        # parse return json
        from json import loads
        raw = reply.readAll()
        try:
            jsonRequest = loads(raw.data())
        except Exception as ex:
            try:
                traceback.print_exc()
            except:
                pass
            self.done.emit(False)
            self.message.emit(ex.message, QgsMessageLog.CRITICAL)
            return
        QgsLogger.debug("replyDownloadSafetyFinished received request %s" % json.dumps(jsonRequest),2 )
        
        # get number of the archived safety
        self.saved_number = jsonRequest["number"]

        message = self.tr("self.saved_number: %s" % self.saved_number )
        self.message.emit(message, QgsMessageLog.INFO)
        
        # successfully end
        self.singleSafetyDownloadDone.emit(True)
        
    def replyUpdateSafetyFinished(self, reply):
        # disconnect current reply callback
        self.manager.finished.disconnect(self.replyUpdateSafetyFinished)
        
        # dump headers
        headerKeys = reply.rawHeaderList()
        for headerName in headerKeys:
            QgsLogger.debug("Response header %s = %s" % (headerName, reply.rawHeader(headerName)) ,2 )

        # received error
        if reply.error():
            message = self.tr("Errore nella HTTP Request: %d - %s" % (reply.error(), reply.errorString()) )
            self.message.emit(message, QgsMessageLog.CRITICAL)
            self.done.emit(False)
            return
        
        # well authenticated :)
        gw.instance().autenthicated = True
        gw.instance().authenticationRetryCounter = 0
        
        # check status code
        statusCode = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        reason = reply.attribute(QNetworkRequest.HttpReasonPhraseAttribute)
        QgsLogger.debug("Response status %s = %s" % (statusCode, reason) ,2 )
        
        # successfully end
        self.singleSafetyUpdateDone.emit(True)

    def replyDownloadSopralluoghiFinished(self, reply):
        # disconnect current reply callback
        self.manager.finished.disconnect(self.replyDownloadSopralluoghiFinished)
        
        # dump headers
        headerKeys = reply.rawHeaderList()
        for headerName in headerKeys:
            QgsLogger.debug("Response header %s = %s" % (headerName, reply.rawHeader(headerName)) ,2 )

        # received error
        if reply.error():
            message = self.tr("Errore nella HTTP Request: %d - %s" % (reply.error(), reply.errorString()) )
            self.message.emit(message, QgsMessageLog.CRITICAL)
            self.done.emit(False)
            return
        
        # well authenticated :)
        gw.instance().autenthicated = True
        gw.instance().authenticationRetryCounter = 0

        # parse json return
        from json import loads
        raw = reply.readAll()
        try:
            jsonRequest = loads(raw.data())
        except Exception as ex:
            try:
                traceback.print_exc()
            except:
                pass
            self.done.emit(False)
            self.message.emit(ex.message, QgsMessageLog.CRITICAL)
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
        # disconnect current reply callback
        self.manager.finished.disconnect(self.replyUpdateSopralluoghiFinished)
        
        # dump headers
        headerKeys = reply.rawHeaderList()
        for headerName in headerKeys:
            QgsLogger.debug("Response header %s = %s" % (headerName, reply.rawHeader(headerName)) ,2 )

        # received error
        if reply.error():
            message = self.tr("Errore nella HTTP Request: %d - %s" % (reply.error(), reply.errorString()) )
            self.message.emit(message, QgsMessageLog.CRITICAL)
            self.done.emit(False)
            return
        
        # well authenticated :)
        gw.instance().autenthicated = True
        gw.instance().authenticationRetryCounter = 0
        
        # check status code
        statusCode = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        reason = reply.attribute(QNetworkRequest.HttpReasonPhraseAttribute)
        QgsLogger.debug("Response status %s = %s" % (statusCode, reason) ,2 )
        
        # successfully end
        self.singleSopralluoghiUpdateDone.emit(True)

    def replyUploadAttachmentFinished(self, reply):
        # disconnect current reply callback
        self.manager.finished.disconnect(self.replyUploadAttachmentFinished)
        
        # dump headers
        headerKeys = reply.rawHeaderList()
        for headerName in headerKeys:
            QgsLogger.debug("Response header %s = %s" % (headerName, reply.rawHeader(headerName)) ,2 )

        # received error
        if reply.error():
            message = self.tr("Errore nella HTTP Request: %d - %s" % (reply.error(), reply.errorString()) )
            self.message.emit(message, QgsMessageLog.CRITICAL)
            self.done.emit(False)
            return
        
        # well authenticated :)
        gw.instance().autenthicated = True
        gw.instance().authenticationRetryCounter = 0
        
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
        
        message = self.tr("Url dell'attachment caricato: %s" % location )
        self.message.emit(message, QgsMessageLog.INFO)

        # successfully end
        self.singleAttachmentUploadDone.emit(True)
