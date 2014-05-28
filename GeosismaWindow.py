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
import copy
from datetime import date, datetime
from psycopg2.extensions import adapt

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *

from qgis.core import *
from qgis.gui import * 

from Utils import *
# import cache manager
from DlgWmsLayersManager import DlgWmsLayersManager, WmsLayersBridge

currentPath = os.path.dirname(__file__)

class GeosismaWindow(QDockWidget):

    # signals
    downloadTeamsDone = pyqtSignal(bool)
    archiveTeamsDone = pyqtSignal(bool)
    downloadRequestsDone = pyqtSignal(bool)
    archiveRequestsDone = pyqtSignal(bool)
    downloadSopralluoghiDone = pyqtSignal(bool)
    archiveSopralluoghiDone = pyqtSignal(bool)
    downloadFab10kModificationsDone = pyqtSignal(bool)
    archiveFab10kModificationsDone = pyqtSignal(bool)
    uploadSafetiesDone = pyqtSignal(bool)
    selectRequestDone = pyqtSignal()
    updatedCurrentSafety = pyqtSignal()
    initNewCurrentSafetyDone = pyqtSignal()
    uploadFab10kmodDone = pyqtSignal(bool)
    
    # static global vars
    MESSAGELOG_CLASS = "rt_geosisma_offline"
    GEOSISMA_DBNAME = "geosismadb.sqlite"
    GEOSISMA_GEODBNAME = "geosisma_geo.sqlite"
    DEFAULT_SRID = 3003
    GEODBDEFAULT_SRID = 32632

    # nomi dei layer in TOC
    LAYER_GEOM_ORIG = "Catasto"
    LAYER_GEOM_MODIF = "Schede sopralluoghi"
    LAYER_GEOM_SOPRALLUOGHI = "Sopralluoghi effettuati"
    LAYER_GEOM_FAB10K = "Fabbricati 10k"
    LAYER_GEOM_FAB10K_MODIF = "Fabbricati 10k modificati"
    LAYER_FOTO = "Foto Edifici"

    # stile per i layer delle geometrie
    STYLE_FOLDER = "styles"
    STYLE_GEOM_ORIG = "stile_geometrie_originali.qml"
    STYLE_GEOM_SOPRALLUOGHI = "stile_sopralluoghi_effettuati.qml"
    STYLE_GEOM_MODIF = "stile_geometrie_modificate.qml"
    STYLE_GEOM_FAB10K = "stile_geometrie_aggregati.qml"
    STYLE_GEOM_FAB10K_MODIF = "stile_geometrie_aggregati_modificati.qml"
    STYLE_FOTO = "stile_fotografie.qml"

    SCALE_IDENTIFY = 5000
    SCALE_MODIFY = 2000

    # nomi tabelle contenenti le geometrie
    TABLE_GEOM_ORIG = "fab_catasto".lower()
    TABLE_GEOM_SOPRALLUOGHI = "sopralluoghi".lower()
    TABLE_GEOM_MODIF = "missions_safety".lower()
    TABLE_GEOM_FAB10K = "fab_10k".lower()
    TABLE_GEOM_FAB10K_MODIF = "fab_10k_mod".lower()

    # ID dei layer contenenti geometrie e wms
    VLID_GEOM_ORIG = ''
    VLID_GEOM_MODIF = ''
    VLID_GEOM_SOPRALLUOGHI = ''
    VLID_GEOM_FAB10K = ''
    VLID_GEOM_FAB10K_MODIF = ''
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
    
    def closeEvent(self, event):
        self.cleanUp()
        return QDockWidget.closeEvent(self, event)
    
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
        
        # clean registered event handler
        if self.iface.actionToggleEditing():
            try:
                self.iface.actionToggleEditing().changed.disconnect(self.actionToggleEditingChanged)
            except:
                pass
            try:
                self.iface.actionToggleEditing().triggered.disconnect(self.actionToggleEditingTriggered)
            except:
                pass
            
        try:
            self.linkSafetyGeometryEmitter.deleteLater()
            self.lookForSafetiesEmitter.deleteLater()
            self.newSafetyGeometryDrawer.deleteLater()
            self.newAggregatiDrawer.deleteLater()
            self.modifyAggregatiEmitter.deleteLater()
        except:
            pass

        # reset singleton
        try:
            GeosismaWindow._instance = None
        except:
            pass
    
    def init(self, parent=None, iface=None):
        QDockWidget.__init__(self, parent)
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
        self.fab10kModifications = []
        self.currentSafety = None
        self.safeties = []
        self.teams = None
        
        MapTool.canvas = self.canvas

        self.linkSafetyGeometryEmitter = FeatureFinder()
        self.linkSafetyGeometryEmitter.registerStatusMsg( u"Click per identificare la geometria da associare alla nuova scheda" )
        QObject.connect(self.linkSafetyGeometryEmitter, SIGNAL("pointEmitted"), self.linkSafetyGeometry)

        self.lookForSafetiesEmitter = FeatureFinder()
        self.lookForSafetiesEmitter.registerStatusMsg( u"Click per identificare la geometria di cui cercare le schede" )
        QObject.connect(self.lookForSafetiesEmitter, SIGNAL("pointEmitted"), self.listLinkedSafeties)

        self.newSafetyGeometryDrawer = PolygonDrawer()
        self.newSafetyGeometryDrawer.registerStatusMsg( u"Click sx per disegnare la nuova gemetria, click dx per chiuderla" )
        QObject.connect(self.newSafetyGeometryDrawer, SIGNAL("geometryEmitted"), self.createNewSafetyGeometry)

        self.connect(self.btnNewSafety, SIGNAL("clicked()"), self.initNewCurrentSafety)
        self.connect(self.btnSelectSafety, SIGNAL("clicked()"), self.selectSafety)
        self.connect(self.btnDeleteCurrentSafety, SIGNAL("clicked()"), self.deleteCurrentSafety)
        self.connect(self.btnUploadSafeties, SIGNAL("clicked()"), self.selectSafetiesToUpload)
        self.connect(self.btnSelectRequest, SIGNAL("clicked()"), self.selectRequest)
        self.connect(self.btnDownload, SIGNAL("clicked()"), self.downloadTeams) # ends emitting downloadTeamsDone
        #self.connect(self.btnReset, SIGNAL("clicked()"), self.reset)
        
        self.connect(self.btnLinkSafetyGeometry, SIGNAL("clicked()"), self.linkSafetyGeometry)
        self.connect(self.btnListLinkedSafeties, SIGNAL("clicked()"), self.listLinkedSafeties)
        self.connect(self.btnNewSafetyGeometry, SIGNAL("clicked()"), self.createNewSafetyGeometry)
        self.connect(self.btnZoomToSafety, SIGNAL("clicked()"), self.zoomToSafety)
        self.connect(self.btnCleanUnlinkedSafeties, SIGNAL("clicked()"), self.cleanUnlinkedSafeties)
        self.connect(self.btnManageAttachments, SIGNAL("clicked()"), self.manageAttachments)
        
        # managing of fab_10k_mod (Fabbricati 10k modificati)
        self.newAggregatiDrawer = PolygonDrawer()
        self.newAggregatiDrawer.registerStatusMsg( u"Click sx per disegnare la nuova gemetria, click dx per chiuderla" )
        QObject.connect(self.newAggregatiDrawer, SIGNAL("geometryEmitted"), self.createNewAggregatiGeometry)
        self.connect(self.btnNewAggregatiGeometry, SIGNAL("clicked()"), self.createNewAggregatiGeometry)
        
        self.modifyAggregatiEmitter = FeatureFinder()
        self.modifyAggregatiEmitter.registerStatusMsg( u"Click per identificare la geometria di cui cercare le schede" )
        self.connect(self.btnModifyAggregatiGeometry, SIGNAL("clicked()"), self.modifyAggregatiGeometry)
        
        self.connect(self.btnUploadModifiedAggregati, SIGNAL("clicked()"), self.selectFab10kmodToUpload)
        
        # custom signals
        self.downloadTeamsDone.connect(self.archiveTeams) # ends emitting archiveTeamsDone
        self.archiveTeamsDone.connect(self.downloadRequests) # ends emitting downloadRequestsDone
        self.archiveTeamsDone.connect(self.resetTeamComboBox)
        self.downloadRequestsDone.connect( self.archiveRequests ) # ends emitting archiveRequestsDone
        self.archiveRequestsDone.connect( self.downloadSopralluoghi ) # ends emitting downloadSopralluoghiDone
        self.downloadSopralluoghiDone.connect( self.archiveSopralluoghi ) # ends emitting downloadFab10kModificationsDone
        self.archiveSopralluoghiDone.connect( self.downloadFab10kModifications ) # ends emitting downloadFab10kModificationsDone
        self.downloadFab10kModificationsDone.connect( self.archiveFab10kModifications ) # end emitting archiveFab10kModificationsDone
        # at the end onf download refresh canvas
        self.archiveFab10kModificationsDone.connect(self.refreshCanvas)
        
        self.updatedCurrentSafety.connect(self.updateSafetyForm)
        self.updatedCurrentSafety.connect(self.updateArchivedCurrentSafety)
        self.updatedCurrentSafety.connect(self.repaintSafetyGeometryLayer)
        self.updatedCurrentSafety.connect(self.zoomToSafety)
        self.updatedCurrentSafety.connect(self.selectCurrentSafetyFeature)
        
        # GUI state based on signals
        self.selectRequestDone.connect(self.manageGuiStatus)
        self.updatedCurrentSafety.connect(self.manageGuiStatus)
        
        self.manageGuiStatus()

