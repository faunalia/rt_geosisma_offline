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

import traceback, os, json, time
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

    # static global vars
    MESSAGELOG_CLASS = "rt_geosisma_offline"
    GEOSISMA_DBNAME = "geosismadb.sqlite"
    GEOSISMA_GEODBNAME = "geosisma_geo.sqlite"
    DEFAULT_SRID = 3003

    _instance = None
    
    # signals
    downloadTeamsDone = pyqtSignal(bool)
    archiveTeamsDone = pyqtSignal(bool)
    downloadRequestsDone = pyqtSignal(bool)
    selectSafetyDone = pyqtSignal()
    selectRequestDone = pyqtSignal()
    updatedCurrentSafety = pyqtSignal()
    initNewCurrentSafetyDone = pyqtSignal()

    # nomi dei layer in TOC
    LAYER_GEOM_ORIG = "Geometrie Originali"
    LAYER_GEOM_MODIF = "Geom. per le schede (invar., suddiv., ex-novo)"
    LAYER_FOTO = "Foto Edifici"

    # stile per i layer delle geometrie
    STYLE_FOLDER = "styles"
    STYLE_GEOM_ORIG = "stile_geometrie_originali.qml"
    STYLE_GEOM_MODIF = "stile_geometrie_modificate.qml"
    STYLE_FOTO = "stile_fotografie.qml"

    SCALE_IDENTIFY = 5000
    SCALE_MODIFY = 2000

    # nomi tabelle contenenti le geometrie
    TABLE_GEOM_ORIG = "catasto_2010".lower()
    TABLE_GEOM_MODIF = "missions_safety".lower()

    # ID dei layer contenenti geometrie e wms
    VLID_GEOM_ORIG = ''
    VLID_GEOM_MODIF = ''
    VLID_FOTO = ''
    RLID_WMS = {}

    # singleton interface
    @classmethod
    def instance(cls, parent=None, iface=None):
        '''
        Singleton interface
        @param parent: passed to init() function
        @param dbName: passed to init() function
        
        '''
        if cls._instance is None:
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
            print "try to delete"
            if self.safetyDlg is not None:
                print "try to delete not none"
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
        self.safetyDlgIsValid = False # flag set up if DockWidget is closed manually
        self.isApriScheda = True
        self.srid = GeosismaWindow.DEFAULT_SRID

        # get bds path
        self.settings = QSettings()
        dbsPath = self.settings.value("/rt_geosisma_offline/pathToDbs", "./offlinedata/dbs/")
        self.DATABASE_OUTNAME = os.path.join(dbsPath, GeosismaWindow.GEOSISMA_DBNAME)
        self.GEODATABASE_OUTNAME = os.path.join(dbsPath, GeosismaWindow.GEOSISMA_GEODBNAME)
        QgsLogger.debug(self.tr("Default dbname: %s" % self.DATABASE_OUTNAME) )
        QgsLogger.debug(self.tr("Default geodbname: %s" % self.GEODATABASE_OUTNAME) )
        
        # get default srid
        self.DEFAULT_SRID = self.settings.value("/rt_geosisma_offline/defaultSrid", self.DEFAULT_SRID, int )
        QgsLogger.debug(self.tr("Default srid: %d" % self.DEFAULT_SRID) )
        
        #geosisma api connection data
        self.user = "Luigi.Pirelli"
        self.pwd = "luigipirelli"
        self.autenthicated = True
        self.maxAuthenticationError = 5
        self.authenticationRetryCounter = 0
        
        # list of dict of requests, tems and safeties
        self.requests = []
        self.currentRequest = None
        self.downloadedTeams = []
        self.downloadedRequests = []
        self.currentSafety = None
        self.teams = None
        
        MapTool.canvas = self.canvas

        self.nuovaPointEmitter = FeatureFinder()
        self.nuovaPointEmitter.registerStatusMsg( u"Click per identificare la geometria da associare alla nuova scheda" )
        QObject.connect(self.nuovaPointEmitter, SIGNAL("pointEmitted"), self.creaNuovaGeometria)

        self.esistentePointEmitter = FeatureFinder()
        QObject.connect(self.esistentePointEmitter, SIGNAL("pointEmitted"), self.identificaSchedaEsistente)

        self.polygonDrawer = PolygonDrawer()
        self.polygonDrawer.registerStatusMsg( u"Click sx per disegnare la nuova gemetria, click dx per chiuderla" )
        QObject.connect(self.polygonDrawer, SIGNAL("geometryEmitted"), self.creaNuovaGeometria)

        self.lineDrawer = LineDrawer()
        self.lineDrawer.registerStatusMsg( u"Click sx per disegnare la linea di taglio, click dx per chiuderla" )
        QObject.connect(self.lineDrawer, SIGNAL("geometryEmitted"), self.spezzaGeometriaEsistente)

        self.fotoPointEmitter = FeatureFinder()
        self.fotoPointEmitter.registerStatusMsg( u"Click su una foto per visualizzarla" )
        QObject.connect(self.fotoPointEmitter, SIGNAL("pointEmitted"), self.identificaFoto)

        self.connect(self.iface.mapCanvas(), SIGNAL( "mapToolSet(QgsMapTool *)" ), self.toolChanged)

        self.connect(self.btnNewSafety, SIGNAL("clicked()"), self.initNewCurrentSafety)
        self.connect(self.btnModifyCurrentSafety, SIGNAL("clicked()"), self.updateSafetyForm)
        self.connect(self.btnDeleteCurrentSafety, SIGNAL("clicked()"), self.deleteCurrentSafety)
        self.connect(self.btnSelectSafety, SIGNAL("clicked()"), self.selectSafety)
        self.connect(self.btnSelectRequest, SIGNAL("clicked()"), self.selectRequest)
        self.connect(self.btnDownloadRequests, SIGNAL("clicked()"), self.downloadTeams)
        self.connect(self.btnReset, SIGNAL("clicked()"), self.reset)
        
        self.connect(self.btnSpezzaGeometriaEsistente, SIGNAL("clicked()"), self.spezzaGeometriaEsistente)
        self.connect(self.btnCreaNuovaGeometria, SIGNAL("clicked()"), self.creaNuovaGeometria)
        self.connect(self.btnRipulisciGeometrie, SIGNAL("clicked()"), self.ripulisciGeometrie)
