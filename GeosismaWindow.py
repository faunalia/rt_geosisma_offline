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
import os
import json # used to dump dicts in strings
import ast # used to convert string indict because json.loads could fail
import inspect
from datetime import date
from psycopg2.extensions import adapt

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *

from Utils import *
# import cache manager
from DlgWmsLayersManager import DlgWmsLayersManager, WmsLayersBridge

currentPath = os.path.dirname(__file__)

class GeosismaWindow(QDockWidget):

    # signals
    downloadTeamsDone = pyqtSignal(bool)
    archiveTeamsDone = pyqtSignal(bool)
    downloadRequestsDone = pyqtSignal(bool)
    uploadSafetiesDone = pyqtSignal(bool)
    selectRequestDone = pyqtSignal()
    updatedCurrentSafety = pyqtSignal()
    initNewCurrentSafetyDone = pyqtSignal()

    # static global vars
    MESSAGELOG_CLASS = "rt_geosisma_offline"
    GEOSISMA_DBNAME = "geosismadb.sqlite"
    GEOSISMA_GEODBNAME = "geosisma_geo.sqlite"
    DEFAULT_SRID = 3003
    GEODBDEFAULT_SRID = 32632

    # nomi dei layer in TOC
    LAYER_GEOM_ORIG = "Geometrie Originali"
    LAYER_GEOM_MODIF = "Geometrie Schede"
    LAYER_GEOM_FAB10K = "Codici Aggregati"
    LAYER_FOTO = "Foto Edifici"

    # stile per i layer delle geometrie
    STYLE_FOLDER = "styles"
    STYLE_GEOM_ORIG = "stile_geometrie_originali.qml"
    STYLE_GEOM_MODIF = "stile_geometrie_modificate.qml"
    STYLE_GEOM_FAB10K = "stile_geometrie_aggregati.qml"
    STYLE_FOTO = "stile_fotografie.qml"

    SCALE_IDENTIFY = 5000
    SCALE_MODIFY = 2000

    # nomi tabelle contenenti le geometrie
    TABLE_GEOM_ORIG = "fab_catasto".lower()
    TABLE_GEOM_MODIF = "missions_safety".lower()
    TABLE_GEOM_FAB10K = "fab_10k".lower()

    # ID dei layer contenenti geometrie e wms
    VLID_GEOM_ORIG = ''
    VLID_GEOM_MODIF = ''
    VLID_GEOM_FAB10K = ''
    VLID_FOTO = ''
    RLID_WMS = {}

    _instance = None
    
    # singleton interface
    @classmethod
    def instance(cls, parent=None, iface=None):
        '''
        Singleton interface
        @param parent: passed to init() function
        @param dbName: passed to init() function
        
        '''
        if cls._instance == None:
            cls._instance = GeosismaWindow()
            cls._instance.init(parent, iface)
        return cls._instance

    def __init__(self):
        pass
    
    def cleanUp(self):
        try:
            from ArchiveManager import ArchiveManager
            ArchiveManager.instance().cleanUp()
        except:
            pass

        try:
            if self.safetyDlg is not None:
                self.safetyDlg.deleteLater()
            self.safetyDlg = None
        except:
            pass
        
        try:
            GeosismaWindow._instance = None
        except:
            pass
    
    def init(self, parent=None, iface=None):
        QDockWidget.__init__(self, parent)
        QObject.connect(self, SIGNAL("destroyed()"), self.cleanUp)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setupUi()
        
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.safetyDlg = None
        self.isApriScheda = True
        self.srid = GeosismaWindow.DEFAULT_SRID

        # get bds path
        self.settings = QSettings()
        dbsPath = self.settings.value("/rt_geosisma_offline/pathToDbs", "./offlinedata/dbs/")
        if not os.path.isabs(dbsPath):
            currentpath = os.path.dirname(os.path.abspath(inspect.getfile( inspect.currentframe() )))
            dbsPath = os.path.join(currentpath, dbsPath)
        self.DATABASE_OUTNAME = os.path.join(dbsPath, GeosismaWindow.GEOSISMA_DBNAME)
        self.GEODATABASE_OUTNAME = os.path.join(dbsPath, GeosismaWindow.GEOSISMA_GEODBNAME)
        QgsLogger.debug(self.tr("Default dbname: %s" % self.DATABASE_OUTNAME) )
        QgsLogger.debug(self.tr("Default geodbname: %s" % self.GEODATABASE_OUTNAME) )
        
        # get default srid
        self.DEFAULT_SRID = self.settings.value("/rt_geosisma_offline/safetyDbDefaultSrid", self.DEFAULT_SRID, int )
        self.GEODBDEFAULT_SRID = self.settings.value("/rt_geosisma_offline/geoDbDefaultSrid", self.GEODBDEFAULT_SRID, int )
        QgsLogger.debug(self.tr("Default srid: %d" % self.DEFAULT_SRID) )
        
        #geosisma api connection data
        self.user = None
        self.pwd = None
        self.autenthicated = False
        self.maxAuthenticationError = 5
        self.authenticationRetryCounter = 0
        
        # list of dict of requests, tems and safeties
        self.requests = []
        self.currentRequest = None
        self.downloadedTeams = []
        self.downloadedRequests = []
        self.currentSafety = None
        self.safeties = []
        self.teams = None
        
        MapTool.canvas = self.canvas

        self.nuovaPointEmitter = FeatureFinder()
        self.nuovaPointEmitter.registerStatusMsg( u"Click per identificare la geometria da associare alla nuova scheda" )
        QObject.connect(self.nuovaPointEmitter, SIGNAL("pointEmitted"), self.linkSafetyGeometry)

        self.connect(self.btnNewSafety, SIGNAL("clicked()"), self.initNewCurrentSafety)
        self.connect(self.btnModifyCurrentSafety, SIGNAL("clicked()"), self.updateSafetyForm)
        self.connect(self.btnDeleteCurrentSafety, SIGNAL("clicked()"), self.deleteCurrentSafety)
        self.connect(self.btnSelectSafety, SIGNAL("clicked()"), self.selectSafety)
        self.connect(self.btnSelectRequest, SIGNAL("clicked()"), self.selectRequest)
        self.connect(self.btnDownloadRequests, SIGNAL("clicked()"), self.downloadTeams)
        self.connect(self.btnReset, SIGNAL("clicked()"), self.reset)
        
        self.connect(self.btnLinkSafetyGeometry, SIGNAL("clicked()"), self.linkSafetyGeometry)
        self.connect(self.btnManageAttachments, SIGNAL("clicked()"), self.manageAttachments)

