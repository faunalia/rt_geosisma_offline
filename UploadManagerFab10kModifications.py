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
from datetime import datetime
from qgis.core import QgsLogger, QgsMessageLog
from qgis.core import QgsNetworkAccessManager
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *

from GeosismaWindow import GeosismaWindow as gw
from DlgWaiting import DlgWaiting

class UploadManagerFab10kModifications(DlgWaiting):
    
    # signals
    done = pyqtSignal(bool)
    singleFab10kmodUploadDone = pyqtSignal(bool)
    message = pyqtSignal(str, int)

    def __init__(self, parent=None):
        DlgWaiting.__init__(self, parent)
        self.records = None
        self.updatedRecords = None
        self.saved_id = None
        self.manager = QgsNetworkAccessManager.instance();
        # clean listeners to avoid overlap 
        try:
            self.manager.finished.disconnect()
        except:
            pass
        # get connection conf
        settings = QSettings()
        self.fab10kmodUrl = settings.value("/rt_geosisma_offline/fab10kmodUrl", "/api/v1/fab10kmod/")
        self.baseApiUrl = settings.value("/rt_geosisma_offline/baseApiUrl", "http://geosisma.faunalia.it/")
        #self.teamUrl = settings.value("/rt_geosisma_offline/teamUrl", "/api/v1/team/")

    def initRecords(self, records):
        self.records = records
        self.updatedRecords = []
    
    def run(self):
        # in this code I'll try to use semaphorese instead to event to manage sequence of actions
        # as you can see the code is less readable in terms of lenght but it follow a linear workflow
        # using event can crate a more modular and robust code but not linear to read
        try:
            if self.records is None or len(self.records) == 0:
                return
            # init progress bar
            self.reset()
            self.setRange( 0, len(self.records) )
            QApplication.setOverrideCursor(Qt.WaitCursor)

            # set semaphores
            self.done.connect(self.setAllFinished)
            self.singleFab10kmodUploadDone.connect(self.setSingleFab10kmodUploadFinished)
            self.allFinished = False

            # upload records
            for fab10kmod in self.records:
                # check if fab10kmod already uploaded
                if str(fab10kmod["gid"]) != "-1":
                    continue
                
                self.setWindowTitle( self.tr("Upload del record n: %d" % fab10kmod["local_gid"]) )
                # save fab10kmod to a temp fab10kmod because of need of modification befor to upload
                fab10kmodToUpload = fab10kmod.copy()
                
                # save plygon data to be saved after saving current fab10kmod
                gids = fab10kmodToUpload.pop("gid")
                local_gid = fab10kmodToUpload.pop("local_gid")
                fab10kmodToUpload["team_id"] = int(fab10kmodToUpload["team_id"])
                
                # set semaphore status for a single fab10kmod management
                self.singleFab10kmodUploadFinished = False

                # upload
                self.saved_id = None
                fab10kmodToUpload["upload_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                self.uploadFab10kmod(fab10kmodToUpload)
            
                # wait end of single request
                while (not self.singleFab10kmodUploadFinished and not self.allFinished):
                    qApp.processEvents()
                    time.sleep(0.1)
                    
                # some other emitted done signal
                if (self.allFinished):
                    break
                    
                if self.saved_id is None:
                    message = self.tr("Non riesco a determinare l'id della record appena caricata sul server - id: %d" % fab10kmod["local_gid"])
                    self.message.emit(message, QgsMessageLog.CRITICAL)
                    self.done.emit(False)
                    break
                
                # update current saved fab10kmod with new id and upload time
                fab10kmod["upload_time"] = fab10kmodToUpload["upload_time"]
                fab10kmod["gid"] = self.saved_id

                # notify successful upload of a fab10kmod
                message = self.tr("Upload con successo del record con local_gid: %s - Id definitivo: %s" % (str(fab10kmod["local_gid"]), str(fab10kmod["gid"])))
                self.message.emit(message, QgsMessageLog.CRITICAL)
                
                self.updatedRecords.append(fab10kmod.copy())
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
    
    def setSingleFab10kmodUploadFinished(self, success):
        QgsLogger.debug("setSingleFab10kmodUploadFinished finished with %s" % success, 2 )
        self.singleFab10kmodUploadFinished = True

    def setAllFinished(self, success):
        QgsLogger.debug("setAllFinished finished with %s" % success, 2 )
        self.allFinished = True

    def uploadFab10kmod(self, fab10kmod):
        request = QNetworkRequest()
        request.setRawHeader("Content-Type", "application/json");
        url = QUrl(self.baseApiUrl + self.fab10kmodUrl)
        
        request.setUrl(url)
        
        # add new listeners
        try:
            self.manager.finished.disconnect()
        except:
            pass
        self.manager.finished.connect(self.replyUploadFab10kmodFinished)

        # start upload
        self.singleFab10kmodUploadFinished = False
        self.manager.post(request, json.dumps(fab10kmod) )
        QgsLogger.debug("uploadFab10kmod to url %s with fab10kmod %s" % (url.toString(), json.dumps(fab10kmod)) ,2 )

    def replyUploadFab10kmodFinished(self, reply):
        # disconnect current reply callback
        self.manager.finished.disconnect(self.replyUploadFab10kmodFinished)
        
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
        
        # get id of the archived fab10kmod
        self.saved_id = os.path.split(os.path.split( location )[0])[1]

        message = self.tr("self.saved_id: %s - %s" % (self.saved_id, location) )
        self.message.emit(message, QgsMessageLog.INFO)
        
        # successfully end
        self.singleFab10kmodUploadDone.emit(True)