#         self.connect(self.btnAbout, SIGNAL("clicked()"), self.about)
        
        # custom signal
        self.downloadTeamsDone.connect(self.archiveTeams)
        self.archiveTeamsDone.connect(self.downloadRequests)
        self.downloadRequestsDone.connect( self.archiveRequests )
        #self.initNewCurrentSafetyDone.connect(self.openCurrentSafety)
        #self.initNewCurrentSafetyDone.connect(self.updateSafetyForm)
        self.updatedCurrentSafety.connect(self.updateSafetyForm)
        self.updatedCurrentSafety.connect(self.updateArchivedCurrentSafety)
        #self.selectSafetyDone.connect(self.updateSafetyForm)
        
        # GUI state based on signals
        self.selectSafetyDone.connect(self.manageGuiStatus)
        self.selectRequestDone.connect(self.manageGuiStatus)
        self.updatedCurrentSafety.connect(self.manageGuiStatus)
        
        self.manageGuiStatus()

#         self.connect(self.iface, SIGNAL("projectRead()"), self.reloadLayersFromProject)
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


        group = QGroupBox( "Geometrie", child )
        vLayout.addWidget( group )
        gridLayout = QGridLayout( group )

        text = u"Crea nuova"
        self.btnCreaNuovaGeometria = QPushButton( QIcon(":/icons/crea_geometria.png"), text, group )
        text = u"Crea nuova geometria"
        self.btnCreaNuovaGeometria.setToolTip( text )
        self.btnCreaNuovaGeometria.setCheckable(True)
        gridLayout.addWidget(self.btnCreaNuovaGeometria, 0, 0, 1, 1)

        text = u"Suddividi"
        self.btnSpezzaGeometriaEsistente = QPushButton( QIcon(":/icons/spezza_geometria.png"), text, group )
        text = u"Suddividi una geometria"
        self.btnSpezzaGeometriaEsistente.setToolTip( text )
        self.btnSpezzaGeometriaEsistente.setCheckable(True)
        gridLayout.addWidget(self.btnSpezzaGeometriaEsistente, 0, 1, 1, 1)

        text = u"Ripulisci geometrie non associate"
        self.btnRipulisciGeometrie = QPushButton( QIcon(":/icons/ripulisci.png"), text, group )
        self.btnRipulisciGeometrie.setToolTip( text )
        gridLayout.addWidget(self.btnRipulisciGeometrie, 1, 0, 1, 2)
        
        # init button status basing on data availability and more
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

