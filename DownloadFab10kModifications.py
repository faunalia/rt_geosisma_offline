# -*- coding: utf-8 -*-
import os, json, traceback, time
from qgis.core import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *

from DlgWaiting import DlgWaiting
from GeosismaWindow import GeosismaWindow as gw

# SpatiaLite imports
from pyspatialite import dbapi2 as db

class DownloadFab10kModifications(DlgWaiting):
    
    # signals
    done = pyqtSignal(bool)
    singleDone = pyqtSignal(bool)
    message = pyqtSignal(str, int)

    def __init__(self, parent=None, bbox=None):
        DlgWaiting.__init__(self, parent)
        self.singleFinished = True
        self.allFinished = True
        
        self.jsonFab10kModifications = None
        self.bbox = bbox # as QgsRectangle
        
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
            # init progress bar
            self.reset()
            self.setWindowTitle( self.tr("Scarica le modifiche a %s" % gw.instance().LAYER_GEOM_FAB10K ))
            self.setRange( 0, 1 )
            QApplication.setOverrideCursor(Qt.WaitCursor)

            # set semaphores
            self.done.connect(self.setAllFinished)
            self.singleDone.connect(self.setSingleFinished)

            # for each request api
            self.allFinished = False

            # create db
            self.jsonRequest = None
            self.singleFinished = False
            self.DownloadFab10kModifications()
            
            # whait end of single request
            while (not self.singleFinished):
                qApp.processEvents()
                time.sleep(0.1)
            
            # archive request in self.downloadedTeams
            #self.downloadedTeams[index]["downloadedRequests"][requestApi] = self.jsonFab10kModifications
            #self.downloadedRequests.append(self.jsonFab10kModifications)
            
            self.onProgress()
            
            # some other emitted done signal
            if (self.allFinished):
                return
            
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

    def DownloadFab10kModifications(self):
        
        # get connection conf
        settings = QSettings()
        fab10kmodUrl = settings.value("/rt_geosisma_offline/fab10kmodUrl", "/api/v1/fab10kmod/")
        self.baseApiUrl = settings.value("/rt_geosisma_offline/baseApiUrl", "http://geosisma-test.faunalia.it/")

        # create json parametr for the bbox... without using geojson pytion module to avoid dependency
        geojsonbbox = """{type: "Polygon", coordinates: [[[%(minx)s, %(miny)s], [%(minx)s, %(maxy)s], [%(maxy)s, %(maxy)s], [%(maxx)s, %(miny)s]]], crs: {"type": "name", "properties": {"name": "EPSG:%(srid)s"}}}"""
        geojsonbbox = geojsonbbox % { "minx":self.bbox.xMinimum(), "miny":self.bbox.yMinimum(), "maxx":self.bbox.xMaximum(), "maxy":self.bbox.yMaximum(), "srid":gw.instance().DEFAULT_SRID }

        print geojsonbbox

        # for each request api
        request = QNetworkRequest()
        url = QUrl(self.baseApiUrl + fab10kmodUrl)
        url.addQueryItem("poly__contains", geojsonbbox )
        url.addQueryItem("format", "json")
        request.setUrl(url)
        
        message = self.tr("Download %s with query: %s and bbox: %s" % (gw.instance().LAYER_GEOM_FAB10K_MODIF, url.toString(), geojsonbbox ) )
        self.message.emit(message, QgsMessageLog.INFO)

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
        print raw
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
            jsonFab10kModifications = json["objects"] # get array of dicts
        else:
            jsonFab10kModifications = [json]
        for modification in jsonFab10kModifications:
            gw.instance().fab10kModifications.append(modification)
        
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

        #gw.instance().downloadedRequests.append(jsonFab10kModifications)
        
        # successfully end
        self.singleDone.emit(True)
