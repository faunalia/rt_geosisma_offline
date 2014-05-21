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

import os, json, traceback
from qgis.core import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from DlgWaiting import DlgWaiting
from GeosismaWindow import GeosismaWindow as gw

# SpatiaLite imports
from pyspatialite import dbapi2 as db

class ResetDB(DlgWaiting):
    
    # signals
    resetDone = pyqtSignal(bool)
    resetMessage = pyqtSignal(str, int)

    def __init__(self, parent=None):
        DlgWaiting.__init__(self, parent)
        self.cursor = None
        self.stopThread = False

        self.DATABASE_OUTNAME = gw.instance().DATABASE_OUTNAME
        self.DATABASE_SCHEMAFILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'schemas', os.path.splitext(gw.GEOSISMA_DBNAME)[0] + "_schema.sql")
        
    def run(self):
        # init progress bar
        self.reset()
        
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            # create db
            self.createDB()
            # end
            self.resetDone.emit(True)
            
        except Exception as e:
            try:
                traceback.print_exc()
            except:
                pass
            self.resetDone.emit(False)
            self.resetMessage.emit(e.message, QgsMessageLog.CRITICAL)
            raise e
        finally:
            QApplication.restoreOverrideCursor()

    def createDB(self):
        self.setWindowTitle(self.tr("Crea il DB %s" % gw.GEOSISMA_DBNAME) )
        self.setRange( 0, 3 )

        if self.stopThread:
            return
        
        if os.path.exists(self.DATABASE_OUTNAME):
            os.unlink(self.DATABASE_OUTNAME)
        # read 
        geosismadb_schema = ""
        with open(self.DATABASE_SCHEMAFILE, 'r') as fs:
            geosismadb_schema += fs.read()
        self.onProgress()
        # connect spatialite db
        try:
            os.remove(self.DATABASE_OUTNAME)
        except:
            pass
        conn = db.connect(self.DATABASE_OUTNAME)
        # create DB
        try:
            self.resetMessage.emit(self.tr("Inizializza il DB Spatialite; %s" % self.DATABASE_OUTNAME), QgsMessageLog.INFO)
            conn.cursor().executescript(geosismadb_schema)
            self.onProgress()
        except db.Error as e:
            self.resetMessage.emit(e.message, QgsMessageLog.CRITICAL)
            raise e
        conn.close()
        
        # remove archived sopralluoghi
        from GeoArchiveManager import GeoArchiveManager # import here to avoid circular import
        GeoArchiveManager.instance().deleteSopralluoghi()
        GeoArchiveManager.instance().commit()
        self.onProgress()
         
        self.onProgress(-1)