#         self.currentSafety = {u'created': u'2013-11-20', u'number': 6, u'team_id': 123, u'safety': u'{"s1istatprov":"","s1istatcom":"","sdate":"20/11/2013","number":6,"s2floorsfc":"13","s2nfloors":"6","s2cer6":true,"s2uso6":true,"s2uson6":6,"s2percuse":"5","s3tA6":true,"s4dA6":true,"s4dB6":true,"s5ensA6":true,"s5ensB6":true,"s6extE2":true}', u'request_id': 55, u'date': u'2013-11-20', u'id': 6}
#         self.manageGuiStatus()
#         self.openCurrentSafety()
#         return
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
                message = self.tr("Manca il layer %s, ricaricando il plugin verrano caricati automaticamente" % self.LAYER_GEOM_ORIG)
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
            #style_path = os.path.join( currentPath, GeosismaWindow.STYLE_FOLDER, GeosismaWindow.STYLE_GEOM_ORIG )
            #(errorMsg, result) = vl.loadNamedStyle( style_path )
            #self.iface.legendInterface().refreshLayerSymbology(vl)

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
                message = self.tr("Manca il layer %s, ricaricando il plugin verrano caricati automaticamente" % self.LAYER_GEOM_ORIG)
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
            if vl == None or not vl.isValid() or not vl.setReadOnly(True):
                return False

            # imposta lo stile del layer
            #style_path = os.path.join( currentPath, GeosismaWindow.STYLE_FOLDER, GeosismaWindow.STYLE_GEOM_ORIG )
            #(errorMsg, result) = vl.loadNamedStyle( style_path )
            #self.iface.legendInterface().refreshLayerSymbology(vl)

            GeosismaWindow.VLID_GEOM_MODIF = self._getLayerId(vl)
            self._addMapLayer(vl)
            # set custom property
            vl.setCustomProperty( "loadedByGeosismaRTPlugin", "VLID_GEOM_MODIF" )
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
        
        # now reset db
        from ResetDB import ResetDB
        self.resetDbDlg = ResetDB()
        self.resetDbDlg.resetDone.connect( self.manageEndResetDbDlg )
        self.resetDbDlg.exec_()
        
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
        
        self.selectRequestDone.emit()
    
    def selectCatastoGeometry(self, catastos):
        if len(catastos) is 0:
            return
        
        # get only the first record
        catasto = catastos[0]
        if len(catastos) is not 1:
            message = self.tr("Ottenuti %d records. Verrà considerato solo il primo con gid: %d" % (len(catastos), catasto["gid"]))
            self.showMessage(message, QgsMessageLog.INFO)
            
        # now get feature related to the record
        # probabily bettere use Nathan query lib: http://nathanw.net/2013/07/24/the-little-query-engine-for-pyqgis/
        QgsLogger.debug(self.tr("Dump del record catasto %s" % json.dumps(catasto)) )
        
        layer = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_ORIG )
        exp = QgsExpression("gid = %d" % catasto["gid"])
        fields = layer.pendingFields()
        exp.prepare(fields)
        features = filter(exp.evaluate, layer.getFeatures())
        layer.setSelectedFeatures( [f.id() for f in features] )
        self.iface.mapCanvas().zoomToSelected(layer)

    def selectSafety(self):
        # get id of the current selected safety
        id = None
        if self.currentSafety is not None:
            id = self.currentSafety["id"]
            
        from DlgSelectSafety import DlgSelectSafety
        dlg = DlgSelectSafety(id)
        ret = dlg.exec_()
        # check if result set
        if ret != 0:
            # get selected request
            #safetyId = dlg.currentSafetyId
            self.currentSafety = dlg.currentSafety

        self.updatedCurrentSafety.emit()
        #self.selectSafetyDone.emit()
        
    def openCurrentSafety(self):
        if self.currentSafety is None:
            return
        
        # get teamName
        from ArchiveManager import ArchiveManager # import here to avoid circular import
        if self.teams is None:
            self.teams = ArchiveManager.instance().loadTeams()
        teamName = ""
        for team in self.teams:
            if team["id"] == self.currentSafety["team_id"]:
                teamName = team["name"]
        
        # open Safety Form
        if self.safetyDlg is not None and self.safetyDlgIsValid:
            self.safetyDlg.deleteLater()
        self.safetyDlg = None
        
        from DlgSafetyForm import DlgSafetyForm
        self.safetyDlg = DlgSafetyForm( teamName, self.currentSafety, self.iface, self.iface.mainWindow() )
        self.safetyDlg.currentSafetyModifed.connect(self.updateCurrentSafety)
        self.safetyDlg.destroyed.connect(self.cleanUpSafetyForm)
        self.safetyDlg.exec_()
        
        self.safetyDlgIsValid = True

    def cleanUpSafetyForm(self):
        print "cleanUpSafetyForm"
        self.safetyDlgIsValid = False

    def updateSafetyForm(self):
        # remove dialog is safety is None
        if self.currentSafety is None:
            if self.safetyDlg is not None:
                self.safetyDlg.deleteLater()
            self.safetyDlg = None
            return
        
        if (self.safetyDlg is not None) and \
            self.safetyDlgIsValid and \
            (self.currentSafety["id"] == self.safetyDlg.currentSafety["id"]):
            # do nothing, update is managed directly by the webView
            return
        
        self.openCurrentSafety()
    
    def updateCurrentSafety(self, safetyDict):
        if safetyDict is None:
            return
        self.currentSafety["safety"] = safetyDict["safety"]
        self.updatedCurrentSafety.emit()
    
    def updateArchivedCurrentSafety(self):
        if self.currentSafety is None:
            return
        
        QgsLogger.debug(self.tr("Dump di safety %s" % json.dumps( self.currentSafety )) )
        try:
            from ArchiveManager import ArchiveManager # import here to avoid circular import
            overwrite = True
            ArchiveManager.instance().archiveSafety(self.currentSafety["request_id"], self.currentSafety["team_id"], self.currentSafety, overwrite)
            ArchiveManager.instance().commit()
            # if it's a new record get new id to update currentSafety
            if self.currentSafety["id"] is None:
                lastId = ArchiveManager.instance().getLastRowId()
                if lastId != self.currentSafety["id"]:
                    self.currentSafety["id"] = lastId
                    
                    message = self.tr("Inserita nuova scheda con id %s" % self.currentSafety["id"])
                    self.showMessage(message, QgsMessageLog.INFO)
            
        except Exception:
            traceback.print_exc()
            ArchiveManager.instance().close() # to avoid locking
            traceback.print_exc()
            message = self.tr("Fallito l'update della scheda di sopralluogo")
            self.showMessage(message, QgsMessageLog.CRITICAL)
            QMessageBox.critical(self, GeosismaWindow.MESSAGELOG_CLASS, message)
        finally:
            ArchiveManager.instance().close() # to avoid locking

    def archiveSafety(self):
        if self.currentSafety is None:
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
        
    def initNewCurrentSafety(self):
        
        request_id = None
        team_id = None
        if self.currentSafety is not None:
            request_id = self.currentSafety["request_id"]
            team_id = self.currentSafety["team_id"]
        elif self.currentRequest is not None:
            request_id = self.currentRequest["id"]
        
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
        
        safety = "{number:%s, sdate:'%s'}"% (adapt(safety_number), dateForForm)
        self.currentSafety = {"id":None, "created":dateIso, "request_id":request_number, "safety":safety, "team_id":team_id, "number":safety_number, "date":dateIso}
        
        self.updatedCurrentSafety.emit() # thi will save new safety on db and update gui
        self.initNewCurrentSafetyDone.emit()
    
    def deleteCurrentSafety(self):
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
            ArchiveManager.instance().deleteSafety(self.currentSafety["id"])
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

    def manageGuiStatus(self):
        if self.currentSafety is None:
            self.btnDeleteCurrentSafety.setEnabled(False)
            self.btnModifyCurrentSafety.setEnabled(False)
            self.btnSelectSafety.setText("Seleziona Scheda [%s]" % "--")
        else:
            self.btnDeleteCurrentSafety.setEnabled(True)
            self.btnModifyCurrentSafety.setEnabled(True)
            self.btnSelectSafety.setText("Seleziona Scheda [%s]" % self.currentSafety["number"])
        
        if self.currentRequest is None:
            self.btnSelectRequest.setText("Seleziona Sopralluogo [%s]" % "--")
        else:
            self.btnSelectRequest.setText("Seleziona Sopralluogo [%s]" % self.currentRequest["id"])
        

            
    def ripulisciGeometrie(self, point=None, button=None):
        pass
     
    def gestioneStradario(self, point=None, button=None):
        pass
     
    def reloadLayersFromProject(self, point=None, button=None):
        pass

    def identificaSchedaEsistente(self, point=None, button=None):
        pass
     
    def toolChanged(self, point=None, button=None):
        pass
    
    @classmethod
    def checkActionScale(self, actionName, maxScale):
        if int(self.instance.canvas.scale()) > maxScale:
            QMessageBox.warning( self.instance, "Azione non permessa", u"L'azione \"%s\" è ammessa solo dalla scala 1:%d" % (actionName, maxScale) )
            return False
        return True

    def creaNuovaGeometria(self, point=None, button=None):
        action = self.btnCreaNuovaGeometria.toolTip()

        if not self.checkActionScale( action, self.SCALE_IDENTIFY ) or point == None:
            return self.nuovaPointEmitter.startCapture()

        if button != Qt.LeftButton:
            self.btnSelNuovaScheda.setChecked(False)
            return

        layerModif = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_MODIF )
        if layerModif == None:
            self.btnSelNuovaScheda.setChecked(False)
            return

        feat = self.nuovaPointEmitter.findAtPoint(layerModif, point)
        if feat != None:
            if not self.checkActionSpatialFromFeature( action, feat, True ):
                return self.nuovaPointEmitter.startCapture()

            # controlla se tale geometria ha qualche scheda associata
            codice = feat.attributeMap()[0].toString()
            abbinato = AutomagicallyUpdater.Query( "SELECT ABBINATO_A_SCHEDA FROM GEOMETRIE_RILEVATE_NUOVE_O_MODIFICATE WHERE ID_UV_NEW = ?", [codice] ).getFirstResult() == '1'
            if abbinato:
                # NO, c'è già una scheda associata
                QMessageBox.warning( self, "RT Omero", "La geometria selezionata appartiene ad un edificio gia' esistente" )
                return self.nuovaPointEmitter.startCapture()

            # OK, non esiste alcuna scheda associata a tale geometria
            # associa la UV a tale geometria
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            self.apriScheda(codice)
            QApplication.restoreOverrideCursor()
            self.btnSelNuovaScheda.setChecked(False)
            return
            
        layerOrig = QgsMapLayerRegistry.instance().mapLayer( GeosismaWindow.VLID_GEOM_ORIG )
        if layerOrig == None:
            self.btnSelNuovaScheda.setChecked(False)
            return

        feat = self.nuovaPointEmitter.findAtPoint(layerOrig, point)        
        if feat != None:
            if not self.checkActionSpatialFromFeature( action, feat, False ):
                return

            uvID = self.copiaGeometria(feat)
            if uvID == None:
                return

            self.apriScheda(uvID)
            QApplication.restoreOverrideCursor()
            self.btnSelNuovaScheda.setChecked(False)
            return

        return self.nuovaPointEmitter.startCapture()
    
    def spezzaGeometriaEsistente(self, point=None, button=None):
        pass
    
    def identificaFoto(self, point=None, button=None):
        pass
    
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

