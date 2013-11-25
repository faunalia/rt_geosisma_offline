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
import os
from qgis.core import QgsLogger, QgsMessageLog
from PyQt4.QtGui import QMessageBox
from PyQt4.QtCore import SIGNAL

from GeosismaWindow import GeosismaWindow as gw
from collections import OrderedDict
# SpatiaLite imports
from pyspatialite import dbapi2 as db
# postgres lib only used to escape sql strings due
# to limitation in spatialite parametric query build
from psycopg2.extensions import adapt

# dericed QObject only to use self.tr translation facility
from PyQt4.QtCore import QObject
class GeoArchiveManager(QObject):
    
    _instance = None
    
    @classmethod
    def instance(cls):
        '''
        Singleton interface
        '''
        if cls._instance is None:
            cls._instance = GeoArchiveManager()
        return cls._instance
    
    def cleanUp(self):
        self.close()
        GeoArchiveManager._instance = None

    def __init__(self):
        '''
        Constructor
        '''
        QObject.__init__(self)
        QObject.connect(self, SIGNAL("destroyed()"), self.cleanUp)

        self.conn = None
        self.cursor = None
        self.connect()
    
    def connect(self):
        self.conn = db.connect(gw.instance().GEODATABASE_OUTNAME)
        self.cursor = self.conn.cursor()
        
    def resetDb(self):
        return
        # connect spatialite db
        if "conn" in locals():
            if (self.isOpen()):
                self.close()
        self.connect()
    
    def checkConnection(self):
        return
        if not self.isOpen():
            self.connect()
    
    def isOpen(self):
        try:
            self.conn.execute("SELECT 1 FROM istat_comuni LIMIT 1;")
            return True
        except db.ProgrammingError:
            return False
    
    def commit(self):
        self.conn.commit()
        # close to be sure to avoid locking
        self.close()
        
    def close(self):
        return
        self.conn.close()
    
#############################################################################
# utility queries
#############################################################################

    def locationDataByBelfiore(self, codiceBelfiore):
        '''
        Method to a load safeties from missions_safety related to catasto geometry
        @param gid_catasto: index of catasto geometry
        @return safeties: list of dict of the retrieved records
        '''
        self.checkConnection()

        sqlquery = '''
            SELECT
                *
            FROM
                codici_belfiore cb,
                istat_regioni ir,
                istat_province ip,
                istat_comuni ic
            WHERE
                cb.id = '%s' AND
                ir.id_istat = cb.id_regione AND
                ip.id_istat = cb.id_provincia AND
                ic.id_istat = cb.id_comune AND
                ic.idprovincia = cb.id_provincia;
            ''' % codiceBelfiore

        QgsLogger.debug(self.tr("Recupera i dati legati al codice belfiore: %s" % sqlquery), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            columnNames = [descr[0] for descr in self.cursor.description]
            safeties = []
            for values in self.cursor:
                listValues = [v for v in values]
                safeties.append( dict(zip(columnNames, listValues)) )
            
            return safeties
            
        except Exception as ex:
            raise(ex)
        
    def localitaByPoint(self, point):
        '''
        Method to a load localita' from istat_loc basing on geometry point
        @param point: where to find features
        @return istat_loc: list of dict of the retrieved records
        '''
        self.checkConnection()

        sqlquery = '''
            SELECT
                *
            FROM
                istat_loc
            WHERE 
                ST_Contains(the_geom, ST_GeometryFromText('POINT(%s %s)', %s));
            ''' % ( point.x(), point.y(), gw.instance().GEODBDEFAULT_SRID )

        QgsLogger.debug(self.tr("Recupera localita' con la query: %s" % sqlquery), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            columnNames = [descr[0] for descr in self.cursor.description]
            safeties = []
            for values in self.cursor:
                listValues = [v for v in values]
                safeties.append( dict(zip(columnNames, listValues)) )
            
            return safeties
            
        except Exception as ex:
            raise(ex)
        
    def fab_10kByPoint(self, point):
        '''
        Method to a load a record from fab_10k basing on geometry point
        @param point: where to find features
        @return fab_10k: list of dict of the retrieved records
        '''
        self.checkConnection()

        sqlquery = '''
            SELECT
                *
            FROM
                fab_10k 
            WHERE 
                ST_Contains(the_geom, ST_GeometryFromText('POINT(%s %s)', %s));
            ''' % ( point.x(), point.y(), gw.instance().GEODBDEFAULT_SRID )

        QgsLogger.debug(self.tr("Recupera fab_10k con la query: %s" % sqlquery), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            columnNames = [descr[0] for descr in self.cursor.description]
            safeties = []
            for values in self.cursor:
                listValues = [v for v in values]
                safeties.append( dict(zip(columnNames, listValues)) )
            
            return safeties
            
        except Exception as ex:
            raise(ex)