#         self.connect(self.iface, SIGNAL("newProjectCreated()"), self.close)

    def setupUi(self):
        self.setObjectName( "rt_geosisma_dockwidget" )
        self.setWindowTitle( self.tr("Geosisma Offline RT") )

        child = QWidget()
        vLayout = QVBoxLayout( child )


        group = QGroupBox( self.tr("Schede Sopralluoghi"), child )
        vLayout.addWidget( group )
        gridLayout = QGridLayout( group )

        text = self.tr(u"Nuova")
        self.btnNewSafety = QPushButton( QIcon(":/icons/nuova_scheda.png"), text, group )
        #text = u"Identifica la geometria per la creazione di una nuova scheda edificio"
        text = self.tr(u"Crea una nuova scheda sopralluogo")
        self.btnNewSafety.setToolTip( text )
        #self.btnNewSafety.setCheckable(True)
        gridLayout.addWidget(self.btnNewSafety, 0, 0, 1, 1)

        text = self.tr(u"Apri")
        self.btnSelectSafety = QPushButton( QIcon(":/icons/modifica_scheda.png"), text, group )
        text = self.tr(u"Seleziona e modifica una scheda sopralluogo")
        self.btnSelectSafety.setToolTip( text )
        gridLayout.addWidget(self.btnSelectSafety, 0, 1, 1, 1)

        text = self.tr(u"Elimina")
        self.btnDeleteCurrentSafety = QPushButton( QIcon(":/icons/cancella_scheda.png"), text, group )
        text = self.tr(u"Elimina scheda sopralluogo")
        self.btnDeleteCurrentSafety.setToolTip( text )
        #self.btnDeleteCurrentSafety.setCheckable(True)
        gridLayout.addWidget(self.btnDeleteCurrentSafety, 0, 2, 1, 1)

        text = self.tr(u"Seleziona Richiesta")
        self.btnSelectRequest = QPushButton( QIcon(":/icons/riepilogo_schede.png"), text, group )
        self.btnSelectRequest.setToolTip( text )
        gridLayout.addWidget(self.btnSelectRequest, 2, 0, 1, 3)

        #text = self.tr(u"Reset")
        #self.btnReset = QPushButton( QIcon(":/icons/riepilogo_schede.png"), text, group )
        #self.btnReset.setToolTip( text )
        #gridLayout.addWidget(self.btnReset, 3, 2, 1, 1)


        group = QGroupBox( self.tr(u"Geometrie Sopralluoghi e allegati"), child )
        vLayout.addWidget( group )
        gridLayout = QGridLayout( group )

        text = self.tr(u"Nuova")
        self.btnNewSafetyGeometry = QPushButton( QIcon(":/icons/crea_geometria.png"), text, group )
        text = self.tr(u"Disegna un poligono da associare alla scheda")
        self.btnNewSafetyGeometry.setToolTip( text )
        self.btnNewSafetyGeometry.setCheckable(True)
        gridLayout.addWidget(self.btnNewSafetyGeometry, 0, 0, 1, 2)

        text = self.tr(u"Zoom")
        self.btnZoomToSafety = QPushButton( QIcon(":/icons/crea_geometria.png"), text, group )
        text = self.tr(u"Zoom al poligono della scheda")
        self.btnZoomToSafety.setToolTip( text )
        gridLayout.addWidget(self.btnZoomToSafety, 0, 2, 1, 1)

        text = self.tr(u"Associa")
        self.btnLinkSafetyGeometry = QPushButton( QIcon(":/icons/crea_geometria.png"), text, group )
        text = self.tr(u"Seleziona una particella da associare alla scheda")
        self.btnLinkSafetyGeometry.setToolTip( text )
        self.btnLinkSafetyGeometry.setCheckable(True)
        gridLayout.addWidget(self.btnLinkSafetyGeometry, 1, 0, 1, 1)

        text = self.tr(u"Elenco")
        self.btnListLinkedSafeties = QPushButton( QIcon(":/icons/crea_geometria.png"), text, group )
        text = self.tr(u"Elencare le scehde associate a una particella")
        self.btnListLinkedSafeties.setToolTip( text )
        self.btnListLinkedSafeties.setCheckable(True)
        gridLayout.addWidget(self.btnListLinkedSafeties, 1, 1, 1, 1)

        text = self.tr(u"Ripulisci")
        self.btnCleanUnlinkedSafeties = QPushButton( QIcon(":/icons/crea_geometria.png"), text, group )
        text = self.tr(u"Elimina schede non associate a nessuna particella")
        self.btnCleanUnlinkedSafeties.setToolTip( text )
        gridLayout.addWidget(self.btnCleanUnlinkedSafeties, 1, 2, 1, 1)

        text = self.tr(u"Gestisci allegati")
        self.btnManageAttachments = QPushButton( QIcon(":/icons/crea_geometria.png"), text, group )
        text = self.tr(u"Aggiuinta e rimozione degli allegati alla scheda corrente")
        self.btnManageAttachments.setToolTip( text )
        gridLayout.addWidget(self.btnManageAttachments, 3, 0, 1, 3)

        group = QGroupBox( self.tr("Geometrie %s" % self.LAYER_GEOM_FAB10K_MODIF), child )
        vLayout.addWidget( group )
        gridLayout = QGridLayout( group )

        label = QLabel( self.tr("Team"), group )
        gridLayout.addWidget(label, 0, 0, 1, 1)
        self.teamComboBox = QComboBox( group )
        gridLayout.addWidget(self.teamComboBox, 0, 1, 1, 1)

        text = self.tr(u"Nuova")
        self.btnNewAggregatiGeometry = QPushButton( QIcon(":/icons/crea_geometria.png"), text, group )
        self.btnNewAggregatiGeometry.setToolTip( self.tr(u"Disegna un nuovo record %s" % self.LAYER_GEOM_FAB10K) )
        self.btnNewAggregatiGeometry.setCheckable(True)
        gridLayout.addWidget(self.btnNewAggregatiGeometry, 0, 2, 1, 1)

        text = self.tr(u"Modifica")
        self.btnModifyAggregatiGeometry = QPushButton( QIcon(":/icons/modifica_scheda.png"), text, group )
        self.btnModifyAggregatiGeometry.setToolTip( self.tr(u"Copia e modifica un Aggregato esistente") )
        self.btnModifyAggregatiGeometry.setCheckable(True)
        gridLayout.addWidget(self.btnModifyAggregatiGeometry, 0, 3, 1, 1)

        group = QGroupBox( self.tr("Sincronizzazione"), child )
        vLayout.addWidget( group )
        gridLayout = QGridLayout( group )

        text = self.tr(u"Dowload")
        self.btnDownload = QPushButton( QIcon(":/icons/riepilogo_schede.png"), text, group )
        self.btnDownload.setToolTip( "Download Richieste di sopralluogo e %s" % self.LAYER_GEOM_FAB10K_MODIF )
        gridLayout.addWidget(self.btnDownload, 0, 0, 1, 2)

        text = self.tr(u"Upload Schede")
        self.btnUploadSafeties = QPushButton( QIcon(":/icons/riepilogo_schede.png"), text, group )
        text = self.tr(u"Upload delle schede sopralluogo")
        self.btnUploadSafeties.setToolTip( text )
        gridLayout.addWidget(self.btnUploadSafeties, 1, 0, 1, 1)

        text = self.tr(u"Upload Aggregati", )
        self.btnUploadModifiedAggregati = QPushButton( QIcon(":/icons/riepilogo_schede.png"), text, group )
        self.btnUploadModifiedAggregati.setToolTip( self.tr(u"Upload di %s" % self.LAYER_GEOM_FAB10K_MODIF ) )
        gridLayout.addWidget(self.btnUploadModifiedAggregati, 1, 1, 1, 1)

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
        
        # load all layers from db
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
        self.loadFab10kModifiedGeometries()
        self.loadSopralluoghiGeometries()
        self.loadSafetyGeometries()
        self.setProjectDefaultSetting()
        self.manageSafetyEditingSignals()
        self.resetTeamComboBox()
        self.registerAggregatiEditingSignals()
        #self.registerAggregatiEditingSignals___APPPP()
        
        return True

    def refreshCanvas(self):
        # seems it doesn't work :(
        self.iface.mapCanvas().refresh()
        self.canvas.refresh()

    def resetTeamComboBox(self):
        from ArchiveManager import ArchiveManager
        self.teams = ArchiveManager.instance().loadTeams()
        self.teamComboBox.clear()
        self.teamComboBox.addItems([str(v["name"]) for v in self.teams])

    def reloadCrs(self):
        #self.srid = self.getSridFromDb()
        self.srid = self.DEFAULT_SRID
        crs = QgsCoordinateReferenceSystem( self.srid, QgsCoordinateReferenceSystem.EpsgCrsId )
        # manage deprecated api using newest. If it's not available then use deprecated one
        try:
            mapSettings = self.canvas.mapSettings()
            mapSettings.setDestinationCrs(crs)
            mapSettings.setMapUnits( crs.mapUnits() if crs.mapUnits() != QGis.UnknownUnit else QGis.Meters )
            self.iface.mapCanvas().setCrsTransformEnabled(True)
        except:
            renderer = self.canvas.mapRenderer()
            self._setRendererCrs(renderer, crs)
            renderer.setMapUnits( crs.mapUnits() if crs.mapUnits() != QGis.UnknownUnit else QGis.Meters )
            renderer.setProjectionsEnabled(True)

    def setProjectDefaultSetting(self):
        project = QgsProject.instance()
        layerSnappingList = [GeosismaWindow.VLID_GEOM_ORIG, GeosismaWindow.VLID_GEOM_FAB10K]
        layerSnappingEnabledList = ["enabled", "enabled"]
        layerSnappingToleranceUnitList = ["0", "0"]
        layerSnapToList = ["to_vertex", "to_vertex"]
        layerSnappingToleranceList = ["0.300000", "0.300000"]
        project.writeEntry("Digitizing", "/IntersectionSnapping", Qt.Checked)
        project.writeEntry("Digitizing", "/LayerSnappingList", layerSnappingList)
        project.writeEntry("Digitizing", "/LayerSnappingEnabledList", layerSnappingEnabledList)
        project.writeEntry("Digitizing", "/LayerSnappingToleranceUnitList", layerSnappingToleranceUnitList)
        project.writeEntry("Digitizing", "/LayerSnapToList", layerSnapToList)
        project.writeEntry("Digitizing", "/LayerSnappingToleranceList", layerSnappingToleranceList)

    def emitSafetyGeometryUpdate(self):
        QgsLogger.debug("emitSafetyGeometryUpdate entered",2 )
        layers = QgsMapLayerRegistry.instance().mapLayersByName(self.LAYER_GEOM_MODIF)
        if len(layers) > 0:
            layer = layers[0]
            features = layer.selectedFeatures()
            if len(features) == 0 or len(features) > 1:
                message = self.tr(u"Nessuno o troppi [%d] record selezionati su %s" % (len(features), self.LAYER_GEOM_ORIG) )
                self.showMessage(message, QgsMessageLog.CRITICAL)
                QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
                return
            # get updated geometry and update currentSafety
            self.currentSafety["the_geom"] = features[0].geometry().exportToWkt()
            
        self.updateArchivedCurrentSafety()

    def manageSafetyEditingSignals(self):
        QgsLogger.debug("manageSafetyEditingSignals entered",2 )
        layers = QgsMapLayerRegistry.instance().mapLayersByName(self.LAYER_GEOM_MODIF)
        if len(layers) > 0:
            try:
                layers[0].editingStopped.disconnect(self.emitSafetyGeometryUpdate)
            except:
                pass
            layers[0].editingStopped.connect(self.emitSafetyGeometryUpdate)
           

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
    
    def loadSopralluoghiGeometries(self):
        # skip if already present
        layers = QgsMapLayerRegistry.instance().mapLayersByName(self.LAYER_GEOM_SOPRALLUOGHI)
        if len(layers) > 0:
            # get id of the Geosisma layer
            valid = False
            for layer in layers:
                prop = layer.customProperty( "loadedByGeosismaRTPlugin" )
                if prop == "VLID_GEOM_SOPRALLUOGHI":
                    valid = True
                    GeosismaWindow.VLID_GEOM_SOPRALLUOGHI = self._getLayerId( layer )
            if not valid:
                message = self.tr("Manca il layer %s, ricaricando il plugin verrà caricato automaticamente" % self.LAYER_GEOM_SOPRALLUOGHI)
                self.showMessage(message, QgsMessageLog.CRITICAL)
                QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            return
        # carica il layer con le geometrie delle safety
        if QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_SOPRALLUOGHI ) == None:
            GeosismaWindow.VLID_GEOM_SOPRALLUOGHI = ''

            uri = QgsDataSourceURI()
            uri.setDatabase(self.GEODATABASE_OUTNAME)
            uri.setDataSource('', self.TABLE_GEOM_SOPRALLUOGHI, 'the_geom')
            vl = QgsVectorLayer( uri.uri(), self.LAYER_GEOM_SOPRALLUOGHI, "spatialite" )
            if vl == None or not vl.isValid():
                return False

            # imposta lo stile del layer
            style_path = os.path.join( currentPath, GeosismaWindow.STYLE_FOLDER, GeosismaWindow.STYLE_GEOM_SOPRALLUOGHI )
            errorMsg, success= vl.loadNamedStyle( style_path )
            if not success:
                message = self.tr("Non posso caricare lo stile %s - %s: %s" % (GeosismaWindow.STYLE_GEOM_SOPRALLUOGHI, errorMsg, style_path) )
                self.showMessage(message, QgsMessageLog.CRITICAL)
                QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            self.iface.legendInterface().refreshLayerSymbology(vl)

            GeosismaWindow.VLID_GEOM_SOPRALLUOGHI = self._getLayerId(vl)
            self._addMapLayer(vl)
            # set custom property
            vl.setCustomProperty( "loadedByGeosismaRTPlugin", "VLID_GEOM_SOPRALLUOGHI" )
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
        # carica il layer
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

    def loadFab10kModifiedGeometries(self):
        # skip if already present
        layers = QgsMapLayerRegistry.instance().mapLayersByName(self.LAYER_GEOM_FAB10K_MODIF)
        if len(layers) > 0:
            # get id of the Geosisma layer
            valid = False
            for layer in layers:
                prop = layer.customProperty( "loadedByGeosismaRTPlugin" )
                if prop == "VLID_GEOM_FAB10K_MODIF":
                    valid = True
                    GeosismaWindow.VLID_GEOM_FAB10K_MODIF = self._getLayerId( layer )
            if not valid:
                message = self.tr("Manca il layer %s, ricaricando il plugin verrà caricato automaticamente" % self.LAYER_GEOM_FAB10K_MODIF)
                self.showMessage(message, QgsMessageLog.CRITICAL)
                QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            return
        # carica il layer
        if QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_FAB10K_MODIF ) == None:
            GeosismaWindow.VLID_GEOM_FAB10K_MODIF = ''

            uri = QgsDataSourceURI()
            uri.setDatabase(self.GEODATABASE_OUTNAME)
            uri.setDataSource('', self.TABLE_GEOM_FAB10K_MODIF, 'the_geom')
            vl = QgsVectorLayer( uri.uri(), self.LAYER_GEOM_FAB10K_MODIF, "spatialite" )
            if vl == None or not vl.isValid():
                return False

            # imposta lo stile del layer
            style_path = os.path.join( currentPath, GeosismaWindow.STYLE_FOLDER, GeosismaWindow.STYLE_GEOM_FAB10K_MODIF )
            errorMsg, success= vl.loadNamedStyle( style_path )
            if not success:
                message = self.tr("Non posso caricare lo stile %s - %s: %s" % (GeosismaWindow.STYLE_GEOM_FAB10K_MODIF, errorMsg, style_path) )
                self.showMessage(message, QgsMessageLog.CRITICAL)
                QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            self.iface.legendInterface().refreshLayerSymbology(vl)

            GeosismaWindow.VLID_GEOM_FAB10K_MODIF = self._getLayerId(vl)
            self._addMapLayer(vl)
            # set custom property
            vl.setCustomProperty( "loadedByGeosismaRTPlugin", "VLID_GEOM_FAB10K_MODIF" )
            
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
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setText(self.tr("Sicuro di voler cancellare tutti i dati locali?") )
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        msgBox.setButtonText(QMessageBox.Yes, self.tr("Si"))
        msgBox.setButtonText(QMessageBox.Cancel, self.tr("No"))
        ret = msgBox.exec_()
        if ret == QMessageBox.Cancel:
            return

        self.user = None
        self.pwd = None
        self.autenthicated = False
        self.authenticationRetryCounter = 0
        
        # close Archive db is opened
        from ArchiveManager import ArchiveManager
        ArchiveManager.instance().cleanUp()
        from GeoArchiveManager import GeoArchiveManager
        GeoArchiveManager.instance().cleanUp()
        
        # remove layer of safety geometrys and reload it
        self._removeMapLayer(self.VLID_GEOM_MODIF)
        self._removeMapLayer(self.VLID_GEOM_SOPRALLUOGHI)
        self._removeMapLayer(self.VLID_GEOM_FAB10K_MODIF)
        
        # now reset db
        from ResetDB import ResetDB
        self.resetDbDlg = ResetDB()
        self.resetDbDlg.resetDone.connect( self.manageEndResetDbDlg )
        self.resetDbDlg.exec_()
        
        # reload safety geometrys layer
        self.loadSafetyGeometries()
        self.loadSopralluoghiGeometries()
        self.loadFab10kModifiedGeometries()
        
        # reset some important globals
        self.requests = []
        self.currentRequest = None
        self.downloadedTeams = []
        self.downloadedRequests = []
        self.sopralluoghi = []
        self.fab10kModifications = []
        self.teams = None
        self.currentSafety = None
        self.updatedCurrentSafety.emit()

        # cleanup some gui elements
        self.teamComboBox.clear()
        
    def manageEndResetDbDlg(self, success):
        self.resetDbDlg.hide()

        QApplication.restoreOverrideCursor()
        if not success:
            message = self.tr("Fallito il reset del database. Controlla il Log")
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        else:
            message = self.tr("Reset avvenuto con successo. !!! Ricorda di sincronizzare il DB con il Download !!!")
            self.showMessage(message, QgsMessageLog.WARNING)
            QMessageBox.warning(self, GeosismaWindow.MESSAGELOG_CLASS, message)

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
            
            self.teams = self.downloadedTeams
            
            self.archiveTeamsDone.emit(success)
            
        except Exception as ex:
            try:
                traceback.print_exc()
            except:
                pass
            ArchiveManager.instance().close() # to avoid locking
            message = self.tr("Fallito l'archiviazione dei team")
            self.showMessage(message + ": "+ex.message, QgsMessageLog.CRITICAL)
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
            message = self.tr("Scaricate %s richieste sopralluogo" % self.downloadedRequests.__len__())
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
        success = True
        
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

            
        except Exception as ex:
            try:
                traceback.print_exc()
            except:
                pass
            ArchiveManager.instance().close() # to avoid locking
            message = self.tr(u"Fallito l'archiviazione delle richieste di sopralluogo")
            self.showMessage(message + ": "+ex.message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            success = False
        finally:
            ArchiveManager.instance().close() # to avoid locking

        # notify end of download
        self.archiveRequestsDone.emit(success)

    def downloadSopralluoghi(self, success):
        if not success:
            return

        # get extent of the fab10k layer
        layer = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_FAB10K )
        if layer == None:
            message = self.tr(u"Non posso determinare l'extent del layer: %s non verrà scaricato '%s'" % ( GeosismaWindow.LAYER_GEOM_FAB10K,GeosismaWindow.LAYER_GEOM_SOPRALLUOGHI ))
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            
            self.downloadSopralluoghiDone.emit(False)
            return

        # download all requests
        self.sopralluoghi = []
        from DownloadSopralluoghi import DownloadSopralluoghi
        self.downloadSopralluoghiDlg = DownloadSopralluoghi( bbox=layer.extent(), srid=GeosismaWindow.GEODBDEFAULT_SRID )
        self.downloadSopralluoghiDlg.done.connect( self.manageEndDownloadSopralluoghiDlg )
        self.downloadSopralluoghiDlg.message.connect(self.showMessage)
        self.downloadSopralluoghiDlg.exec_()

    def manageEndDownloadSopralluoghiDlg(self, success):
        if self.downloadSopralluoghiDlg is None:
            return
        self.downloadSopralluoghiDlg.hide()

        QApplication.restoreOverrideCursor()
        if not success:
            message = self.tr(u"Fallito lo scaricamento di '%s'. Controlla il Log" % self.LAYER_GEOM_SOPRALLUOGHI)
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        else:
            message = self.tr("Scaricati %s record di %s" % (self.sopralluoghi.__len__(), self.LAYER_GEOM_SOPRALLUOGHI) )
            self.showMessage(message, QgsMessageLog.INFO)
            QMessageBox.information(self, GeosismaWindow.MESSAGELOG_CLASS, message)

        # notify end of download
        self.downloadSopralluoghiDone.emit(success)
        
        if self.downloadSopralluoghiDlg:
            self.downloadSopralluoghiDlg.deleteLater()
        self.downloadSopralluoghiDlg = None

    def archiveSopralluoghi(self, success):
        if not success:
            return
        success = True
        
        try:
