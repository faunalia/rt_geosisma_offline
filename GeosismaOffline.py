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
import os, sys, inspect
# realpath() with make your script run, even if you symlink it :)
cmd_folder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile( inspect.currentframe() ))[0]))
if cmd_folder not in sys.path:
     sys.path.insert(0, cmd_folder)

 # use this if you want to include modules from a subforder
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"libraries")))
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)

from qgis.core import *
from qgis.utils import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import QWebView
from PyQt4.QtWebKit import QWebSettings
import json, csv

from GeosismaQuery import *
from GeosismaSchedaVulnerabilitaDlg_ui import Ui_SchedaVulnerabilitaDlg

class GeosismaAutocomplete(QObject):
    
    def __init__(self, webView):
        QObject.__init__(self)
        self.webView = webView
        self.jsonvalue = "{}"

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
    def printValue(self, value):
        self.jsonvalue = value

    def updateScheda(self):
        #self.jsonvalue = '{"s1istatprov":"045","s1istatcom":"004","sdate":"23/10/2013","s1viacorso":"1","s2nfloors":"8","s2nunder":"1","s2floorh":"4","s2floorsfc":"15","s2percuse":"6","s2prop":"0","s3isolpill":"1","s3cover":"2","s3reg1":"0","s3reg2":"1","s7diss":"3","s8riskst":"1","s8risknst":"0","s8riskext":"1","s8riskgeo":"2","s8agibilita":"1","s8accuracy":"3","s8whynot":"4","s8prov1":"0","s8prov2":"0","s8prov3":"0","s8prov4":"0","s8prov5":"0","s8prov6":"0","s8prov7":"1","s8prov8":"1","s8prov9":"1","s8prov10":"1","s8prov11":"1","s8prov12":"1","s9obs":[["arg1","note1"],["arg2","note2"],["arg3","note3"]],"s0com":"com","s0sigla":"sigla","number":3,"s1prov":"MS","s1istatreg":"009","s1com":"Casola in Lunigiana","s1loc":"Casola in Lunigiana","s1istatloc":"10003","s1istatcens":"001","s1catfoglio":"24","s1catpart1":"955","s1via":"del corso","s1civico":"17","s1coorde":12,"s1coordn":44,"s1fuso":33,"s1name":"pasquale","s1coduso":"02","s2cer8":true,"s2uso8":true,"s2uson8":3,"s2occupiers":4,"s3tG3":true,"s3tH3":true,"s3tG2":true,"s3tG1":true,"s4dA6":true,"s4dB5":true,"s4dC4":true,"s4dC5":true,"s4dE5":true,"s4dH6":true,"s4pA5":true,"s4pC4":true,"s4pC2":true,"s4pB2":true,"s4pE2":true,"s5ensA6":true,"s5ensB6":true,"s5ensE5":true,"s5ensC4":true,"s5ensD4":true,"s5ensE4":true,"s5ensD3":true,"s5ensB2":true,"s5ensG1":true,"s5ensA1":true,"s6extA2":true,"s6extB2":true,"s6extB1":true,"s6extC1":true,"s6extE2":true,"s8whyother":"altro1","s8prov11other":"altro2","s8prov12other":"altro3","s8inag":3,"s8famev":4,"s8persev":5,"s3tB4":true,"s3tC5":true}'
        self.webView.page().mainFrame().evaluateJavaScript("updateSafety("+self.jsonvalue+")")


class GeosismaOfflineDlg(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        # init dlg
        self.ui = Ui_SchedaVulnerabilitaDlg()
        self.ui.setupUi(self)
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
        self.ui.webView.page().mainFrame().javaScriptWindowObjectCleared.connect( self.addAutocompleteBridge )
        self.ui.webView.page().mainFrame().loadFinished.connect( self.resetValues )
        self.offline_autocomplete = GeosismaAutocomplete(self.ui.webView)
        #set button event
        self.ui.pushButton.clicked.connect( self.offline_autocomplete.updateScheda )
        
    def resetValues(self):
        print "resetValues"
        self.jsonvalues = '{"s1istatprov":"045","s1istatcom":"004","sdate":"22/10/2013","s1prov":"MS","s1istatreg":"009","s1com":"Casola in Lunigiana","s1loc":"Casola in Lunigiana","s1istatloc":"10003","s1istatcens":"001","s1catfoglio":"24","s1catpart1":"966","s2nfloors":"1","s2floorsfc":"8","s2uso1":true,"s2uson1":12,"s2percuse":"0","s2occupiers":3,"s3tA1":true,"s3tG1":true,"s3tH1":true,"s3reg1":"1","s3as2":true,"s3as1":true,"s3as3":true,"s4dA1":true,"s4dC1":true,"s4dF1":true,"s4pB1":true,"s4pC1":true,"s4pD1":true,"s4pE1":true,"s4pF1":true,"s5ensA1":true,"s5ensB1":true,"s6extA1":true,"s6extB1":true,"s6extC1":true,"s6extD1":true,"s6extE1":true,"s7morfo":"1","s8riskst":"0","s8agibilita":"0","s8accuracy":"0","s8prov1":"0","s8prov7":"0","s8prov8":"0","s8prov2":"0","s8prov3":"0","s8prov4":"0","s8prov5":"0","s8prov6":"0","s8prov9":"0","s8prov10":"0","s8prov11":"0","s8prov12":"0","s8prov11other":"111111111111111","s8prov12other":"12121212121212"}'
        return

    def addAutocompleteBridge(self):
        # inject autocompletation class
        self.ui.webView.page().mainFrame().addToJavaScriptWindowObject("offline_autocomplete", self.offline_autocomplete)

    def javaScriptConsoleMessage(self, msg, line, source):
        print '%s line %d: %s' % (source, line, msg)
        return True


class GeosismaOffline:

    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
    
    def initGui(self):
        self.action = QAction(QIcon(":/plugins/"), "&RT Geosisma Offline", self.iface.mainWindow())
        QObject.connect(self.action, SIGNAL("activated()"), self.show_graph) 
        self.iface.addPluginToMenu("RT Geosisma Offline", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("RT Geosisma Offline",self.action)
        self.iface.removeToolBarIcon(self.action)

    def show_graph(self):
        GeosismaWebForm = 'GeosismaSchedaAgibilita.html'
        template_path = os.path.dirname(os.path.realpath(__file__))+'/template/'+GeosismaWebForm
        # create webview clearing cache
        # js-python connector is insude WebView Class
        self.dlg = GeosismaOfflineDlg()
        
        #self.web = WebPage()
        # load content
        QWebSettings.clearMemoryCaches()
        self.dlg.ui.webView.load(QUrl(template_path))
        self.dlg.show()


if __name__ == "__main__":
    pass
