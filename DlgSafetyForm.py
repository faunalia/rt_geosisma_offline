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
Created on Oct 4, 2013

@author: Luigi Pirelli (luipir@gmail.com)
'''
import os, sys, traceback
from qgis.core import QgsLogger
from qgis.utils import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
# webview import
from PyQt4.QtWebKit import QWebView
from PyQt4.QtWebKit import QWebSettings
# Geosisma imports
from GeosismaQuery import *
# import cache manager
from DlgWmsLayersManager import DlgWmsLayersManager, WmsLayersBridge
from psycopg2.extensions import adapt

class SafetyFormBridge(QObject):
    
    # signals
    saveSafetyDone = pyqtSignal()

    def __init__(self, dialog):
        QObject.__init__(self)
        self.dialog = dialog
        #self.jsonvalue = "{}"

    @pyqtSlot(str, str, result=str)
    def get(self, api, jsonquery):
        QgsLogger.debug( "api: " + api )
        QgsLogger.debug( "jsonquery: " + jsonquery )
        # do query
        if ( api == "provincia/" ):
            return QueryProvincia(jsonquery).getJsonFile()
        elif ( api == "comune/" ):
            return QueryComune(jsonquery).getJsonFile()
        elif ( api == "localita/" ):
            return QueryLocalita(jsonquery).getJsonFile()
        #elif ( api == "catasto2010_1/" ):
            #return QueryCatasto2010_1(jsonquery).getJsonFile()
        elif ( api == "catasto2010_2/" ):
            return QueryCatasto2010_2(jsonquery).getJsonFile()

    @pyqtSlot(str)
    def saveSafety(self, value):
        #self.jsonvalue = value
        # manage directly safety in DlgSafetyForm class instead of emitting signal to avoid 
        # interference with signal emitted dring reload (done when safetyForm webView is saved)
        # the strategy is to save the safety before reloading in a synchronous way
        self.dialog.currentSafety["safety"] = value
        self.saveSafetyDone.emit()

#     def updateScheda(self):
#         self.jsonvalue = '{"s1istatprov":"045","s1istatcom":"004","sdate":"23/10/2013","s1viacorso":"1","s2nfloors":"8","s2nunder":"1","s2floorh":"4","s2floorsfc":"15","s2percuse":"6","s2prop":"0","s3isolpill":"1","s3cover":"2","s3reg1":"0","s3reg2":"1","s7diss":"3","s8riskst":"1","s8risknst":"0","s8riskext":"1","s8riskgeo":"2","s8agibilita":"1","s8accuracy":"3","s8whynot":"4","s8prov1":"0","s8prov2":"0","s8prov3":"0","s8prov4":"0","s8prov5":"0","s8prov6":"0","s8prov7":"1","s8prov8":"1","s8prov9":"1","s8prov10":"1","s8prov11":"1","s8prov12":"1","s9obs":[["arg1","note1"],["arg2","note2"],["arg3","note3"]],"s0com":"com","s0sigla":"sigla","number":3,"s1prov":"MS","s1istatreg":"009","s1com":"Casola in Lunigiana","s1loc":"Casola in Lunigiana","s1istatloc":"10003","s1istatcens":"001","s1catfoglio":"24","s1catpart1":"955","s1via":"del corso","s1civico":"17","s1coorde":12,"s1coordn":44,"s1fuso":33,"s1name":"pasquale","s1coduso":"02","s2cer8":true,"s2uso8":true,"s2uson8":3,"s2occupiers":4,"s3tG3":true,"s3tH3":true,"s3tG2":true,"s3tG1":true,"s4dA6":true,"s4dB5":true,"s4dC4":true,"s4dC5":true,"s4dE5":true,"s4dH6":true,"s4pA5":true,"s4pC4":true,"s4pC2":true,"s4pB2":true,"s4pE2":true,"s5ensA6":true,"s5ensB6":true,"s5ensE5":true,"s5ensC4":true,"s5ensD4":true,"s5ensE4":true,"s5ensD3":true,"s5ensB2":true,"s5ensG1":true,"s5ensA1":true,"s6extA2":true,"s6extB2":true,"s6extB1":true,"s6extC1":true,"s6extE2":true,"s8whyother":"altro1","s8prov11other":"altro2","s8prov12other":"altro3","s8inag":3,"s8famev":4,"s8persev":5,"s3tB4":true,"s3tC5":true}'
#         #self.jsonvalue = json.dumps(self.jsonvalue)
#         self.dialog.webView.page().mainFrame().evaluateJavaScript("updateSafety("+self.jsonvalue+")")


class DlgSafetyForm(QDockWidget):
    
    # signals
    currentSafetyModifed = pyqtSignal(dict)

    def __init__(self, teamName, safetyDict=None, iface=None, parent=None):
        QDockWidget.__init__(self, parent)
        # init internal safety
        self.currentSafety = safetyDict
        self.teamName = teamName
        self.iface = iface
        # init gui
        self.setupUi()
        # set webView setting
        QWebSettings.globalSettings().setAttribute(QWebSettings.JavascriptEnabled, True)
        QWebSettings.globalSettings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
        QWebSettings.globalSettings().setAttribute(QWebSettings.JavascriptCanAccessClipboard, True)
        QWebSettings.globalSettings().setAttribute(QWebSettings.SpatialNavigationEnabled, True)
        QWebSettings.globalSettings().setAttribute(QWebSettings.PrintElementBackgrounds, True)
        QWebSettings.globalSettings().setAttribute(QWebSettings.OfflineStorageDatabaseEnabled, True)
        QWebSettings.globalSettings().setAttribute(QWebSettings.LocalStorageEnabled, True)
        QWebSettings.globalSettings().globalSettings().enablePersistentStorage("/tmp/")
        # relod connection if erased e.g for reloading
        self.webView.page().mainFrame().javaScriptWindowObjectCleared.connect( self.addSafetyFormBridge )
        self.webView.page().mainFrame().loadFinished.connect( self.initSafetyValues )
        # Python to JS bridge definition and signal connection
        self.safetyFormBridge = SafetyFormBridge(self)
        self.safetyFormBridge.saveSafetyDone.connect(self.notifySafetyModified)
    
    def setupUi(self):
        from PyQt4 import QtWebKit
        
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setObjectName( "DlgSafetyForm" )
        self.setWindowTitle( self.tr("Scheda Sopralluogo") )

        child = QWidget()
        gridLayout = QGridLayout(child)
        gridLayout.setMargin(0)
        gridLayout.setContentsMargins(0, 0, 0, 0)
        
        self.webView = QtWebKit.QWebView(child)
        gridLayout.addWidget(self.webView, 0,0,1,1)

        self.setWidget(child)
        self.webView.setUrl(QUrl("about:blank"))
        self.webView.setObjectName("webView")        
        # try to restore position from stored main window state
        if self.iface and not iface.mainWindow().restoreDockWidget(self):
            iface.mainWindow().addDockWidget(Qt.BottomDockWidgetArea, self)
        
    def activate(self):
        self.activateWindow()
        self.raise_()
        QDockWidget.setFocus(self)

    def closeEvent(self, event):
        #self.saveSettingsDlgSafetyForm()
        QWidget.closeEvent(self, event)

    def initSafetyValues(self):
        
        #self.currentSafety = {"safety": "{u'sdate': u'20/03/2013', u's1mapright': u'643334.2044114', u'number': 3, u's1com': u'San Marcello Pistoiese', u's1istatcom': u'019', u's0com': u'', u's1mapleft': u'643291.87110092', u's1viacorso': 1, u's1istatloc': u'10010', u's1name': u'Club Juventus', u's0sigla': u'', u's1mapbottom': u'4879570.583229', u's1aggn': u'019103576', u's1prov': u'PT', u's1istatcens': u'002', u's1civico': u'121', u's1catfoglio': u'55', u's1istatreg': u'009', u's1pos': 3, u's1loc': u'San Marcello Pistoiese', u's1catpart1': u'61', u's1istatprov': u'047', u's1maptop': u'4879597.6765478', u's1via': u'Marconi', u's1edn': u'3'}"}
        #self.currentSafety = '{"s1istatprov":"045","s1istatcom":"004","sdate":"22/10/2013","s1prov":"MS","s1istatreg":"009","s1com":"Casola in Lunigiana","s1loc":"Casola in Lunigiana","s1istatloc":"10003","s1istatcens":"001","s1catfoglio":"24","s1catpart1":"966","s2nfloors":"1","s2floorsfc":"8","s2uso1":true,"s2uson1":12,"s2percuse":"0","s2occupiers":3,"s3tA1":true,"s3tG1":true,"s3tH1":true,"s3reg1":"1","s3as2":true,"s3as1":true,"s3as3":true,"s4dA1":true,"s4dC1":true,"s4dF1":true,"s4pB1":true,"s4pC1":true,"s4pD1":true,"s4pE1":true,"s4pF1":true,"s5ensA1":true,"s5ensB1":true,"s6extA1":true,"s6extB1":true,"s6extC1":true,"s6extD1":true,"s6extE1":true,"s7morfo":"1","s8riskst":"0","s8agibilita":"0","s8accuracy":"0","s8prov1":"0","s8prov7":"0","s8prov8":"0","s8prov2":"0","s8prov3":"0","s8prov4":"0","s8prov5":"0","s8prov6":"0","s8prov9":"0","s8prov10":"0","s8prov11":"0","s8prov12":"0","s8prov11other":"111111111111111","s8prov12other":"12121212121212"}' 
        
        if self.currentSafety is None:
            return
        
        safety = self.prepareSafetyToJs(self.currentSafety["safety"])
        JsCommand = "updateSafety(%s, %s)" % (adapt(self.teamName), safety)
        QgsLogger.debug(self.tr("Init Safety with JS command: %s" % JsCommand))
        
        self.webView.page().mainFrame().evaluateJavaScript(JsCommand)
        #self.jsonvalues = '{"s1istatprov":"045","s1istatcom":"004","sdate":"22/10/2013","s1prov":"MS","s1istatreg":"009","s1com":"Casola in Lunigiana","s1loc":"Casola in Lunigiana","s1istatloc":"10003","s1istatcens":"001","s1catfoglio":"24","s1catpart1":"966","s2nfloors":"1","s2floorsfc":"8","s2uso1":true,"s2uson1":12,"s2percuse":"0","s2occupiers":3,"s3tA1":true,"s3tG1":true,"s3tH1":true,"s3reg1":"1","s3as2":true,"s3as1":true,"s3as3":true,"s4dA1":true,"s4dC1":true,"s4dF1":true,"s4pB1":true,"s4pC1":true,"s4pD1":true,"s4pE1":true,"s4pF1":true,"s5ensA1":true,"s5ensB1":true,"s6extA1":true,"s6extB1":true,"s6extC1":true,"s6extD1":true,"s6extE1":true,"s7morfo":"1","s8riskst":"0","s8agibilita":"0","s8accuracy":"0","s8prov1":"0","s8prov7":"0","s8prov8":"0","s8prov2":"0","s8prov3":"0","s8prov4":"0","s8prov5":"0","s8prov6":"0","s8prov9":"0","s8prov10":"0","s8prov11":"0","s8prov12":"0","s8prov11other":"111111111111111","s8prov12other":"12121212121212"}'

    def prepareSafetyToJs(self, safety=None):
        if safety is None:
            return safety
        # remove "u" of unicode string
        safety = safety.replace("u'", "'")
        # sometimes some records have value "True" that is not recognised by JS => mod to "true"
        safety = safety.replace("True,", " 1,")
        safety = safety.replace("true,", " 1,")
        safety = safety.replace("False,", " 0,")
        safety = safety.replace("false,", " 0,")
        return safety

    def addSafetyFormBridge(self):
        # inject autocompletation class
        self.webView.page().mainFrame().addToJavaScriptWindowObject("safetyFormBridge", self.safetyFormBridge)

    def notifySafetyModified(self):
        self.currentSafetyModifed.emit(self.currentSafety)

    def exec_(self):
        GeosismaWebForm = 'GeosismaSchedaAgibilita.html'
        template_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'template',GeosismaWebForm)
        # create webview clearing cache
        # js-python connector is inside WebView Class
        # load content
        QWebSettings.clearMemoryCaches()
        url = QUrl.fromLocalFile( template_path ) # necessary to be compatible among different way to refer resources (e.g. windows y linux)
        self.webView.load(url)
        self.show()

    def javaScriptConsoleMessage(self, msg, line, source):
        print '%s line %d: %s' % (source, line, msg)
        return True