#         self.connect(self.btnAbout, SIGNAL("clicked()"), self.about)
        
        # custom signal
        self.downloadTeamsDone.connect(self.archiveTeams)
        self.archiveTeamsDone.connect(self.downloadRequests)
        self.downloadRequestsDone.connect( self.archiveRequests )
        self.updatedCurrentSafety.connect(self.updateSafetyForm)
        self.updatedCurrentSafety.connect(self.updateArchivedCurrentSafety)
        self.updatedCurrentSafety.connect(self.repaintSafetyGeometryLayer)
        
        # GUI state based on signals
        self.selectRequestDone.connect(self.manageGuiStatus)
        self.updatedCurrentSafety.connect(self.manageGuiStatus)
        
        self.manageGuiStatus()

#         self.connect(self.iface, SIGNAL("newProjectCreated()"), self.close)

    def setupUi(self):
        self.setObjectName( "rt_geosisma_dockwidget" )
        self.setWindowTitle( "Geosisma Offline RT" )

        child = QWidget()
        vLayout = QVBoxLayout( child )


        group = QGroupBox( "Schede Sopralluoghi", child )
        vLayout.addWidget( group )
        gridLayout = QGridLayout( group )

        text = u"Nuova"
        self.btnNewSafety = QPushButton( QIcon(":/icons/nuova_scheda.png"), text, group )
        #text = u"Identifica la geometria per la creazione di una nuova scheda edificio"
        text = u"Crea una nuova scheda sopralluogo"
        self.btnNewSafety.setToolTip( text )
        #self.btnNewSafety.setCheckable(True)
        gridLayout.addWidget(self.btnNewSafety, 0, 0, 1, 1)

        text = u"Modifica"
        self.btnModifyCurrentSafety = QPushButton( QIcon(":/icons/modifica_scheda.png"), text, group )
        #text = u"Identifica la geometria per l'apertura di una scheda gia' esistente su di essa"
        text = u"Modifica scheda sopralluogo corrente"
        self.btnModifyCurrentSafety.setToolTip( text )
        #self.btnModifyCurrentSafety.setCheckable(True)
        gridLayout.addWidget(self.btnModifyCurrentSafety, 0, 1, 1, 1)

        text = u"Elimina"
        self.btnDeleteCurrentSafety = QPushButton( QIcon(":/icons/cancella_scheda.png"), text, group )
        text = u"Elimina scheda sopralluogo"
        self.btnDeleteCurrentSafety.setToolTip( text )
        #self.btnDeleteCurrentSafety.setCheckable(True)
        gridLayout.addWidget(self.btnDeleteCurrentSafety, 0, 2, 1, 1)

        text = u"Seleziona Scheda"
        self.btnSelectSafety = QPushButton( QIcon(":/icons/riepilogo_schede.png"), text, group )
        self.btnSelectSafety.setToolTip( text )
        gridLayout.addWidget(self.btnSelectSafety, 1, 0, 1, 3)

        text = u"Seleziona Sopralluogo"
        self.btnSelectRequest = QPushButton( QIcon(":/icons/riepilogo_schede.png"), text, group )
        self.btnSelectRequest.setToolTip( text )
        gridLayout.addWidget(self.btnSelectRequest, 2, 0, 1, 3)

        text = u"Download Sopralluoghi"
        self.btnDownloadRequests = QPushButton( QIcon(":/icons/riepilogo_schede.png"), text, group )
        self.btnDownloadRequests.setToolTip( text )
        gridLayout.addWidget(self.btnDownloadRequests, 3, 0, 1, 2)

        text = u"Reset"
        self.btnReset = QPushButton( QIcon(":/icons/riepilogo_schede.png"), text, group )
        self.btnReset.setToolTip( text )
        gridLayout.addWidget(self.btnReset, 3, 2, 1, 1)


        group = QGroupBox( "Geometrie e allegati", child )
        vLayout.addWidget( group )
        gridLayout = QGridLayout( group )

        text = u"Associa particella"
        self.btnLinkSafetyGeometry = QPushButton( QIcon(":/icons/crea_geometria.png"), text, group )
        text = u"Seleziona una particella da associare alla scheda"
        self.btnLinkSafetyGeometry.setToolTip( text )
        self.btnLinkSafetyGeometry.setCheckable(True)
        gridLayout.addWidget(self.btnLinkSafetyGeometry, 0, 0, 1, 1)

        text = u"Gestisci allegati"
        self.btnManageAttachments = QPushButton( QIcon(":/icons/crea_geometria.png"), text, group )
        text = u"Aggiuinta e rimozione degli allegati alla scheda corrente"
        self.btnManageAttachments.setToolTip( text )
        gridLayout.addWidget(self.btnManageAttachments, 1, 0, 1, 1)

#         text = u"About"
#         self.btnAbout = QPushButton( QIcon(":/icons/about.png"), text, child )
#         self.btnAbout.setToolTip( text )
#         vLayout.addWidget( self.btnAbout )
#         #gridLayout.addWidget(self.btnAbout, 7, 1, 1, 1)

        self.setWidget(child)

    def exec_(self):
        if not self.startPlugin():
            return False
        
#         # load test data to test functions
#         self.settings = QSettings()
#         dbsPath = self.settings.value("/rt_geosisma_offline/pathToDbs", "./offlinedata/dbs/")
#         path = dbsPath + '/../../doc/downloadedTeams+downloadedRequests.json'
#         json_data=open(path)
#         data = json.load(json_data)
#         self.downloadedTeams = data
#         self.archiveRequests(True)
#         return
#         from ArchiveManager import ArchiveManager # import here to avoid circular import
#         req = ArchiveManager.instance().loadRequests([533, 554])
#         print req
#         return

#         dbsPath = self.settings.value("/rt_geosisma_offline/pathToDbs", "./offlinedata/dbs/")
#         path = dbsPath + '/../../doc/downloadedSafeties.json'
#         with open(path,'r') as inf:
#             dict_from_file = eval(inf.read())
#         from ArchiveManager import ArchiveManager
#         for safety in dict_from_file["objects"]:
#             
#             for k,v in safety.items():
#                 print k,v
#             print "------------------"
#             ArchiveManager.instance().archiveSafety(None, "123", safety)
#         ArchiveManager.instance().commit()
#         return