#            geomToExclude = QgsGeometry.fromWkt("MULTIPOLYGON (((1.0000000000000000 0.0000000000000000, 1.0000000000000000 1.0000000000000000, 0.0000000000000000 1.0000000000000000, 0.0000000000000000 0.0000000000000000, 1.0000000000000000 0.0000000000000000)))")
            from GeoArchiveManager import GeoArchiveManager # import here to avoid circular import
            GeoArchiveManager.instance().deleteSopralluoghi()
            for sopralluogo in self.sopralluoghi:
                
                # check if Sopralluogo has a valid geometry
                # there's no way to validate geometry... but there are default record 
                # that are set with geometry as: 
                # MULTIPOLYGON (((1.0000000000000000 0.0000000000000000, 1.0000000000000000 1.0000000000000000, 
                #                 0.0000000000000000 1.0000000000000000, 0.0000000000000000 0.0000000000000000, 
                #                 1.0000000000000000 0.0000000000000000)))
#                 try:
#                     geom = QgsGeometry.fromWkt( sopralluogo["the_geom"] )
#                     if not geom.isGeosValid():
#                         message = self.tr(u"Non archiviato Sopralluogo con gid: %d perchè ha una geometria invalida %s" % (sopralluogo["gid"], sopralluogo["the_geom"]))
#                         self.showMessage(message, QgsMessageLog.CRITICAL)
#                         continue
#                     
#                     if geom.isGeosEqual(geomToExclude):
#                         message = self.tr(u"Non archiviato Sopralluogo con gid: %d perchè ha una geometria invalida %s" % (sopralluogo["gid"], sopralluogo["the_geom"]))
#                         self.showMessage(message, QgsMessageLog.CRITICAL)
#                         continue
# 
#                 except Exception as ex:
#                     message = self.tr(u"Non archiviato Sopralluogo con gid: %d perchè ha una geometria invalida %s" % (sopralluogo["gid"], sopralluogo["the_geom"]))
#                     self.showMessage(message + ": "+ex.message, QgsMessageLog.CRITICAL)
#                     continue
                
                GeoArchiveManager.instance().archiveSopralluoghi(sopralluogo)
            GeoArchiveManager.instance().commit()
            
        except Exception as ex:
            try:
                traceback.print_exc()
            except:
                pass
            GeoArchiveManager.instance().close() # to avoid locking
            message = self.tr("Fallito l'archiviazione delle richieste di sopralluogo")
            self.showMessage(message + ": "+ex.message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            success = False
        finally:
            GeoArchiveManager.instance().close() # to avoid locking

        # notify end of download
        self.archiveSopralluoghiDone.emit(success)

    def downloadFab10kModifications(self, success):
        if not success:
            return
        
        # get extent of the fab10k layer
        layer = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_FAB10K )
        if layer == None:
            message = self.tr(u"Non posso determinare l'extent del layer: %s non verrà scaricato '%s'" % ( GeosismaWindow.LAYER_GEOM_FAB10K,GeosismaWindow.LAYER_GEOM_FAB10K_MODIF ))
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            
            self.downloadFab10kModificationsDone.emit(False)
            return
        
        # download all requests
        self.fab10kModifications = []
        from DownloadFab10kModifications import DownloadFab10kModifications
        self.downloadFab10kModificationsDlg = DownloadFab10kModifications( bbox=layer.extent(), srid=GeosismaWindow.GEODBDEFAULT_SRID )
        self.downloadFab10kModificationsDlg.done.connect( self.manageEndDownloadFab10kModificationsDlg )
        self.downloadFab10kModificationsDlg.message.connect(self.showMessage)
        self.downloadFab10kModificationsDlg.exec_()
        
    def manageEndDownloadFab10kModificationsDlg(self, success):
        if self.downloadFab10kModificationsDlg is None:
            return
        self.downloadFab10kModificationsDlg.hide()

        QApplication.restoreOverrideCursor()
        if not success:
            message = self.tr("Fallito lo scaricamento di %s. Controlla il Log" % self.LAYER_GEOM_FAB10K_MODIF)
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        else:
            message = self.tr("Scaricati %s record di %s" % (self.fab10kModifications.__len__(), self.LAYER_GEOM_FAB10K_MODIF) )
            self.showMessage(message, QgsMessageLog.INFO)
            QMessageBox.information(self, GeosismaWindow.MESSAGELOG_CLASS, message)

        # notify end of download
        self.downloadFab10kModificationsDone.emit(success)
        
        if self.downloadFab10kModificationsDlg:
            self.downloadFab10kModificationsDlg.deleteLater()
        self.downloadFab10kModificationsDlg = None

    def archiveFab10kModifications(self, success):
        if not success:
            return
        
        #QgsLogger.debug(self.tr("Dump di Teams e Requests scaricate: %s" % json.dumps( self.downloadedTeams )), 2 )
        try:
            from GeoArchiveManager import GeoArchiveManager # import here to avoid circular import
            # remove all local modification that has already been archived
            GeoArchiveManager.instance().deleteArchivedFab10kModifications()
            for modification in self.fab10kModifications:
                GeoArchiveManager.instance().archiveFab10kModifications(modification)
                
            GeoArchiveManager.instance().commit()
            success = True

        except Exception as ex:
            success = False
            try:
                traceback.print_exc()
            except:
                pass
            GeoArchiveManager.instance().close() # to avoid locking
            message = self.tr("Fallito l'archiviazione delle modifiche a %s" % self.LAYER_GEOM_FAB10K_MODIF)
            self.showMessage(message + ": "+ex.message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        finally:
            GeoArchiveManager.instance().close() # to avoid locking

        self.archiveFab10kModificationsDone.emit(success)
    
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
    
    def zoomToExtent(self, boundingBox, transform=True):
        geom = QgsGeometry.fromWkt(boundingBox.asWktPolygon())
        if transform:
            # bbox arrive in DB coordinate 32632 => convert in default view coordinate 3003
            defaultCrs = QgsCoordinateReferenceSystem(self.DEFAULT_SRID)  # WGS 84 / UTM zone 33N
            geoDbCrs = QgsCoordinateReferenceSystem(self.GEODBDEFAULT_SRID)  # WGS 84 / UTM zone 33N
            xform = QgsCoordinateTransform(geoDbCrs, defaultCrs)
            if geom.transform(xform):
                message = self.tr("Errore nella conversione del bbox del DB a quello del progetto")
                self.showMessage(message, QgsMessageLog.WARNING)
                return
        self.iface.mapCanvas().setExtent(geom.boundingBox())
        self.iface.mapCanvas().refresh()
    
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
        self.iface.mapCanvas().refresh()

    def selectSafety(self, gid=None):
        # get id of the current selected safety
        local_id = None
        if self.currentSafety is not None and not gid:
            local_id = self.currentSafety["local_id"]
            
        from DlgSelectSafety import DlgSelectSafety
        dlg = DlgSelectSafety(currentSafetyId=local_id, gid=gid)

        # cancel because no results to show
        if len(dlg.records) == 0 :
            if gid:
                message = u"Nessuna scheda associata alla particella"
            elif local_id:
                message = u"Nessuna scheda con local_id %" % local_id
            else:
                message = u"Nessuna scheda disponibile"
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("RT Geosisma")
            msgBox.setInformativeText(self.tr( message ))
            msgBox.setStandardButtons(QMessageBox.Yes)
            msgBox.setButtonText(QMessageBox.Yes, self.tr("Ok"))
            ret = msgBox.exec_()
            dlg.deleteLater()
            return

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
    
    def selectSafetiesToUpload(self, gid=None):
        # get id of the current selected safety
        local_id = None
        if self.currentSafety is not None and not gid:
            local_id = self.currentSafety["local_id"]
            
        from DlgUploadSafeties import DlgUploadSafeties
        dlg = DlgUploadSafeties(currentRecordId=local_id, gid=gid)

        # cancel because no results to show
        if len(dlg.records) == 0 :
            if gid:
                message = u"Nessuna scheda associata alla particella"
            elif local_id:
                message = u"Nessuna scheda con local_id %" % local_id
            else:
                message = u"Nessuna scheda disponibile"
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("RT Geosisma")
            msgBox.setInformativeText(self.tr( message ))
            msgBox.setStandardButtons(QMessageBox.Yes)
            msgBox.setButtonText(QMessageBox.Yes, self.tr("Ok"))
            msgBox.exec_()
            dlg.deleteLater()
            return

        ret = dlg.exec_()
        
        # check if result set
        if ret != 0:
            recordsToUpload = []
            if (dlg.buttonSelected == "Save"): # Means Upload the selected safeties records
                if dlg.selected is None or len(dlg.selected) == 0:
                    return
                
                recordsToUpload = dlg.selected
     
            elif (dlg.buttonSelected == "SaveAll"): # means upload all safeties
                # add to the list only safety to be uploaded
                for record in dlg.records:
                    if str(record["id"]) != "-1":
                        continue
                    if record["the_geom"] == None or record["the_geom"] == "":
                        continue
                    recordsToUpload.append(record)
            
            # then upload
            if len(recordsToUpload) == 0:
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Information)
                msgBox.setText(u"Non ci sono schede da caricare sul server")
                msgBox.setStandardButtons(QMessageBox.Yes)
                msgBox.setButtonText(QMessageBox.Yes, self.tr("Ok"))
                msgBox.exec_()
                return
            
            self.uploadSafeties( recordsToUpload )
        
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
        QgsLogger.debug("updateCurrentSafetyFromForm entered",2 )
        if safetyDict == None:
            return
        
        # check if safetyNumber is changed
        subSafetyDict = json.loads( safetyDict["safety"] )
        if self.currentSafety["number"] != subSafetyDict["number"]:
            # check if number is laready kept
            from ArchiveManager import ArchiveManager # import here to avoid circular import
            safety_numbers = ArchiveManager.instance().loadSafetyNumbers()
            if int(subSafetyDict["number"]) in [int(v) for v in safety_numbers]:
                message = self.tr(u"Scheda non salvata. Il numero di scheda %s è giá presente. Scegline un'altro" % subSafetyDict["number"])
                self.showMessage(message, QgsMessageLog.WARNING)
                QMessageBox.warning(self, GeosismaWindow.MESSAGELOG_CLASS, message)
                return
            
            #modify safetyNumber of the record
            self.currentSafety["number"] = subSafetyDict["number"]
        
        self.currentSafety["date"] = subSafetyDict["sdate"]
        self.currentSafety["safety"] = safetyDict["safety"]
        self.updatedCurrentSafety.emit()
        
        QgsLogger.debug("updateCurrentSafetyFromForm exit",2 )
    
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
            
        except Exception as ex:
            try:
                traceback.print_exc()
            except:
                pass
            ArchiveManager.instance().close() # to avoid locking
            message = self.tr("Fallito l'update della scheda di sopralluogo")
            self.showMessage(message + ": "+ex.message, QgsMessageLog.CRITICAL)
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
            
        except Exception as ex:
            try:
                traceback.print_exc()
            except:
                pass
            ArchiveManager.instance().close() # to avoid locking
            message = self.tr("Fallito l'archiviazione della scheda di sopralluogo")
            self.showMessage(message + ": "+ex.message, QgsMessageLog.CRITICAL)
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
        request_id = dlg.selectedRequestId
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
            if str(request["id"]) != str(request_id):
                continue
            keys = ["s1prov", "s1com", "s1loc", "s1via", "s1civico", "s1catfoglio", "s1catpart1"]
            for k in keys:
                if request[k] != "":
                    subSafety[k] = '%s' % str(request[k])
            break

        safety = "%s" % json.dumps(subSafety)
        self.currentSafety = {"local_id":None, "id":-1, "created":dateIso, "request_id":request_id, "safety":safety, "team_id":team_id, "number":safety_number, "date":dateForForm, "gid_catasto":"", "the_geom":None}
        
        self.updatedCurrentSafety.emit() # thi will save new safety on db and update gui
        self.initNewCurrentSafetyDone.emit()
        QgsLogger.debug("initNewCurrentSafety exit",2 )
    
    def deleteCurrentSafety(self):
        QgsLogger.debug("deleteCurrentSafety entered",2 )
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setText(self.tr("Sicuro di cancellare la scheda %s ?" % self.currentSafety["number"]))
        msgBox.setInformativeText(self.tr(u"L'operazione cancellerà definitivamente la scheda dal database"))
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
            
        except Exception as ex:
            try:
                traceback.print_exc()
            except:
                pass
            ArchiveManager.instance().close() # to avoid locking
            message = self.tr("Fallita la cancellazione della scheda %s" % self.currentSafety["number"])
            self.showMessage(message + ": "+ex.message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        finally:
            ArchiveManager.instance().close() # to avoid locking

        QgsLogger.debug("deleteCurrentSafety exit",2 )

    def manageGuiStatus(self):
        if self.currentSafety == None:
            self.btnDeleteCurrentSafety.setText("Elimina [%s]" % "--")
            self.btnDeleteCurrentSafety.setEnabled(False)
            
            self.btnLinkSafetyGeometry.setEnabled(False)
            #self.btnListLinkedSafeties.setEnabled(False)
            self.btnNewSafetyGeometry.setEnabled(False)
            self.btnZoomToSafety.setEnabled(False)
            self.btnManageAttachments.setEnabled(False)
        else:
            self.btnDeleteCurrentSafety.setText("Elimina [%s]" % self.currentSafety["number"])
            self.btnDeleteCurrentSafety.setEnabled(True)
            #self.btnSelectSafety.setText("Apri [%s]" % self.currentSafety["number"])
        
            self.btnLinkSafetyGeometry.setEnabled(True)
            #self.btnListLinkedSafeties.setEnabled(True)
            self.btnNewSafetyGeometry.setEnabled(True)
            self.btnZoomToSafety.setEnabled(True)
            self.btnManageAttachments.setEnabled(True)

        if self.currentRequest == None:
            self.btnSelectRequest.setText("Seleziona Richiesta [%s]" % "--")
        else:
            self.btnSelectRequest.setText("Seleziona Richiesta [%s]" % self.currentRequest["number"])
        
    @classmethod
    def checkActionScale(cls, actionName, maxScale):
        if int(cls.instance().canvas.scale()) > maxScale:
            QMessageBox.warning( cls.instance(), "Azione non permessa", u"L'azione \"%s\" è ammessa solo dalla scala 1:%d" % (actionName, maxScale) )
            return False
        return True

    def zoomToSafety(self):
        QgsLogger.debug("zoomToSafety entered",2 )
        if self.currentSafety == None:
            return
        
        if self.currentSafety["the_geom"] == None or self.currentSafety["the_geom"] == "":
            QMessageBox.warning( self, "Poligono inesistente", u"Nessun poligono associato alla scheda n.%s" % self.currentSafety["number"])
            return
        
        # get bbox of the current safety geometry
        geom = QgsGeometry.fromWkt(self.currentSafety["the_geom"])
        bbox = geom.boundingBox()
        
        # zoom to bbox
        self.zoomToExtent(bbox, transform=False)
        
    def selectCurrentSafetyFeature(self):
        QgsLogger.debug("selectCurrentSafetyFeature entered",2 )
        if self.currentSafety == None:
            return
        
        layerModified = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_MODIF )
        if layerModified:
            layerModified.removeSelection()
            layerModified.select(self.currentSafety["local_id"])

    def createNewSafetyGeometry(self, polygon=None):
        QgsLogger.debug("createNewSafetyGeometry entered",2 )
        if self.currentSafety == None:
            QMessageBox.warning( self, "Nessuna scheda corrente", u"Creare o selezionare almeno una scheda su cui creare/sostituire il poligono")
            self.btnNewSafetyGeometry.setChecked(False)
            return
        
        # if exist polygon and is the first time activated the funzion (polygon=None)
        if (self.currentSafety["the_geom"] != None and
            self.currentSafety["the_geom"] != "" and
            polygon == None):
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setText(self.tr(u"Esiste già un poligono associato alla scheda n.%s ?" % self.currentSafety["number"]) )
            msgBox.setInformativeText(self.tr("Vuoi sostituirlo con un nuovo poligono?"))
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            msgBox.setButtonText(QMessageBox.Yes, self.tr("Si"))
            msgBox.setButtonText(QMessageBox.Cancel, self.tr("No"))
            ret = msgBox.exec_()
            if ret == QMessageBox.Cancel:
                self.btnNewSafetyGeometry.setChecked(False)
                return

        # set current active layer VLID_GEOM_MODIF
        currentActiveLayer = self.iface.activeLayer()
        if self._getLayerId(currentActiveLayer) != GeosismaWindow.VLID_GEOM_MODIF:
            layer = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_MODIF )
            self.iface.setActiveLayer(layer)

        action = self.btnNewSafetyGeometry.toolTip()

        if not self.checkActionScale( action, self.SCALE_MODIFY ):
            self.newSafetyGeometryDrawer.startCapture()
            self.newSafetyGeometryDrawer.stopCapture()
            self.btnNewSafetyGeometry.setChecked(False)
            return
        if polygon == None:
            return self.newSafetyGeometryDrawer.startCapture()
        
        # try to convert to multypolygon to match DB constraint
        if not polygon.isMultipart():
            if not polygon.convertToMultiType(): 
                QMessageBox.critical( self, "RT Geosisma", self.tr("Non posso convertire la geometria disegnata in Multipolygon") )
                self.btnNewSafetyGeometry.setChecked(False)
                return
            
        self.currentSafety["the_geom"] = polygon.exportToWkt()
        self.btnNewSafetyGeometry.setChecked(False)

        self.updatedCurrentSafety.emit() # thi will save new safety on db and update gui

    def linkSafetyGeometry(self, point=None, button=None):
        if self.currentSafety == None:
            self.btnLinkSafetyGeometry.setChecked(False)
            return
        
        action = self.btnLinkSafetyGeometry.toolTip()
        if not self.checkActionScale( action, self.SCALE_IDENTIFY ) or point == None:
            return self.linkSafetyGeometryEmitter.startCapture()

        if button != Qt.LeftButton:
            self.btnLinkSafetyGeometry.setChecked(False)
            return

        layerModif = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_MODIF )
        layerOrig = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_ORIG )
        if layerOrig == None and layerModif == None:
            self.btnLinkSafetyGeometry.setChecked(False)
            return

        featModif = self.linkSafetyGeometryEmitter.findAtPoint(layerModif, point) if layerOrig != None else None
        featOrig = self.linkSafetyGeometryEmitter.findAtPoint(layerOrig, point) if layerOrig != None else None
        
        # if no features found... continue campturing mouse
        if featModif == None and featOrig == None:
            return self.linkSafetyGeometryEmitter.startCapture()
            
        
        # check whato to do
        getFromCatasto = False
        getFromSafety = False
        if featOrig != None and featModif == None:
            getFromCatasto = True
        if featOrig == None and featModif != None:
            getFromSafety = True
        if featOrig != None and featModif != None:
            # then ask
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setText("RT Geosisma")
            msgBox.setInformativeText(self.tr(u"Presenti geometrie Schede e Catasto su questo punto. Cosa vuoi fare?"))
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel | QMessageBox.Open)
            msgBox.setButtonText(QMessageBox.Yes, self.tr("Associa geometria catastale"))
            msgBox.setButtonText(QMessageBox.Open, self.tr("Associa a una parte"))
            msgBox.setButtonText(QMessageBox.Cancel, self.tr("Annulla, associo un'altra geometria"))
            ret = msgBox.exec_()
            if ret == QMessageBox.Cancel:
                # continue on another geometry
                return self.linkSafetyGeometryEmitter.startCapture()
            if ret == QMessageBox.Yes:
                getFromCatasto = True
            if ret == QMessageBox.Open:
                getFromSafety = True
        
        # delesect records
        if featOrig:
            gid = featOrig["gid"]
            layerOrig.deselect(gid)
        if featModif:
            local_id = featModif["local_id"]
            layerModif.deselect(local_id)
        
        # copy from Particella (nominal case)
        if getFromCatasto:
            from ArchiveManager import ArchiveManager

            # controlla se tale geometria ha qualche scheda associata
            features = ArchiveManager.instance().loadSafetiesByCatasto(gid)
            
            # get all local_id but not of the current one
            associated_features = [feature for feature in features if feature["local_id"] != self.currentSafety["local_id"] ]
            
            # if previous list is != 0
            if len(associated_features) > 0:
                
                safety_numbers = [feature["number"] for feature in associated_features]
                
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Warning)
                msgBox.setText("RT Geosisma")
                msgBox.setInformativeText(self.tr(u"Già presenti le schede %s su questa particella. Vuoi continuare?" % str(safety_numbers) ))
                msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
                msgBox.setButtonText(QMessageBox.Yes, self.tr("Si"))
                msgBox.setButtonText(QMessageBox.Cancel, self.tr("No: seleziono un'altra geometria"))
                ret = msgBox.exec_()
                if ret == QMessageBox.Cancel:
                    # continue on another geometry
                    return self.linkSafetyGeometryEmitter.startCapture()
                
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            # associa il poligono alla safety
            crs = layerOrig.dataProvider().crs()
            
            self.updateCurrentSafetyWithCatasto(crs, featOrig, point)
            
        # copy from safety geometry (enhanced linking)
        if getFromSafety:
            # check if feature already belongs to current safety
            if featModif["local_id"] == self.currentSafety["local_id"]:
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Warning)
                msgBox.setText("RT Geosisma")
                msgBox.setInformativeText(self.tr(u"Il poligono già appartiene alla scheda corrente. Seleziona un'altra geometria!"))
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.exec_()
                return self.linkSafetyGeometryEmitter.startCapture()
            
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            # associa il poligono alla safety
            self.updateCurrentSafetyWithSafetyPolygon(featModif, point)
            
        self.canvas.refresh()
        QApplication.restoreOverrideCursor()
        self.btnLinkSafetyGeometry.setChecked(False)


    def listLinkedSafeties(self, point=None, button=None):
        action = self.btnListLinkedSafeties.toolTip()
        if not self.checkActionScale( action, self.SCALE_IDENTIFY ) or point == None:
            return self.lookForSafetiesEmitter.startCapture()

        if button != Qt.LeftButton:
            self.btnListLinkedSafeties.setChecked(False)
            return

        layerOrig = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_ORIG )
        if layerOrig == None:
            self.btnListLinkedSafeties.setChecked(False)
            return

        feat = self.lookForSafetiesEmitter.findAtPoint(layerOrig, point)
        if feat != None:
            # already get => unselect if
            gid = feat["gid"]
            layerOrig.deselect(gid)
            
            # show list of safeties related to gid
            self.btnListLinkedSafeties.setChecked(False)
            self.selectSafety(gid=gid)
            
        else:
            self.lookForSafetiesEmitter.startCapture()

    def cleanUnlinkedSafeties(self):
        QgsLogger.debug("cleanUnlinkedSafeties entered",2 )
        try:
            from ArchiveManager import ArchiveManager # import here to avoid circular import
            # get list of unlinked safeties
            safeties = ArchiveManager.instance().loadUnlikedSafeties()
            if len(safeties) == 0:
                QMessageBox.warning( self, "Nessuna scheda da cancellare", u"Non ci sono schede non associate a particelle")
                return
            
            listOfSafeties = [x["number"] for x in safeties]
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setText(self.tr(u"Sicuro di cancellare le schede %s ?" % str(listOfSafeties) ) )
            msgBox.setInformativeText(self.tr(u"L'operazione cancellerà definitivamente le schede elencate dal database"))
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            msgBox.setButtonText(QMessageBox.Yes, self.tr("Si"))
            msgBox.setButtonText(QMessageBox.Cancel, self.tr("No"))
            ret = msgBox.exec_()
            if ret == QMessageBox.Cancel:
                return
    
            resetCurrentSafety = False
            for safety in safeties:
                QgsLogger.debug(self.tr("Cancella safety %s" % json.dumps( self.currentSafety )) )
                ArchiveManager.instance().deleteSafety(safety["local_id"])
                ArchiveManager.instance().commit()
                ArchiveManager.instance().deleteAttachmentsBySasfety(safety["local_id"])
                ArchiveManager.instance().commit()
                
                if self.currentSafety and (safety["local_id"] == self.currentSafety["local_id"]):
                    resetCurrentSafety = True
            
            if resetCurrentSafety:
                # reset current safety
                self.currentSafety = None
                self.updatedCurrentSafety.emit()
            
        except Exception as ex:
            try:
                traceback.print_exc()
            except:
                pass
            ArchiveManager.instance().close() # to avoid locking
            message = self.tr(u"Fallita la cancellazione delle schede non associate")
            self.showMessage(message + ": "+ex.message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        finally:
            ArchiveManager.instance().close() # to avoid locking

        QgsLogger.debug("cleanUnlinkedSafeties exit",2 )
        

    def updateCurrentSafetyWithSafetyPolygon(self, feature, point):
        '''
        Method update CurrentSafety with element get from Safety Geometries
        @param feature: QgsFeature of the original safety
        @param point: QgsPoint where user cliked
        @signal currentSafetyModified
        '''
        if self.currentSafety == None:
            return

        fieldNames = [field.name() for field in feature.fields()]
        featureDic = dict(zip(fieldNames, feature.attributes()))
        
        tempSafety = copy.copy( self.currentSafety )
        
        # check if there is already a geometry in the current safety
        # => ask if you want to add a new particella or reset if it 
        # refer to the same geometry
        substituteMode = False
        unifyMode = False
        
        if (tempSafety["the_geom"] == None) or (tempSafety["the_geom"] == ""):
            substituteMode = True
            tempSafety["gid_catasto"] = ""
            tempSafety["the_geom"] = None
        else:
            # ask what to do in case ther is already a geometryu
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setText("RT Geosisma")
            msgBox.setInformativeText(self.tr(u"La scheda ha già una geometria associata\nCosa vuoi fare?"))
            msgBox.setStandardButtons(QMessageBox.Reset | QMessageBox.Cancel | QMessageBox.Yes)
            msgBox.setButtonText(QMessageBox.Reset, self.tr("Sostituire"))
            msgBox.setButtonText(QMessageBox.Yes, self.tr("Unire"))
            msgBox.setButtonText(QMessageBox.Cancel, self.tr("Nulla"))
            ret = msgBox.exec_()
            # if ignore do nothing
            if ret == QMessageBox.Cancel:
                return
            # if unify then do nothing... the feature will be added to the current values of geom
            elif ret == QMessageBox.Yes:
                unifyMode = True
                pass
            # if substitute then reset current safety geometry and pass... next steps will add selected geometry
            elif ret == QMessageBox.Reset:
                substituteMode = True
                tempSafety["gid_catasto"] = ""
                tempSafety["the_geom"] = None
        
        # copy origin to current
        # updating safety json with fixed data in the current safety
        # e.g avoid the hineritance of safety number, team number, and all already set data
        # in the current safety
        currentSafetyDict = json.loads( self.currentSafety["safety"] )
        tempSafetyDict = json.loads( featureDic["safety"] )
        for k in currentSafetyDict.keys():
            tempSafetyDict[k] = currentSafetyDict[k]

        tempSafety["safety"] = json.dumps(tempSafetyDict)
        tempSafety["gid_catasto"] = featureDic["gid_catasto"]
        
        # get current Part that intersect point in the origin multipolygon
        sourceGeom = feature.geometry()
        sourceMultyPartGeom = sourceGeom.asMultiPolygon()
        updatedSourceGeom = QgsGeometry()
        newDestinationGeom = QgsGeometry()
        for part in sourceMultyPartGeom:
            partGeom = QgsGeometry.fromPolygon(part)
            if (partGeom.contains(point)):
                newDestinationGeom.addPart(part[0], QGis.Polygon)
            else:
                updatedSourceGeom.addPart(part[0], QGis.Polygon)
        
        # manage geometry
        if substituteMode:
            # get safety geometry converting to MultyPolygon (that is a DB contraint)
            # this is necessary because  QgsGeometry.fromWkt tries to convert to simple POLYGON if
            # actuals safety geometry has only one polygon.
            newDestinationGeom = QgsGeometry.fromWkt( newDestinationGeom.exportToWkt() )
            if not newDestinationGeom.isMultipart():
                if not newDestinationGeom.convertToMultiType(): 
                    QMessageBox.critical( self, "RT Geosisma", self.tr("Non posso convertire la geometria della scheda in Multipolygon") )
                    return
            
            tempSafety["the_geom"] = newDestinationGeom.exportToWkt()
        
        if unifyMode:
            # get safety geometry converting to MultyPolygon (that is a DB contraint)
            # this is necessary because  QgsGeometry.fromWkt tries to convert to simple POLYGON if
            # actuals safety geometry has only one polygon.
            safetyGeometry = QgsGeometry.fromWkt( tempSafety["the_geom"] )
            if not safetyGeometry.isMultipart():
                if not safetyGeometry.convertToMultiType(): 
                    QMessageBox.critical( self, "RT Geosisma", self.tr("Non posso convertire la geometria della scheda in Multipolygon") )
                    return

            # add polygon in the current safety multypolygon
            safetyGeometry = safetyGeometry.combine(newDestinationGeom)
            
            # again convert to Multypolygon beacuse QgsGeometry.combine create one Polygon if
            # the two geometry are adiacent and the result is a unique Polygon
            if not safetyGeometry.isMultipart():
                if not safetyGeometry.convertToMultiType(): 
                    QMessageBox.critical( self, "RT Geosisma", self.tr("Non posso convertire la geometria della scheda in Multipolygon") )
                    return

            # update geometry in the safety
            tempSafety["the_geom"] = safetyGeometry.exportToWkt()
        
        # now update origin safety with the new Multypoligon without the part that has been moved to current safety

        # get source geometry converting to MultyPolygon (that is a DB contraint)
        # this is necessary because  QgsGeometry.fromWkt tries to convert to simple POLYGON if
        # actuals safety geometry has only one polygon.
        updatedSourceGeom = QgsGeometry.fromWkt( updatedSourceGeom.exportToWkt() )
        if not updatedSourceGeom.isMultipart():
            if not updatedSourceGeom.convertToMultiType(): 
                QMessageBox.critical( self, "RT Geosisma", self.tr("Non posso convertire la geometria sorgente della scheda in Multipolygon") )
                return
        
        layerModif = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_MODIF )
        if not layerModif.dataProvider().changeGeometryValues( { featureDic["local_id"]: updatedSourceGeom } ):
            errors = layerModif.dataProvider().errors()
            QMessageBox.critical( self, "RT Geosisma", self.tr("Errore eliminando poligono dalla sheda di origine %s" % str(errors)) )
            return
        
        # at the end update currentSafety and emit signal
        self.currentSafety = tempSafety        
        self.updatedCurrentSafety.emit()
        
    def updateCurrentSafetyWithCatasto(self, geoDbCrs, feature, point):
        '''
        Method update CurrentSafety with element related to current original feature (from catasto)
        @param crs: QgsCoordinateReferenceSystem of the feature geometry
        @param feature: QgsFeature of the original catasto layer
        @param point: QgsPoint where user cliked
        @signal currentSafetyModified
        '''
        if self.currentSafety == None:
            return
        
        fieldNames = [field.name() for field in feature.fields()]
        featureDic = dict(zip(fieldNames, feature.attributes()))
        
        tempSafety = copy.copy( self.currentSafety )
        
        # check if there is already a geometry in the current safety
        # => ask if you want to add a new particella or reset if it 
        # refer to the same geometry
        associateMode = False
        substituteMode = False
        unifyMode = False
        
        if (tempSafety["the_geom"] == None) or (tempSafety["the_geom"] == ""):
            substituteMode = True
        else:
            # check if safety geometry is referred to the same feature
            gidToFind = "_%s_" % featureDic["gid"]
            index = tempSafety["gid_catasto"].find(gidToFind)
            if index < 0:
                # it's a new particella
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Warning)
                msgBox.setText("RT Geosisma")
                msgBox.setInformativeText(self.tr(u"La scheda ha già una geometria associata\nCosa vuoi fare?"))
                msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel | QMessageBox.Open)
                msgBox.setButtonText(QMessageBox.Yes, self.tr("Associare"))
                msgBox.setButtonText(QMessageBox.Reset, self.tr("Sostituire"))
                msgBox.setButtonText(QMessageBox.Open, self.tr("Unire"))
                msgBox.setButtonText(QMessageBox.Cancel, self.tr("Nulla"))
                ret = msgBox.exec_()
                # if ignore do nothing
                if ret == QMessageBox.Cancel:
                    return
                # if unify then do nothing... the feature will be added to the current values of geom
                elif ret == QMessageBox.Open:
                    unifyMode = True
                    pass
                # only associate particella to the current geometry without modifing it
                elif ret == QMessageBox.Yes:
                    associateMode = True
                    pass
                # if substitute then reset current safety geometry and pass... next steps will add selected geometry
                elif ret == QMessageBox.Reset:
                    substituteMode = True
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
                    return self.linkSafetyGeometryEmitter.startCapture()
                tempSafety["gid_catasto"] = ""
                tempSafety["the_geom"] = None
                substituteMode = True

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
        
        # manage geometry
        if substituteMode:
            tempSafety["the_geom"] = featureGeometry.exportToWkt()
        
        if unifyMode:
            # create geometry from current safety geometry
            featureMultiPolygon = featureGeometry.asMultiPolygon()
            if len(featureMultiPolygon) == 0:
                QMessageBox.critical( self, "RT Geosisma", self.tr("La geometria della scheda corrente non e' Multipolygon") )
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
        
        if associateMode:
            pass
        
        # record reference to the related cataasto polygons
        if substituteMode:
            tempSafety["gid_catasto"] = "_%d_" % featureDic["gid"]
        
        if associateMode or unifyMode:
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
    ###### section to manage Aggregati creation and modification
    ###############################################################

    def selectFab10kmodToUpload(self):
        # get TeamId from teamName
        team_id = None
        teamName = self.teamComboBox.currentText()
        if teamName == "":
            message = self.tr( u"Nessun team specificato a cui associare le modifiche al layer %s" % self.LAYER_GEOM_FAB10K_MODIF )
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText(message)
            msgBox.setStandardButtons(QMessageBox.Yes)
            msgBox.setButtonText(QMessageBox.Yes, self.tr("Ok"))
            msgBox.exec_()
            return
        for team in self.teams:
            if str(team["name"]) == teamName:
                team_id = team["id"]
                break
        
        from DlgUploadFab10kmod import DlgUploadFab10kmod
        dlg = DlgUploadFab10kmod( teamId=team_id )

        # cancel because no results to show
        if len(dlg.records) == 0 :
            message = self.tr( u"Nessun record %s disponibile" % self.LAYER_GEOM_FAB10K_MODIF )
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText(message)
            msgBox.setStandardButtons(QMessageBox.Yes)
            msgBox.setButtonText(QMessageBox.Yes, self.tr("Ok"))
            msgBox.exec_()
            dlg.deleteLater()
            return

        ret = dlg.exec_()
        
        # check if result set
        if ret != 0:
            recordsToUpload = []
            if (dlg.buttonSelected == "Save"): # Means Upload the selected fab10kmod records
                if dlg.selected is None or len(dlg.selected) == 0:
                    return
                
                recordsToUpload = dlg.selected
     
            elif (dlg.buttonSelected == "SaveAll"): # means upload all safeties
                # add to the list only safety to be uploaded
                for record in dlg.records:
                    if str(record["gid"]) != "-1":
                        continue
                    recordsToUpload.append(record)
            
            # then upload
            self.uploadFab10kmod( recordsToUpload )

    def uploadFab10kmod(self, records):
        if records is None or len(records) == 0:
            return
        from UploadManagerFab10kModifications import UploadManagerFab10kModifications
        self.UploadManagerFab10kModificationsDlg = UploadManagerFab10kModifications()
        self.UploadManagerFab10kModificationsDlg.initRecords(records)
        self.UploadManagerFab10kModificationsDlg.done.connect( self.manageEndUploadFasb10kmodDlg )
        self.UploadManagerFab10kModificationsDlg.message.connect(self.showMessage)
        self.UploadManagerFab10kModificationsDlg.exec_()

    def manageEndUploadFasb10kmodDlg(self, success):
        if self.UploadManagerFab10kModificationsDlg is None:
            return
        self.UploadManagerFab10kModificationsDlg.hide()

        QApplication.restoreOverrideCursor()
        if not success:
            message = self.tr("Fallito l'Upload dei record %s. Controlla il Log" % self.LAYER_GEOM_FAB10K_MODIF)
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        else:
            message = self.tr("Upload avvenuto con successo")
            self.showMessage(message, QgsMessageLog.INFO)
            QMessageBox.information(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        
        # get updated safeties
        updatedRecords = self.UploadManagerFab10kModificationsDlg.updatedRecords

        from GeoArchiveManager import GeoArchiveManager
        for modifiedRecord in updatedRecords:
            GeoArchiveManager.instance().updateFab10kModifications(modifiedRecord)
            GeoArchiveManager.instance().commit()
            
        # notify end of download
        self.uploadFab10kmodDone.emit(success)
        
        if self.UploadManagerFab10kModificationsDlg:
            self.UploadManagerFab10kModificationsDlg.deleteLater()
        self.UploadManagerFab10kModificationsDlg = None

    def createNewAggregatiGeometry(self, polygon=None):
        QgsLogger.debug("createNewAggregatiGeometry entered",2 )
        
        # set current active layer VLID_GEOM_FAB10K_MODIF
        currentActiveLayer = self.iface.activeLayer()
        if self._getLayerId(currentActiveLayer) != GeosismaWindow.VLID_GEOM_FAB10K_MODIF:
            currentActiveLayer = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_FAB10K_MODIF )
            self.iface.setActiveLayer(currentActiveLayer)
        
        action = self.btnNewAggregatiGeometry.toolTip()

        if not self.checkActionScale( action, self.SCALE_MODIFY ):
            self.newAggregatiDrawer.startCapture()
            self.newAggregatiDrawer.stopCapture()
            self.btnNewSafetyGeometry.setChecked(False)
            return
        if polygon == None:
            return self.newAggregatiDrawer.startCapture()
        
        # try to convert to polygon to match DB constraint
        # could be more efficiend usign dict compherension
        # but I prefere readability when there's no performance problems
        # iterating on all features
        if polygon.isMultipart():
            polygon = polygon.convertToType(QGis.Polygon, False)
            if polygon == None:
                QMessageBox.critical( self, "RT Geosisma", self.tr(u"La geometria disegnata è Multipolygon. Non posso convertirla in Polygon") )
                self.btnNewSafetyGeometry.setChecked(False)
                return
        
        # find nearest fab_10k record to state the value of identif field
        nearestfeat = self.getNearestAggregato(polygon)
        if nearestfeat == None:
            return
        
        # determine new aggregato identif basing on the nearest aggregato
        # new aggregato is specified as in specifiche aggregati.odt ​
        newidentif = nearestfeat["identif"]+"51"
        
        # set team_id
