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
import os, sys, inspect, traceback
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
import json, csv

from GeosismaWindow import GeosismaWindow


class GeosismaOffline:
    
    instance = None

    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.dlg = None
        GeosismaOffline.instance = self
    
    def initGui(self):
        #self.action = QAction(QIcon(":/plugins/geosismaoffline/icon.png"), "&RT Geosisma Offline", self.iface.mainWindow())
        self.action = QAction(QIcon(":/icons/icon.png"), "RT Geosisma Offline", self.iface.mainWindow())
        self.resetAction = QAction(QIcon(""), "Reset DB", self.iface.mainWindow())
        self.resetAction.triggered.connect(self.resetDb)
        QObject.connect(self.action, SIGNAL("activated()"), self.run) 
        self.iface.addPluginToMenu("&RT Geosisma Offline", self.action)
        self.iface.addPluginToMenu("&RT Geosisma Offline", self.resetAction)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("RT Geosisma Offline",self.action)
        self.iface.removePluginMenu("RT Geosisma Offline",self.resetAction)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        # check precondition
        try:
            import pyspatialite
        except ImportError:
            try:
                traceback.print_exc()
            except:
                pass
            QMessageBox.information(self.iface.mainWindow(), "Attenzione", u"Modulo 'pyspatialite' non trovato. Senza di esso non e' possibile eseguire RT Geosisma Offline.".encode() )
            return
        
        # load gui
        if self.dlg == None:
            self.dlg = GeosismaWindow.instance(self.iface.mainWindow(), self.iface)
            QObject.connect(self.dlg, SIGNAL("destroyed()"), self.onDlgClosed) # sembra non funzionare!!!
        self.dlg.exec_()

    def onDlgClosed(self):
        try:
            if self.dlg:
                self.dlg.deleteLater()
        except:
            pass
        self.dlg = None

    def resetDb(self):
        if self.dlg == None:
            message = "Avviare prima RT Geosisma Offline prima di fare il reset"
            QMessageBox.information(self.iface.mainWindow(), GeosismaWindow.MESSAGELOG_CLASS, message)
            return
        self.dlg.reset()
        
if __name__ == "__main__":
    pass