#         self.currentSafety = {u'created': u'2013-11-21', u'gid_catasto': None, u'number': 2, u'team_id': 123, u'safety': u'{"s1istatprov":"045","s1istatcom":"004","sdate":"21/11/2013","number":2,"s1catfoglio":"24","s1com":"Casola in Lunigiana","s1istatcens":"001","s1istatloc":"10003","s1istatreg":"009","s1loc":"Casola in Lunigiana","s1prov":"MS","s1catpart1":"966"}', u'request_id': 51, u'date': u'2013-11-21', u'the_geom': None, u'id': 2}
#         self.updatedCurrentSafety.emit()
#        return
        self.reloadCrs()
        
        # load all the layers from db
        self.wmsLayersBridge = WmsLayersBridge(self.iface, self.showMessage)
        self.wmsLayersBridge.instance.offlineMode = True
        firstTime = True
        if not DlgWmsLayersManager.loadWmsLayers(firstTime): # static method
            message = self.tr("Impossibile caricare i layer WMS")
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            # continue

        self.loadLayerGeomOrig()
        self.loadFab10kGeometries()
        self.loadSafetyGeometries()

        return True

    def reloadCrs(self):
        #self.srid = self.getSridFromDb()
        self.srid = self.DEFAULT_SRID
        srs = QgsCoordinateReferenceSystem( self.srid, QgsCoordinateReferenceSystem.EpsgCrsId )
        renderer = self.canvas.mapRenderer()
        self._setRendererCrs(renderer, srs)
        renderer.setMapUnits( srs.mapUnits() if srs.mapUnits() != QGis.UnknownUnit else QGis.Meters )
        renderer.setProjectionsEnabled(True)

    def loadLayerGeomOrig(self):
        # skip if already present
        layers = QgsMapLayerRegistry.instance().mapLayersByName(self.LAYER_GEOM_ORIG)
        if len(layers) > 0:
            # get id of the Geosisma layer
            valid = False
            for layer in layers:
                prop = layer.customProperty( "loadedByGeosismaRTPlugin" )
                if prop == "VLID_GEOM_ORIG":
                    valid = True
                    GeosismaWindow.VLID_GEOM_ORIG = self._getLayerId( layer )
            if not valid:
                message = self.tr("Manca il layer %s, ricaricando il plugin verrà caricato automaticamente" % self.LAYER_GEOM_ORIG)
                self.showMessage(message, QgsMessageLog.CRITICAL)
                QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            return
        # carica il layer con le geometrie originali
        if QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_ORIG ) == None:
            GeosismaWindow.VLID_GEOM_ORIG = ''

            uri = QgsDataSourceURI()
            uri.setDatabase(self.GEODATABASE_OUTNAME)
            uri.setDataSource('', self.TABLE_GEOM_ORIG, 'the_geom')
            vl = QgsVectorLayer( uri.uri(), self.LAYER_GEOM_ORIG, "spatialite" )
            if vl == None or not vl.isValid() or not vl.setReadOnly(True):
                return False

            # imposta lo stile del layer
            style_path = os.path.join( currentPath, GeosismaWindow.STYLE_FOLDER, GeosismaWindow.STYLE_GEOM_ORIG )
            errorMsg, success= vl.loadNamedStyle( style_path )
            if not success:
                message = self.tr("Non posso caricare lo stile %s - %s: %s" % (GeosismaWindow.STYLE_GEOM_ORIG, errorMsg, style_path) )
                self.showMessage(message, QgsMessageLog.CRITICAL)
                QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            self.iface.legendInterface().refreshLayerSymbology(vl)

            GeosismaWindow.VLID_GEOM_ORIG = self._getLayerId(vl)
            self._addMapLayer(vl)
            # set custom property
            vl.setCustomProperty( "loadedByGeosismaRTPlugin", "VLID_GEOM_ORIG" )
        return True
    
    def loadSafetyGeometries(self):
        # skip if already present
        layers = QgsMapLayerRegistry.instance().mapLayersByName(self.LAYER_GEOM_MODIF)
        if len(layers) > 0:
            # get id of the Geosisma layer
            valid = False
            for layer in layers:
                prop = layer.customProperty( "loadedByGeosismaRTPlugin" )
                if prop == "VLID_GEOM_MODIF":
                    valid = True
                    GeosismaWindow.VLID_GEOM_MODIF = self._getLayerId( layer )
            if not valid:
                message = self.tr("Manca il layer %s, ricaricando il plugin verrà caricato automaticamente" % self.LAYER_GEOM_MODIF)
                self.showMessage(message, QgsMessageLog.CRITICAL)
                QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            return
        # carica il layer con le geometrie delle safety
        if QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_MODIF ) == None:
            GeosismaWindow.VLID_GEOM_MODIF = ''

            uri = QgsDataSourceURI()
            uri.setDatabase(self.DATABASE_OUTNAME)
            uri.setDataSource('', self.TABLE_GEOM_MODIF, 'the_geom')
            vl = QgsVectorLayer( uri.uri(), self.LAYER_GEOM_MODIF, "spatialite" )
            if vl == None or not vl.isValid():
                return False

            # imposta lo stile del layer
            style_path = os.path.join( currentPath, GeosismaWindow.STYLE_FOLDER, GeosismaWindow.STYLE_GEOM_MODIF )
            errorMsg, success= vl.loadNamedStyle( style_path )
            if not success:
                message = self.tr("Non posso caricare lo stile %s - %s: %s" % (GeosismaWindow.STYLE_GEOM_MODIF, errorMsg, style_path) )
                self.showMessage(message, QgsMessageLog.CRITICAL)
                QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            self.iface.legendInterface().refreshLayerSymbology(vl)

            GeosismaWindow.VLID_GEOM_MODIF = self._getLayerId(vl)
            self._addMapLayer(vl)
            # set custom property
            vl.setCustomProperty( "loadedByGeosismaRTPlugin", "VLID_GEOM_MODIF" )
        return True

    def loadFab10kGeometries(self):
        # skip if already present
        layers = QgsMapLayerRegistry.instance().mapLayersByName(self.LAYER_GEOM_FAB10K)
        if len(layers) > 0:
            # get id of the Geosisma layer
            valid = False
            for layer in layers:
                prop = layer.customProperty( "loadedByGeosismaRTPlugin" )
                if prop == "VLID_GEOM_FAB10K":
                    valid = True
                    GeosismaWindow.VLID_GEOM_FAB10K = self._getLayerId( layer )
            if not valid:
                message = self.tr("Manca il layer %s, ricaricando il plugin verrà caricato automaticamente" % self.LAYER_GEOM_FAB10K)
                self.showMessage(message, QgsMessageLog.CRITICAL)
                QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            return
        # carica il layer con le geometrie delle safety
        if QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_FAB10K ) == None:
            GeosismaWindow.VLID_GEOM_FAB10K = ''

            uri = QgsDataSourceURI()
            uri.setDatabase(self.GEODATABASE_OUTNAME)
            uri.setDataSource('', self.TABLE_GEOM_FAB10K, 'the_geom')
            vl = QgsVectorLayer( uri.uri(), self.LAYER_GEOM_FAB10K, "spatialite" )
            if vl == None or not vl.isValid():
                return False

            # imposta lo stile del layer
            style_path = os.path.join( currentPath, GeosismaWindow.STYLE_FOLDER, GeosismaWindow.STYLE_GEOM_FAB10K )
            errorMsg, success= vl.loadNamedStyle( style_path )
            if not success:
                message = self.tr("Non posso caricare lo stile %s - %s: %s" % (GeosismaWindow.STYLE_GEOM_FAB10K, errorMsg, style_path) )
                self.showMessage(message, QgsMessageLog.CRITICAL)
                QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            self.iface.legendInterface().refreshLayerSymbology(vl)

            GeosismaWindow.VLID_GEOM_FAB10K = self._getLayerId(vl)
            self._addMapLayer(vl)
            # set custom property
            vl.setCustomProperty( "loadedByGeosismaRTPlugin", "VLID_GEOM_FAB10K" )
        return True

    def showMessage(self, message, messagetype):
        QgsMessageLog.logMessage(message, GeosismaWindow.MESSAGELOG_CLASS, messagetype)
        #self.ui.logLabel.setText(message)

    def startPlugin(self):
        # try to restore position from stored main window state
        if not self.iface.mainWindow().restoreDockWidget(self):
            self.iface.mainWindow().addDockWidget(Qt.LeftDockWidgetArea, self)
        # force show even if it was restored as hidden
        self.show()
        self.activateWindow()
        self.raise_()
        QApplication.processEvents( QEventLoop.ExcludeUserInputEvents )

        return True

    def about(self):
        if self.canvas.isDrawing():
            return    # wait until the renderer ends
