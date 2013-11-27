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
from qgis.core import QgsLogger, QgsMessageLog, QgsCredentials
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *

from GeosismaWindow import GeosismaWindow as gw
from DlgWaiting import DlgWaiting

class UploadManager(DlgWaiting):
    
    # signals
    done = pyqtSignal(bool)
    message = pyqtSignal(str, int)

    def __init__(self, parent=None):
        DlgWaiting.__init__(self, parent)
    
    def initSafeties(self, safeties):
        self.safeties = safeties
    
    def run(self):
        try:
            # init progress bar
            self.reset()
            
            self.setRange( 0, 0 )
            QApplication.setOverrideCursor(Qt.WaitCursor)

            settings = QSettings()
            teamUrl = settings.value("/rt_geosisma_offline/teamUrl", "/api/v1/team/")
            requestUrl = settings.value("/rt_geosisma_offline/requestUrl", "/api/v1/request/")

            # upload safeties
            for safety in self.safeties:
                self.setWindowTitle( self.tr("Upload della scheda n: %d" % safety["number"]) )
                # save plygon data to be saved after saving current safety
                geometry = safety.pop("the_geom")
                gids = safety.pop("gid_catasto")
                id = safety.pop("id")
                uploaded = safety.pop("uploaded")
                
                # prepare safety to send
                safety["team"] = teamUrl + "/" + safety["team_id"] + "/"
                if "request_id" in safety:
                    safety["request"] = requestUrl + "/" + safety["request_id"] + "/"
                
                # upload
                self.uploadSafety(safety)
            
        except Exception as e:
            traceback.print_exc()
            self.done.emit(False)
            self.message.emit(e.message, QgsMessageLog.CRITICAL)
            QApplication.restoreOverrideCursor()
            raise e
        finally:
            QApplication.restoreOverrideCursor()
    
    def uploadSafety(self, safety):
        # get connection conf
        settings = QSettings()
        safetyUrl = settings.value("/rt_geosisma_offline/safetyUrl", "/api/v1/safety/")
        sopralluoghiUrl = settings.value("/rt_geosisma_offline/safetyUrl", "/api/v1/sopralluoghi/")
        self.baseApiUrl = settings.value("/rt_geosisma_offline/baseApiUrl", "http://geosisma-test.faunalia.it/")

        self.manager = QNetworkAccessManager(self);
        
        self.manager.finished.connect(self.replyFinished)
        self.manager.authenticationRequired.connect(self.authenticationRequired)
        
        QByteArray 

        request = QNetworkRequest()
        request.setRawHeader("Content-Type", "application/json");
        url = QUrl(self.baseApiUrl + safetyUrl)
        
        request.setUrl(url)
        
        # start download
        QApplication.setOverrideCursor(Qt.WaitCursor)
        print safety
        print json.dumps(safety)
        self.manager.post(request, json.dumps(safety) )

        self.singleFinished = False
        self.onProgress()

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

    def replyFinished(self, reply):
        
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
        
        self.onProgress()
        
        # well authenticated :)
        gw.instance().autenthicated = True
        gw.instance().authenticationRetryCounter = 0

        from json import loads
        raw = reply.readAll()
        
        print raw
        
        # successfully end
        self.done.emit(True)