#         settings = QSettings()
#         teamUrl = settings.value("/rt_geosisma_offline/teamUrl", "/api/v1/team/")
#         team_id = teamUrl + str(self.currentSafety["team_id"]) + "/"

        # build the new record
        if not polygon.convertToMultiType():
            message = self.tr(u"Problemi convertendo in multiplygon il nuovo poligono")
            self.showMessage(message, QgsMessageLog.WARNING)
            QMessageBox.warning(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            return
        newAggregato = self.initNewAggregatiDict()
        newAggregato["identif"] = newidentif
        newAggregato["fab_10k_gid"] = nearestfeat["gid"]
        
        newAggregato["the_geom"] = polygon.exportToWkt()
        
        #save newAggregato in DB
        from GeoArchiveManager import GeoArchiveManager
        try:
            GeoArchiveManager.instance().archiveFab10kModifications(newAggregato)
            GeoArchiveManager.instance().commit()
            
            newAggregato["local_gid"] = GeoArchiveManager.instance().getLastRowId()
            message = self.tr("Inserito nuovo record %s con id %s" % ( self.LAYER_GEOM_FAB10K_MODIF ,newAggregato["local_gid"]) )
            self.showMessage(message, QgsMessageLog.INFO)
            
        except Exception as ex:
            try:
                traceback.print_exc()
            except:
                pass
            message = self.tr(u"Fallito il salvataggio del nuovo record %s con identificativo %s" % (self.LAYER_GEOM_FAB10K_MODIF, newidentif) )
            self.showMessage(message + ": "+ex.message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        finally:
            GeoArchiveManager.instance().close() # to avoid locking
        
        # redraw canvas to paint new added records
        self.iface.mapCanvas().refresh() 
        
        self.btnNewAggregatiGeometry.setChecked(False)


    def initNewAggregatiDict(self):
        teamName = self.teamComboBox.currentText()
        for team in self.teams:
            if str(team["name"]) == teamName:
                team_id = team["id"]
                break

        newAggregato = {}
        newAggregato["local_gid"] = None
        newAggregato["gid"] = -1 # <--- it's new so it's not yet archived on remote server
        newAggregato["identif"] = None
        newAggregato["fab_10k_gid"] = None
        newAggregato["mod_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        newAggregato["team_id"] = team_id
        newAggregato["upload_time"] = None
        newAggregato["the_geom"] = None
        
        return newAggregato


    def getNearestAggregato(self, polygon):
        """
        find the nearest Aggregato to the input polygon
        @param polygon: target polygon to measure nearest distance
        @return feature: nearest Aggregato feature
        """
        QgsLogger.debug("getNearestAggregato entered",2 )
        
        # tranform input polygon to VLID_GEOM_FAB10K crs
        defaultCrs = QgsCoordinateReferenceSystem(self.DEFAULT_SRID)  # WGS 84 / UTM zone 33N
        geoDbCrs = QgsCoordinateReferenceSystem(self.GEODBDEFAULT_SRID)  # WGS 84 / UTM zone 33N
        xform = QgsCoordinateTransform(defaultCrs, geoDbCrs)
        if polygon.transform(xform):
            QMessageBox.critical( self, "RT Geosisma", self.tr("Errore nella conversione del poligono al CRS di %s: %d" % (self.LAYER_GEOM_FAB10K, self.GEODBDEFAULT_SRID) ))
            return None
        
        # could be implemented getting nearest point to polygon, than intersect this point
        # with the feature and get this last feature. But I implemented a readable solution that
        # shouldn't have performance problems
        nearest = {"distance":999999999999999999999999999999999, "feature":None}
        layer = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_FAB10K )
        for feat in layer.getFeatures():
            distance = polygon.distance( feat.geometry() )
            if distance != 0 and distance < nearest["distance"]:
                nearest["distance"] = distance
                nearest["feature"] = feat
        return nearest["feature"]
        
        
    def modifyAggregatiGeometry(self, point=None, button=None):
        """
        function to manage action to modify an existing Aggregaty polygon
        using default qgis edit tools and intercepting standard edit events
        @param point: point on canvas to point the Aggregato to modify
        @param button: what buttn has been pressed
        """
        QgsLogger.debug("modifyAggregatiGeometry entered",2 )

        self.modifyAggregatiEmitter.stopCapture()
        try:
            QObject.disconnect(self.modifyAggregatiEmitter, SIGNAL("pointEmitted"), self.modifyAggregatiGeometry)
        except:
            traceback.print_exc()

        action = self.btnModifyAggregatiGeometry.toolTip()
        if not self.checkActionScale( action, self.SCALE_IDENTIFY ) or point == None:
            QObject.connect(self.modifyAggregatiEmitter, SIGNAL("pointEmitted"), self.modifyAggregatiGeometry)
            return self.modifyAggregatiEmitter.startCapture()

        if button != Qt.LeftButton:
            self.btnModifyAggregatiGeometry.setChecked(False)
            return

        layerOrig = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_FAB10K )
        if layerOrig == None:
            self.btnModifyAggregatiGeometry.setChecked(False)
            return

        # if no features found... continue campturing mouse
        featOrig = self.modifyAggregatiEmitter.findAtPoint(layerOrig, point) if layerOrig != None else None
        if featOrig == None:
            QObject.connect(self.modifyAggregatiEmitter, SIGNAL("pointEmitted"), self.modifyAggregatiGeometry)
            return self.modifyAggregatiEmitter.startCapture()
        
        # delesect records
        if featOrig:
            gid = featOrig["gid"]
            layerOrig.deselect(gid)
        
        # stop capturing and reset interface
        self.btnModifyAggregatiGeometry.setChecked(False)
        
        ####################################
        # copy from Aggregati (nominal case)
        ####################################
        aggregatoModificato = self.initNewAggregatiDict()
        aggregatoModificato["identif"] = featOrig["identif"]
        aggregatoModificato["fab_10k_gid"] = featOrig["gid"]
        aggregatoModificato["the_geom"] = featOrig.geometry().exportToWkt()

        #save newAggregato in DB
        from GeoArchiveManager import GeoArchiveManager
        try:
            GeoArchiveManager.instance().archiveFab10kModifications(aggregatoModificato)
            GeoArchiveManager.instance().commit()
            
            aggregatoModificato["local_id"] = GeoArchiveManager.instance().getLastRowId()
            message = self.tr("Inserito record %s con local_id %s" % (self.LAYER_GEOM_FAB10K_MODIF, aggregatoModificato["local_id"]) )
            self.showMessage(message, QgsMessageLog.INFO)
            
        except Exception as ex:
            try:
                traceback.print_exc()
            except:
                pass
            message = self.tr(u"Fallito il salvataggio del record %s con identificativo %s" % (self.LAYER_GEOM_FAB10K_MODIF, featOrig["identif"]) )
            self.showMessage(message + ": "+ex.message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        finally:
            GeoArchiveManager.instance().close() # to avoid locking
        
        ####################################
        # activate a qgis editing session 
        # on the Aggregati layer 
        ####################################
        
        # set current active layer VLID_GEOM_FAB10K_MODIF
        currentActiveLayer = self.iface.activeLayer()
        if self._getLayerId(currentActiveLayer) != GeosismaWindow.VLID_GEOM_FAB10K_MODIF:
            currentActiveLayer = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_FAB10K_MODIF )
            self.iface.setActiveLayer(currentActiveLayer)
        
        # activate editing session
        self.iface.actionToggleEditing().trigger()


    def actionToggleEditingTriggered(self, checked):
        """
        Signal handler activated when editing action is triggered on GEOM_FAB10K_MODIF layer
        it manage when truly editing is terminated after rollback. Rollback qgis managing 
        result in emitting a train of signal and the last one is actionToggleEditing().triggered()
        This callback is tegistered only when GEOM_FAB10K_MODIF has been modifed and before saving changes
        """
        QgsLogger.debug("actionToggleEditingTriggered entered with checked: %s" % str(checked),2 )
        try:
            self.iface.actionToggleEditing().triggered.disconnect(self.actionToggleEditingTriggered)
        except:
            pass
        self.iface.actionToggleEditing().trigger()

        # apply only on GEOM_FAB10K_MODIF layer
        layer = self.iface.activeLayer()
        if not layer or self._getLayerId(layer) != GeosismaWindow.VLID_GEOM_FAB10K_MODIF:
            self.btnModifyAggregatiGeometry.setChecked(False)
            return
        
        # import lib to manage geoarchive
        from GeoArchiveManager import GeoArchiveManager

        # manage modified polygons basing on this cases
        # 1) removed polygons are simply set to noll it's geometry
        # 2) added polygons are managed as in createNewAggregatiGeometry
        # 3) if multy-polygon is modifed but still the same part numbers
        # 4) if multy-polygon has changed it's parts => create new records
        #    assigning identif derived from the original polygon
        
        # 1) removed polygons are simply set to empty geometry QgsGeometry()
        for local_gid in self.deletedFeatureIds:
            # I can modify only deature belonging to my team and not already uploaded
            feat = layer.getFeatures(QgsFeatureRequest(local_gid))
            feat = feat.next()
            if not self.checkCanModifyAggregato(feat):
                continue
            
            # use direct sql instead of data provider due to lock problems
            QgsLogger.debug("Set geometry to NULL in %s with local_id %i" % (GeosismaWindow.TABLE_GEOM_FAB10K_MODIF, local_gid) ,2 )
            feat.setGeometry( QgsGeometry() )
            GeoArchiveManager.instance().updateFab10kModifications(feat) # mod date is updated inside
            
        # 2) added polygons are managed as in createNewAggregatiGeometry
        # try to avoid adding features... should be done using "nuova" button
        
        # 3) if polygon is modifed but still the same part numbers => simply modify of the current polygon
        # this could create a problem in case splitting and removing parts...
        # 4) if multy-polygon has changed it's parts => create new records
        #    assigning identif derived from the original polygon
        for local_gid, geom in self.changedGeometries.items():
            # I can modify only feature belonging to my team and not already uploaded
            feat = layer.getFeatures(QgsFeatureRequest(local_gid))
            feat = feat.next()
            if not self.checkCanModifyAggregato(feat):
                continue
            
            # if equal discard
            if geom.isGeosEqual(feat.geometry()):
                QgsLogger.debug("Unmodified geometry for in %s with local_gid %i" % (GeosismaWindow.TABLE_GEOM_FAB10K_MODIF, local_gid) ,2 )
                continue
            
            parts = geom.asMultiPolygon()
            if parts == None or len(parts) == 0:
                message = self.tr(u"Record %s con local_gid: %s non è multiplygon" % (self.LAYER_GEOM_FAB10K_MODIF, str(feat["local_gid"]) ))
                self.showMessage(message, QgsMessageLog.WARNING)
                QMessageBox.warning(self, GeosismaWindow.MESSAGELOG_CLASS, message)
                continue
            
            # TODO: better check on parts modification because thy can have same part number but different geometry due the fact
            # that combining splitting and deleting operations
            # In this case probably there is only a change in shape of their parts
            originalParts = feat.geometry().asMultiPolygon()
            if (len(parts) == len(originalParts)):
                QgsLogger.debug("Modify geometry in %s with id %i" % (GeosismaWindow.TABLE_GEOM_FAB10K_MODIF, local_gid) ,2 )
                feat.setGeometry( geom )
                GeoArchiveManager.instance().updateFab10kModifications(feat) # mod date is updated inside
                continue
            
            # TODO: better check on parts modification because thy can have same part number but different geometry due the fact
            # that combining splitting and deleting operations
            if (len(parts) != len(originalParts)):
                # create features basing on parts and remove origin record
                for index, part in enumerate(parts):
                    partGeom = QgsGeometry.fromPolygon(part)
                    if not partGeom.convertToMultiType():
                        message = self.tr(u"Problemi convertendo in multiplygon una parte della geometria con local_gid: %i" % str(feat["local_gid"]))
                        self.showMessage(message, QgsMessageLog.WARNING)
                        QMessageBox.warning(self, GeosismaWindow.MESSAGELOG_CLASS, message)
                        continue
                    
                    aggregatoModificato = self.initNewAggregatiDict()
                    newIdentif = "%s%02d" % (feat["identif"], index+1)
                    aggregatoModificato["identif"] =  newIdentif
                    aggregatoModificato["fab_10k_gid"] = feat["fab_10k_gid"]
                    aggregatoModificato["the_geom"] = partGeom.exportToWkt()
                    
                    # save new aggregato
                    GeoArchiveManager.instance().archiveFab10kModifications(aggregatoModificato)
                    
                    aggregatoModificato["local_gid"] = GeoArchiveManager.instance().getLastRowId()
                    message = self.tr("Inserito record %s con local_gid %s e identificativo %s" % (self.LAYER_GEOM_FAB10K_MODIF, aggregatoModificato["local_gid"], aggregatoModificato["identif"]))
                    self.showMessage(message, QgsMessageLog.INFO)
                
                # then remove source aggregato
                GeoArchiveManager.instance().deleteFab10kModification(local_gid)
                #layer.dataProvider().deleteFeatures([local_gid])
        
        # commit all changes in DB
        GeoArchiveManager.instance().commit()
        
        # redraw layer to update their status
        self.iface.mapCanvas().refresh()
        
    def actionToggleEditingChanged(self):
        """
        Signal handler activated when editing action is toggled on GEOM_FAB10K_MODIF layer
        This is useful to rollback modification before to programmatically do other actions
        """
        QgsLogger.debug("actionToggleEditingChanged entered",2 )
        if self.iface.actionToggleEditing().isChecked():
            return

        # apply only on GEOM_FAB10K_MODIF layer
        layer = self.iface.activeLayer()
        if not layer or self._getLayerId(layer) != GeosismaWindow.VLID_GEOM_FAB10K_MODIF:
            self.btnModifyAggregatiGeometry.setChecked(False)
            return
        
        # check if layer has been modified
        if not layer.isModified():
            self.btnModifyAggregatiGeometry.setChecked(False)
            return
        
        # check if want to commit changes
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setText(self.tr("Vuoi salvare i cambiamenti nel layer %s ?" % GeosismaWindow.LAYER_GEOM_FAB10K_MODIF) )
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        msgBox.setButtonText(QMessageBox.Cancel, self.tr("Chiudi senza salvare"))
        msgBox.setButtonText(QMessageBox.Yes, self.tr("Salva"))
        ret = msgBox.exec_()
         
        if ret == QMessageBox.Cancel:
            layer.rollBack()
            layer.commitChanges()
            self.iface.actionToggleEditing().trigger()
            return
        
        # before apply all change copy editing buffer and rollback all modifications
        # on fab_10k_mod so I can control all geometry modification
        # programmatically
        # they are saved as instance variable to be used to another callback activated when
        # editing is really termionated
        self.deletedFeatureIds = layer.editBuffer().deletedFeatureIds()
        self.changedGeometries = layer.editBuffer().changedGeometries()
        
        # register callback to manage modification after effective editing end
        try:
            self.iface.actionToggleEditing().triggered.disconnect(self.actionToggleEditingTriggered)
        except:
            pass
        self.iface.actionToggleEditing().triggered.connect(self.actionToggleEditingTriggered)
        
        # discard all changes
        layer.rollBack()
        layer.commitChanges()


    def checkCanModifyAggregato(self, feat):
        if feat["upload_time"] != None :
            message = self.tr(u"Record %s con local_gid: %s giá caricato sul server. Crea un nuovo aggregato a partire dall'originale" % (self.LAYER_GEOM_FAB10K_MODIF, str(feat["local_gid"]) ))
            self.showMessage(message, QgsMessageLog.WARNING)
            QMessageBox.warning(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            return False

        # get current TeamId
        team_id = None
        for team in self.teams:
            if str(team["name"]) == self.teamComboBox.currentText():
                team_id = team["id"]
                break

        if str(feat["team_id"]) != str(team_id):
            message = self.tr(u"Record %s con local_gid: %s appartiene al team %s, non al team corrente" % (self.LAYER_GEOM_FAB10K_MODIF, str(feat["local_gid"]), str(feat["team_id"])))
            self.showMessage(message, QgsMessageLog.WARNING)
            QMessageBox.warning(self, GeosismaWindow.MESSAGELOG_CLASS, message)
            return False
        
        return True
    
    def registerAggregatiEditingSignals(self):
        """
        Add signals to manage editing of an existing Aggregato modificato
        This assume that original Aggregato has been copied as GEOM_FAB10K_MODIF 
        """
        QgsLogger.debug("registerAggregatiEditingSignals entered",2 )

        layer = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_FAB10K_MODIF )
        if layer == None:
            return

        try:
            self.iface.actionToggleEditing().changed.disconnect(self.actionToggleEditingChanged)
        except:
            pass
        self.iface.actionToggleEditing().changed.connect(self.actionToggleEditingChanged)

    
    def registerAggregatiEditingSignals___APPPP(self):
        """
        add signals to manage editing of an existing Aggregato
        """
        QgsLogger.debug("registerAggregatiEditingSignals___APPPP entered",2 )
        
        self.editingStated = False
        
        def editingStarted():
            print "editingStarted"
        def editingStopped ():
            print "editingStopped "
        def layerModified():
            print "layerModified"
        def beforeCommitChanges ():
            print "beforeCommitChanges "
        def beforeRollBack():
            print "beforeRollBack"
        def featureAdded(fid):
            print "featureAdded"
        def featureDeleted(fid):
            print "featureDeleted"
        def updatedFields():
            print "updatedFields"
        def geometryChanged(fid, geom):
            print "geometryChanged"
        def editCommandStarted():
            print "editCommandStarted"
        def editCommandEnded():
            print "editCommandEnded"
        def editCommandDestroyed():
            print "editCommandDestroyed"
        def actionToggleEditingtriggered(checked):
            print "actionToggleEditingtriggered checked: ", checked
        def actionToggleEditingchanged():
            print "actionToggleEditingchanged"
        def actionToggleEditingtoggled():
            print "actionToggleEditingtoggled..."
#             if self.iface.actionToggleEditing().isChecked():
#                 return
#             print "self.editingStated", self.editingStated
#             if not self.editingStated:
#                 return
#             layers = QgsMapLayerRegistry.instance().mapLayersByName(self.LAYER_GEOM_MODIF)
#             if len(layers) > 0:
#                 layer = layers[0]
#                 print "modified", layer.isModified()
#                 msgBox = QMessageBox()
#                 msgBox.setIcon(QMessageBox.Warning)
#                 msgBox.setText(self.tr("pippo"))
#                 msgBox.setInformativeText(self.tr("Aggiornare il record ?"))
#                 msgBox.setStandardButtons(QMessageBox.YesAll | QMessageBox.Yes | QMessageBox.Cancel)
#                 msgBox.setButtonText(QMessageBox.YesAll, self.tr("Chiudi senza salvare"))
#                 msgBox.setButtonText(QMessageBox.Yes, self.tr("Salva modifiche"))
#                 msgBox.setButtonText(QMessageBox.Cancel, self.tr("Continua"))
#                 ret = msgBox.exec_()
#                 
#                 if ret == QMessageBox.Cancel:
#                     print "cancel"
#                 if ret == QMessageBox.YesAll:
#                     print "yes all"
#                 if ret == QMessageBox.Yes:
#                     print "-----------yes"
#                     editBuffer = copy.copy( layer.editBuffer() )
#                     layer.rollBack()
#                     for key, geom in editBuffer.changedGeometries().iteritems():
#                         print "nmodified id", key
#                         feat = layer.getFeatures(QgsFeatureRequest(key))
#                         feat=feat.next()
#                         oldgeom = feat.geometry()
#                         print "new geom = ", geom.exportToWkt()
#                         print "old geom = ", oldgeom.exportToWkt()

        layer = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_FAB10K_MODIF )
        if layer == None:
            return 
        try:
            self.iface.actionToggleEditing().triggered.disconnect(actionToggleEditingtriggered)
            self.iface.actionToggleEditing().changed.disconnect(actionToggleEditingchanged)
            self.iface.actionToggleEditing().toggled.disconnect(actionToggleEditingtoggled)
        except:
            pass
        self.iface.actionToggleEditing().triggered.connect(actionToggleEditingtriggered)
        self.iface.actionToggleEditing().changed.connect(actionToggleEditingchanged)
        self.iface.actionToggleEditing().toggled.connect(actionToggleEditingtoggled)
        layer.editingStarted.connect(editingStarted)
        layer.editingStopped.connect(editingStopped)
        layer.layerModified.connect(layerModified)
        layer.beforeCommitChanges.connect(beforeCommitChanges)
        layer.beforeRollBack.connect(beforeRollBack)
        layer.featureAdded.connect(featureAdded)
        layer.featureDeleted.connect(featureDeleted)
        layer.updatedFields.connect(updatedFields)
        layer.geometryChanged.connect(geometryChanged)
        layer.editCommandStarted.connect(editCommandStarted)
        layer.editCommandEnded.connect(editCommandEnded)
        layer.editCommandDestroyed.connect(editCommandDestroyed)
        #layer.editingStopped.connect(self.emitSafetyGeometryUpdate)

    
    ###############################################################
    ###### static methods
    ###############################################################
    @classmethod
    def _getLayerId(self, layer):
        if layer == None:
            return None
        if hasattr(layer, 'id'):
            return layer.id()
        return layer.getLayerID() 

    @classmethod
    def _getRendererCrs(self, renderer):
        if renderer == None:
            return None
        if hasattr(renderer, 'destinationCrs'):
            return renderer.destinationCrs()
        return renderer.destinationSrs()

    @classmethod
    def _setRendererCrs(self, renderer, crs):
        if renderer == None:
            return None
        if hasattr(renderer, 'setDestinationCrs'):
            return renderer.setDestinationCrs( crs )
        return renderer.setDestinationSrs( crs )

    @classmethod
    def _addMapLayer(self, layer):
        if layer == None:
            return None
        if hasattr(QgsMapLayerRegistry.instance(), 'addMapLayers'):
            return QgsMapLayerRegistry.instance().addMapLayers( [layer] )
        return QgsMapLayerRegistry.instance().addMapLayer(layer)

    @classmethod
    def _removeMapLayer(self, layer):
        if layer == None:
            return None
        if hasattr(QgsMapLayerRegistry.instance(), 'removeMapLayers'):
            return QgsMapLayerRegistry.instance().removeMapLayers( [layer] )
        return QgsMapLayerRegistry.instance().removeMapLayer(layer)

    @classmethod
    def _logMessage(self, group, msg):
        try:
            QgsMessageLog.logMessage( msg, group )
        except:
            pass