#         from DlgAbout import DlgAbout
#         DlgAbout(self).exec_()

    def reset(self):
        self.user = None
        self.pwd = None
        self.autenthicated = False
        self.authenticationRetryCounter = 0
        
        # close Archive db is opened
        from ArchiveManager import ArchiveManager
        ArchiveManager.instance().cleanUp()
        
        # remove layer of safety geometrys and reload it
        self._removeMapLayer(self.VLID_GEOM_MODIF)
        
        # now reset db
        from ResetDB import ResetDB
        self.resetDbDlg = ResetDB()
        self.resetDbDlg.resetDone.connect( self.manageEndResetDbDlg )
        self.resetDbDlg.exec_()
        
        # reload safety geometrys layer
        self.loadSafetyGeometries()
        
        # reset some important globals
        self.requests = []
        self.currentRequest = None
        self.downloadedTeams = []
        self.downloadedRequests = []
        self.teams = None
        self.currentSafety = None
        self.updatedCurrentSafety.emit()

    def manageEndResetDbDlg(self, success):
        self.resetDbDlg.hide()

        QApplication.restoreOverrideCursor()
        if not success:
            message = self.tr("Fallito il reset del database. Controlla il Log")
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        else:
            message = self.tr("Reset avvenuto con successo")
            self.showMessage(message, QgsMessageLog.INFO)
            QMessageBox.information(self, GeosismaWindow.MESSAGELOG_CLASS, message)

        if self.resetDbDlg:
            self.resetDbDlg.deleteLater()
        self.resetDbDlg = None

    def downloadTeams(self):
        self.downloadedTeams = []
        from DownloadTeams import DownloadTeams
        self.downloadTeamsDlg = DownloadTeams()
        self.downloadTeamsDlg.done.connect( self.manageEndDownloadTeamsDlg )
        self.downloadTeamsDlg.message.connect(self.showMessage)
        self.downloadTeamsDlg.exec_()
    
    def manageEndDownloadTeamsDlg(self, success):
        if self.downloadTeamsDlg is None:
            return
        self.downloadTeamsDlg.hide()

        QApplication.restoreOverrideCursor()
        if not success:
            message = self.tr("Fallito lo scaricamento dei teams. Controlla il Log")
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        else:
            message = self.tr("Scaricate i dati di %d teams" % self.downloadedTeams.__len__())
            self.showMessage(message, QgsMessageLog.INFO)
        
        # notify end of download
        self.downloadTeamsDone.emit(success)
        
        if self.downloadTeamsDlg:
            self.downloadTeamsDlg.deleteLater()
        self.downloadTeamsDlg = None

    def archiveTeams(self, success):
        if not success:
            return
        
        QgsLogger.debug(self.tr("Dump di Teams e Requests scaricate: %s" % json.dumps( self.downloadedTeams )) )
        try:
            from ArchiveManager import ArchiveManager # import here to avoid circular import
            ArchiveManager.instance().saveAll = False
            for team in self.downloadedTeams:
                ArchiveManager.instance().archiveTeam(team)
                ArchiveManager.instance().commit()

            self.archiveTeamsDone.emit(success)
            
        except Exception:
            traceback.print_exc()
            ArchiveManager.instance().close() # to avoid locking
            traceback.print_exc()
            message = self.tr("Fallito l'archiviazione dei team")
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        finally:
            ArchiveManager.instance().close() # to avoid locking

    def downloadRequests(self, success):
        if not success:
            return
        
        # get all sopralluoghiRequests
        for index,team in enumerate(self.downloadedTeams):
            # add a dict of dict with all requests to be donwloaded
            # key will be the request api
            self.downloadedTeams[index]["downloadedRequests"] = {}
            
            for request in team["requests"]:
                self.downloadedTeams[index]["downloadedRequests"][request] = None
        
        # download all requests
        self.downloadedRequests = []
        from DownloadRequests import DownloadRequests
        self.downloadRequestsDlg = DownloadRequests()
        self.downloadRequestsDlg.done.connect( self.manageEndDownloadRequestsDlg )
        self.downloadRequestsDlg.message.connect(self.showMessage)
        self.downloadRequestsDlg.exec_()
        
    def manageEndDownloadRequestsDlg(self, success):
        if self.downloadRequestsDlg is None:
            return
        self.downloadRequestsDlg.hide()

        QApplication.restoreOverrideCursor()
        if not success:
            message = self.tr("Fallito lo scaricamento delle richieste sopralluogo. Controlla il Log")
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        else:
            message = self.tr("Scaricate %s schede soralluoghi" % self.downloadedRequests.__len__())
            self.showMessage(message, QgsMessageLog.INFO)
            QMessageBox.information(self, GeosismaWindow.MESSAGELOG_CLASS, message)

        # notify end of download
        self.downloadRequestsDone.emit(success)
        
        if self.downloadRequestsDlg:
            self.downloadRequestsDlg.deleteLater()
        self.downloadRequestsDlg = None

    def archiveRequests(self, success):
        if not success:
            return
        
        #QgsLogger.debug(self.tr("Dump di Teams e Requests scaricate: %s" % json.dumps( self.downloadedTeams )), 2 )
        try:
            from ArchiveManager import ArchiveManager # import here to avoid circular import
            ArchiveManager.instance().saveAll = False
            for team in self.downloadedTeams:
                # get event_id and team_id from meta
                team_id = team["id"]
                #team_name = team["name"]
        
                for request in team["downloadedRequests"].values():
                    ArchiveManager.instance().archiveRequest(team_id, request)
                    ArchiveManager.instance().commit()

            
        except Exception:
            traceback.print_exc()
            ArchiveManager.instance().close() # to avoid locking
            traceback.print_exc()
            message = self.tr("Fallito l'archiviazione delle richieste di sopralluogo")
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        finally:
            ArchiveManager.instance().close() # to avoid locking

    def selectRequest(self):
        from DlgSelectRequest import DlgSelectRequest
        dlg = DlgSelectRequest()
        ret = dlg.exec_()
        # check if result set
        if ret == 0:
            return
        # get selected request
        self.currentRequest = dlg.currentRequest
        self.requests = dlg.records
        
        self.selectRequestDone.emit()
    
    def selectCatastoGeometry(self, catastos):
        if len(catastos) == 0:
            return
        
        # get only the first record
        catasto = catastos[0]
        if len(catastos) != 1:
            message = self.tr("Ottenuti %d records. Verrà considerato solo il primo con gid: %d" % (len(catastos), catasto["gid"]))
            self.showMessage(message, QgsMessageLog.INFO)
            
        # now get feature related to the record
        # probabily bettere use Nathan query lib: http://nathanw.net/2013/07/24/the-little-query-engine-for-pyqgis/
        QgsLogger.debug(self.tr("Dump del record catasto %s" % json.dumps(catasto)) )
        
        layer = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_ORIG )
        layer.removeSelection()
        exp = QgsExpression("gid = %d" % catasto["gid"])
        fields = layer.pendingFields()
        exp.prepare(fields)
        features = filter(exp.evaluate, layer.getFeatures())
        layer.setSelectedFeatures( [f.id() for f in features] )
        self.iface.mapCanvas().zoomToSelected(layer)

    def selectSafety(self):
        # get id of the current selected safety
        local_id = None
        if self.currentSafety is not None:
            local_id = self.currentSafety["local_id"]
            
        from DlgSelectSafety import DlgSelectSafety
        dlg = DlgSelectSafety(local_id)
        ret = dlg.exec_()
        # check if result set
        if ret != 0:
            if (dlg.buttonSelected == "Ok"):
                # deselect all safety geometries
                layer = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_ORIG )
                layer.removeSelection()
                
                # get selected request
                self.currentSafety = dlg.currentSafety
                self.updatedCurrentSafety.emit()
                
            elif (dlg.buttonSelected == "Save"): # Means Upload current safety
                if dlg.currentSafety is None:
                    return
                # get selected request
                self.safeties = dlg.records
                self.currentSafety = dlg.currentSafety
                self.updatedCurrentSafety.emit()
                
                # now upload currentSafety if not already uploaded
                if str(self.currentSafety["id"]) == "-1":
                    self.uploadSafeties([self.currentSafety])
                else:
                    message = self.tr("Scheda %s gia' archiviata con il numero: %s" % (self.currentSafety["local_id"], self.currentSafety["number"]))
                    self.showMessage(message, QgsMessageLog.WARNING)
                    QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
    
            elif (dlg.buttonSelected == "SaveAll"): # means upload all safeties
                self.safeties = dlg.records
                
                # add to the list only safety to be uploaded
                safetyToUpload = []
                for safety in self.safeties:
                    if str(safety["id"]) != "-1":
                        continue
                    safetyToUpload.append(safety)
                
                self.uploadSafeties(safetyToUpload)

    def openCurrentSafety(self):
        QgsLogger.debug("openCurrentSafety entered",2 )
        if self.currentSafety == None:
            return
        
        # get teamName
        from ArchiveManager import ArchiveManager # import here to avoid circular import
        if self.teams == None:
            self.teams = ArchiveManager.instance().loadTeams()
        teamName = ""
        for team in self.teams:
            if team["id"] == self.currentSafety["team_id"]:
                teamName = team["name"]
        
        # update safetyForm is opened
        if self.safetyDlg is not None:
            self.updateSafetyForm()
        
        else:
            self.safetyDlg = None
            from DlgSafetyForm import DlgSafetyForm
            self.safetyDlg = DlgSafetyForm( teamName, self.currentSafety, self.iface, self.iface.mainWindow() )
            self.safetyDlg.currentSafetyModifed.connect(self.updateCurrentSafetyFromForm)
            self.safetyDlg.destroyed.connect(self.cleanUpSafetyForm)
            self.safetyDlg.exec_()
            
        QgsLogger.debug("openCurrentSafety exit",2 )

    def cleanUpSafetyForm(self):
        try:
            QgsLogger.debug("cleanUpSafetyForm entered",2 )
            self.safetyDlg = None
            QgsLogger.debug("cleanUpSafetyForm exit",2 )
        except:
            pass

    def updateSafetyForm(self):
        QgsLogger.debug("updateSafetyForm entered",2 )
        # remove dialog is safety == None
        if self.currentSafety == None:
            if self.safetyDlg is not None:
                self.safetyDlg.deleteLater()
            self.safetyDlg = None
            return
        
        if self.safetyDlg is None:
            # open e new one
            self.openCurrentSafety()
        else:
            # could be managed passing safety in the signal managed by the form
            self.safetyDlg.currentSafety = self.currentSafety
            self.safetyDlg.update()
            
        QgsLogger.debug("updateSafetyForm exit",2 )
    
    def updateCurrentSafetyFromForm(self, safetyDict):
        if safetyDict == None:
            return
        self.currentSafety["safety"] = safetyDict["safety"]
        self.updatedCurrentSafety.emit()
    
    def updateArchivedCurrentSafety(self):
        QgsLogger.debug("updateArchivedCurrentSafety entered",2 )
        if self.currentSafety == None:
            return
        
        tempSafety = self.updateArchivedSafety(self.currentSafety)
        if not tempSafety is None:
            self.currentSafety = tempSafety
        
        QgsLogger.debug("updateArchivedCurrentSafety exit",2 )

    def updateArchivedSafety(self, safety):
        QgsLogger.debug("updateArchivedSafety entered",2 )
        if safety == None:
            return safety
        
        QgsLogger.debug(self.tr("Dump di safety %s" % json.dumps( safety )) )
        try:
            from ArchiveManager import ArchiveManager # import here to avoid circular import
            overwrite = True
            ArchiveManager.instance().archiveSafety(safety["request_id"], safety["team_id"], safety, overwrite)
            ArchiveManager.instance().commit()
            # if it's a new record get new id to update currentSafety
            if safety["local_id"] == None:
                lastId = ArchiveManager.instance().getLastRowId()
                if lastId != self.currentSafety["local_id"]:
                    safety["local_id"] = lastId
                    
                    message = self.tr("Inserita nuova scheda con id %s" % safety["local_id"])
                    self.showMessage(message, QgsMessageLog.INFO)
            
        except Exception:
            traceback.print_exc()
            ArchiveManager.instance().close() # to avoid locking
            traceback.print_exc()
            message = self.tr("Fallito l'update della scheda di sopralluogo")
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            safety = None
        finally:
            ArchiveManager.instance().close() # to avoid locking
        
        QgsLogger.debug("updateArchivedSafety exit",2 )
        
        return safety

    def repaintSafetyGeometryLayer(self):
        vl = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_MODIF )
        if vl is not None:
            vl.triggerRepaint()

    def archiveSafety(self):
        QgsLogger.debug("archiveSafety entered",2 )
        if self.currentSafety == None:
            return
        
        QgsLogger.debug(self.tr("Dump di safety %s" % json.dumps( self.currentSafety )) )
        try:
            from ArchiveManager import ArchiveManager # import here to avoid circular import
            ArchiveManager.instance().archiveSafety(self.currentSafety["request_id"], self.currentSafety["team_id"], self.currentSafety)
            ArchiveManager.instance().commit()
            
        except Exception:
            traceback.print_exc()
            ArchiveManager.instance().close() # to avoid locking
            traceback.print_exc()
            message = self.tr("Fallito l'archiviazione della scheda di sopralluogo")
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        finally:
            ArchiveManager.instance().close() # to avoid locking
        
        QgsLogger.debug("archiveSafety exit",2 )

    def initNewCurrentSafety(self):
        QgsLogger.debug("initNewCurrentSafety entered",2 )
        
        request_id = None
        team_id = None
        
        if self.currentRequest is not None:
            request_id = self.currentRequest["id"]
        if self.currentSafety is not None:
            team_id = self.currentSafety["team_id"]
            if self.currentRequest is None:
                request_id = self.currentSafety["request_id"]
        
        from DlgSelectRequestTeamAndNumber import DlgSelectRequestTeamAndNumber
        dlg = DlgSelectRequestTeamAndNumber(request_id, team_id)
        ret = dlg.exec_()
        # check if result set
        if ret == 0:
            return ret
        
        # get selected
        request_number = dlg.selectedRequestNumber
        team_name, team_id = dlg.selectedTeamNameAndId
        safety_number = dlg.selectedSafetyNumber
        
        dlg.hide()
        dlg.deleteLater()

        # get id of the current selected safety
        currentDate = date.today()
        dateIso = currentDate.isoformat()
        dateForForm = currentDate.__format__("%d/%m/%Y")
        
        subSafety = {}
        strNumber = "%s" % adapt(safety_number)
        subSafety["number"] = strNumber
        subSafety["sdate"] = '%s' % dateForForm
        
        # set subsafety data of selected request
        from ArchiveManager import ArchiveManager
        self.requests = ArchiveManager.instance().loadRequests()
        
        for request in self.requests:
            if str(request["id"]) != str(request_number):
                continue
            keys = ["s1prov", "s1com", "s1loc", "s1via", "s1civico", "s1catfoglio", "s1catpart1"]
            for k in keys:
                if request[k] != "":
                    subSafety[k] = '%s' % str(request[k])
            break

        safety = "%s" % json.dumps(subSafety)
        self.currentSafety = {"local_id":None, "id":-1, "created":dateIso, "request_id":request_number, "safety":safety, "team_id":team_id, "number":safety_number, "date":dateIso, "gid_catasto":"", "the_geom":None}
        
        self.updatedCurrentSafety.emit() # thi will save new safety on db and update gui
        self.initNewCurrentSafetyDone.emit()
        QgsLogger.debug("initNewCurrentSafety exit",2 )
    
    def deleteCurrentSafety(self):
        QgsLogger.debug("deleteCurrentSafety entered",2 )
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setText(self.tr("Sicuro di cancellare la scheda %s ?" % self.currentSafety["number"]))
        msgBox.setInformativeText(self.tr("L'operazione cancellera' definitivamente la scheda dal database"))
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        msgBox.setButtonText(QMessageBox.Yes, self.tr("Si"))
        msgBox.setButtonText(QMessageBox.Cancel, self.tr("No"))
        ret = msgBox.exec_()
        if ret == QMessageBox.Cancel:
            return
    
        QgsLogger.debug(self.tr("Cancella safety %s" % json.dumps( self.currentSafety )) )
        try:
            from ArchiveManager import ArchiveManager # import here to avoid circular import
            ArchiveManager.instance().deleteSafety(self.currentSafety["local_id"])
            ArchiveManager.instance().commit()
            ArchiveManager.instance().deleteAttachmentsBySasfety(self.currentSafety["local_id"])
            ArchiveManager.instance().commit()
            
            # reset current safety
            self.currentSafety = None
            self.updatedCurrentSafety.emit()
            
        except Exception:
            traceback.print_exc()
            ArchiveManager.instance().close() # to avoid locking
            traceback.print_exc()
            message = self.tr("Fallita la cancellazione della scheda %s" % self.currentSafety["number"])
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        finally:
            ArchiveManager.instance().close() # to avoid locking

        QgsLogger.debug("deleteCurrentSafety exit",2 )

    def manageGuiStatus(self):
        if self.currentSafety == None:
            self.btnDeleteCurrentSafety.setEnabled(False)
            self.btnModifyCurrentSafety.setEnabled(False)
            self.btnManageAttachments.setEnabled(False)
            self.btnSelectSafety.setText("Seleziona Scheda [%s]" % "--")
        else:
            self.btnDeleteCurrentSafety.setEnabled(True)
            self.btnModifyCurrentSafety.setEnabled(True)
            self.btnManageAttachments.setEnabled(True)
            self.btnSelectSafety.setText("Seleziona Scheda [%s]" % self.currentSafety["local_id"])
        
        if self.currentRequest == None:
            self.btnSelectRequest.setText("Seleziona Sopralluogo [%s]" % "--")
        else:
            self.btnSelectRequest.setText("Seleziona Sopralluogo [%s]" % self.currentRequest["id"])
        
    @classmethod
    def checkActionScale(cls, actionName, maxScale):
        if int(cls.instance().canvas.scale()) > maxScale:
            QMessageBox.warning( cls.instance(), "Azione non permessa", u"L'azione \"%s\" è ammessa solo dalla scala 1:%d" % (actionName, maxScale) )
            return False
        return True

    def linkSafetyGeometry(self, point=None, button=None):
        if self.currentSafety == None:
            self.btnLinkSafetyGeometry.setChecked(False)
            return
        
        action = self.btnLinkSafetyGeometry.toolTip()
        if not self.checkActionScale( action, self.SCALE_IDENTIFY ) or point == None:
            return self.nuovaPointEmitter.startCapture()

        if button != Qt.LeftButton:
            self.btnLinkSafetyGeometry.setChecked(False)
            return

        layerOrig = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_ORIG )
        if layerOrig == None:
            self.btnLinkSafetyGeometry.setChecked(False)
            return

        feat = self.nuovaPointEmitter.findAtPoint(layerOrig, point)
        if feat != None:
            from ArchiveManager import ArchiveManager

            # already get => unselect if
            gidIndex = feat.fieldNameIndex("gid")
            gid = feat.attributes()[gidIndex]
            layerOrig.deselect(gid)
            
            #if not self.checkActionSpatialFromFeature( action, feat, True ):
            #    return self.nuovaPointEmitter.startCapture()

            # controlla se tale geometria ha qualche scheda associata
            features = ArchiveManager.instance().loadSafetiesByCatasto(gid)
            if len(features) == 1:
                feature = features[0]
                # related safety is not the current safety... ask if you want to create another
                # safety on the same polygon
                if feature["local_id"] != self.currentSafety["local_id"]:
                    msgBox = QMessageBox()
                    msgBox.setIcon(QMessageBox.Warning)
                    msgBox.setText("RT Geosisma")
                    msgBox.setInformativeText(self.tr("E' già presente la scheda %d su questa particella. Vuoi continuare?" % feature["number"]))
                    msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
                    msgBox.setButtonText(QMessageBox.Yes, self.tr("Si"))
                    msgBox.setButtonText(QMessageBox.Cancel, self.tr("No: seleziono un'altra particella"))
                    ret = msgBox.exec_()
                    if ret == QMessageBox.Cancel:
                        # continue on another geometry
                        return self.nuovaPointEmitter.startCapture()
                
            if len(features) > 1:
                # NO, c'è già una scheda associata
                QMessageBox.critical( self, "RT Geosisma", self.tr("Anomalia! Esistono più schede associate al poligono! Seleziona un'altro poligono") )
                return self.nuovaPointEmitter.startCapture()

            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            # OK, non esiste alcuna scheda associata a tale geometria
            # associa il poligono alla safety
            crs = layerOrig.dataProvider().crs()
            
            self.updateCurrentSafetyWithCatasto(crs, feat, point)
            
            self.canvas.refresh()
            QApplication.restoreOverrideCursor()
            self.btnLinkSafetyGeometry.setChecked(False)
            
        else:
            self.nuovaPointEmitter.startCapture()
    
    def updateCurrentSafetyWithCatasto(self, geoDbCrs, feature, point):
        '''
        Method update CurrentSafety with element related to current original feature (from catasto)
        @param crs: QgsCoordinateReferenceSystem of the feature geometry
        @param feature: QgsFeature of the original catasto layer
        @signal currentSafetyModified
        '''
        if self.currentSafety == None:
            return
        
        fieldNames = [field.name() for field in feature.fields()]
        featureDic = dict(zip(fieldNames, feature.attributes()))
        
        tempSafety = self.currentSafety
        
        # check if there is already a geometry in the current safety
        # => ask if you want to add a new particella or reset if it 
        # refer to the same geometry
        if (tempSafety["the_geom"] == None) or (tempSafety["the_geom"] == ""):
            pass
        else:
            # check if safety geometry is referred to the same feature
            gidToFind = "_%s_" % featureDic["gid"]
            index = tempSafety["gid_catasto"].find(gidToFind)
            if index < 0:
                # it's a new particella
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Warning)
                msgBox.setText("RT Geosisma")
                msgBox.setInformativeText(self.tr("La scheda ha gia' una particella associata\nCosa vuoi fare?"))
                msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel | QMessageBox.Open)
                msgBox.setButtonText(QMessageBox.Yes, self.tr("Sostituire"))
                msgBox.setButtonText(QMessageBox.Cancel, self.tr("Nulla"))
                msgBox.setButtonText(QMessageBox.Open, self.tr("Unire"))
                ret = msgBox.exec_()
                # if ignore do nothing
                if ret == QMessageBox.Cancel:
                    return
                # if unify then do nothing... the feature will be added to the current values of geom
                elif ret == QMessageBox.Open:
                    pass
                # if substitute then reset current safety geometry and pass... next steps will add selected geometry
                elif ret == QMessageBox.Yes:
                    tempSafety["gid_catasto"] = ""
                    tempSafety["the_geom"] = None
            else:
                # it's a particella already in linked partielle => probabily need 
                # to overwrite safety geometry modification
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Warning)
                msgBox.setText("RT Geosisma")
                msgBox.setInformativeText(self.tr("Vuoi resettare la geometria della scheda: %s ?" % tempSafety["number"]))
                msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
                msgBox.setButtonText(QMessageBox.Yes, self.tr("Si"))
                msgBox.setButtonText(QMessageBox.Cancel, self.tr("No: seleziono un'altra particella"))
                ret = msgBox.exec_()
                if ret == QMessageBox.Cancel:
                    # continue on another geometry
                    return self.nuovaPointEmitter.startCapture()
                tempSafety["gid_catasto"] = ""
                tempSafety["the_geom"] = None

        # convert point come from default SRID to GEODB srid to allow geos search in that db
        # point is a pick from the current canvas that is in self.DEFAULT_SRID
        # but geo db is in another srid
        pointGeom = QgsGeometry.fromPoint(point)
        defaultCrs = QgsCoordinateReferenceSystem(self.DEFAULT_SRID)  # WGS 84 / UTM zone 33N
        xform = QgsCoordinateTransform(defaultCrs, geoDbCrs)
        if pointGeom.transform(xform):
            QMessageBox.critical( self, "RT Geosisma", self.tr("Errore nella conversione della punto al CRS delle particelle") )
            return
        point = pointGeom.asPoint()
        if point[0] == 0 and point[1] == 0:
            QMessageBox.critical( self, "RT Geosisma", self.tr("Errore delal geometria in QgsPoint") )
            return

        # get location data from DB to fill safety
        from GeoArchiveManager import GeoArchiveManager
        safetyLocationDataDict = GeoArchiveManager.instance().locationDataByBelfiore( featureDic["belfiore"] )[0]
        
        # update safety json with catasto data (foglio and particella)
        subSafetyDict = ast.literal_eval( tempSafety["safety"] )
        
        subSafetyDict["s1prov"] = safetyLocationDataDict["sigla"]
        subSafetyDict["s1com"] = safetyLocationDataDict["toponimo"]
        subSafetyDict["s1istatreg"] = safetyLocationDataDict["id_regione"]
        subSafetyDict["s1istatprov"] = safetyLocationDataDict["id_provincia"]
        subSafetyDict["s1istatcom"] = safetyLocationDataDict["id_comune"]
        subSafetyDict["s1catfoglio"] = featureDic["foglio"]
        subSafetyDict["s1catalle"] = featureDic["allegato"]
        subSafetyDict["s1catpart1"] = featureDic["codbo"]
        
        # get localita'
        localitaDict = GeoArchiveManager.instance().localitaByPoint( point )
        if len(localitaDict) > 0:
            localitaDict = localitaDict[0]
            subSafetyDict["s1loc"] = localitaDict["denom_loc"]
            subSafetyDict["s1istatloc"] = localitaDict["cod_loc"]
        
        # get aggregato
        fab_10kDict = GeoArchiveManager.instance().fab_10kByPoint( point )
        if len(fab_10kDict) > 0:
            fab_10kDict = fab_10kDict[0]
            subSafetyDict["s1aggn"] = fab_10kDict["identif"]
        
        # update temp safety with subSafety
        tempSafety["safety"] = json.dumps(subSafetyDict)

        # convert feature geometry to default SRID
        #defaultCrs = QgsCoordinateReferenceSystem(self.DEFAULT_SRID)  # WGS 84 / UTM zone 33N
        xform = QgsCoordinateTransform(geoDbCrs, defaultCrs)
        
        featureGeometry = feature.geometry()
        if featureGeometry.transform(xform):
            QMessageBox.critical( self, "RT Geosisma", self.tr("Errore nella conversione della particella al CRS corrente") )
            return
        
        # fuse current safety polygon with the new feature's one
        if (tempSafety["the_geom"] == None) or (tempSafety["the_geom"] == ""):
            tempSafety["the_geom"] = featureGeometry.exportToWkt()
        else:
            # create geometry from current safety geometry
            featureMultiPolygon = featureGeometry.asMultiPolygon()
            if len(featureMultiPolygon) == 0:
                QMessageBox.critical( self, "RT Geosisma", self.tr("La geometria della sceda corrente non e' Multipolygon") )
                return
            
            # get safety geometry converting to MultyPolygon (that is a DB contraint)
            # thi sis necessary because  QgsGeometry.fromWkt tries to converto to simple POLYGON if
            # actuals safety geometry has only a polygon.
            safetyGeometry = QgsGeometry.fromWkt( tempSafety["the_geom"] )
            if not safetyGeometry.isMultipart():
                if not safetyGeometry.convertToMultiType(): 
                    QMessageBox.critical( self, "RT Geosisma", self.tr("Non posso convertire la geometria della scheda in Multipolygon") )
                    return

            # add polygon of the feature multipolygon in the safety multypolygon
            safetyGeometry = safetyGeometry.combine(featureGeometry)
            
            # again convert to Multypolygon beacuse QgsGeometry.combine create one Polygon if
            # the two geometry are adiacent and the result is a unique Polygon
            if not safetyGeometry.isMultipart():
                if not safetyGeometry.convertToMultiType(): 
                    QMessageBox.critical( self, "RT Geosisma", self.tr("Non posso convertire la geometria della scheda in Multipolygon") )
                    return

            # update geometry in the safety
            tempSafety["the_geom"] = safetyGeometry.exportToWkt()
        
        # record reference to the related cataasto polygons
        if (tempSafety["gid_catasto"] == None) or (tempSafety["gid_catasto"] == ""):
            tempSafety["gid_catasto"] = "_%d_" % featureDic["gid"]
        else:
            tempSafety["gid_catasto"] = "%s_%d_" % (tempSafety["gid_catasto"], featureDic["gid"])

        # update safety
        self.currentSafety = tempSafety
        self.updatedCurrentSafety.emit()
    
    def uploadSafeties(self, safeties):
        if safeties is None or len(safeties) == 0:
            return
        from UploadManager import UploadManager
        self.uploadSafetyDlg = UploadManager()
        self.uploadSafetyDlg.initSafeties(safeties)
        self.uploadSafetyDlg.done.connect( self.manageEndUploadSafetiesDlg )
        self.uploadSafetyDlg.message.connect(self.showMessage)
        self.uploadSafetyDlg.exec_()

    def manageEndUploadSafetiesDlg(self, success):
        if self.uploadSafetyDlg is None:
            return
        self.uploadSafetyDlg.hide()

        QApplication.restoreOverrideCursor()
        if not success:
            message = self.tr("Fallito l'Upload delle schede. Controlla il Log")
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        else:
            message = self.tr("Upload avvenuto con successo")
            self.showMessage(message, QgsMessageLog.INFO)
            QMessageBox.information(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        
        # get updated safeties
        updatedSafeties = self.uploadSafetyDlg.updatedSafeties

        currentModified = False
        for modSafety in updatedSafeties:
            self.updateArchivedSafety(modSafety)
            
            # check if currentSafety has been modified
            if self.currentSafety != None:
                if self.currentSafety["id"] == modSafety["id"]:
                    self.currentSafety = modSafety
                    currentModified = True
        
        if currentModified:
            self.updatedCurrentSafety.emit()
        
        # notify end of download
        self.uploadSafetiesDone.emit(success)
        
        if self.uploadSafetyDlg:
            self.uploadSafetyDlg.deleteLater()
        self.uploadSafetyDlg = None

    def manageAttachments(self):
        if self.currentSafety is None:
            return
        from DlgManageAttachments import DlgManageAttachments
        self.manageAttachmentsDlg = DlgManageAttachments(self.currentSafety["local_id"], self.currentSafety["team_id"])
        self.manageAttachmentsDlg.exec_()

    ###############################################################
    ###### static methods
    ###############################################################
    @classmethod
    def _getLayerId(self, layer):
        if hasattr(layer, 'id'):
            return layer.id()
        return layer.getLayerID() 

    @classmethod
    def _getRendererCrs(self, renderer):
        if hasattr(renderer, 'destinationCrs'):
            return renderer.destinationCrs()
        return renderer.destinationSrs()

    @classmethod
    def _setRendererCrs(self, renderer, crs):
        if hasattr(renderer, 'setDestinationCrs'):
            return renderer.setDestinationCrs( crs )
        return renderer.setDestinationSrs( crs )

    @classmethod
    def _addMapLayer(self, layer):
        if hasattr(QgsMapLayerRegistry.instance(), 'addMapLayers'):
            return QgsMapLayerRegistry.instance().addMapLayers( [layer] )
        return QgsMapLayerRegistry.instance().addMapLayer(layer)

    @classmethod
    def _removeMapLayer(self, layer):
        if hasattr(QgsMapLayerRegistry.instance(), 'removeMapLayers'):
            return QgsMapLayerRegistry.instance().removeMapLayers( [layer] )
        return QgsMapLayerRegistry.instance().removeMapLayer(layer)

    @classmethod
    def _logMessage(self, group, msg):
        try:
            QgsMessageLog.logMessage( msg, group )
        except:
            pass

