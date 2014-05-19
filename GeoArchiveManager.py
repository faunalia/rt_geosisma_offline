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
from datetime import datetime
from qgis.core import QgsLogger, QgsMessageLog, QgsFeature
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
        # connect spatialite db
        if "conn" in locals():
            if (self.isOpen()):
                self.close()
        self.connect()
    
    def checkConnection(self):
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
        self.conn.close()

    def archiveFab10kModifications(self, modificationDict):
        '''
        Method to a archive a fab_10k_modifications in fab_10k_mod table
        @param modificationDict: modification record dictionary - keys have to be the same key of Db
        '''
        self.checkConnection()
        
        # preare dictionary to be used for DB
        modificationOrdered = self.prepareFab10kModificationDict(modificationDict)
        
        # create query
        sqlquery = "INSERT INTO %s " % gw.instance().TABLE_GEOM_FAB10K_MODIF
        sqlquery += "( "+",".join(modificationOrdered.keys()) + " ) VALUES ( "
        for k, v in modificationOrdered.items():
            if v == None:
                sqlquery += "NULL, "
                continue
            if k == "the_geom":
                sqlquery += "GeomFromText('%s',%d), " % ( v, gw.instance().GEODBDEFAULT_SRID )
                continue
            sqlquery += "%s, " % adapt(v)
        sqlquery = sqlquery[0:-2] + " );"
        
        QgsLogger.debug(self.tr("Inserisce record in %s con la query: %s" % (gw.instance().TABLE_GEOM_FAB10K_MODIF, sqlquery) ), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            
        except db.IntegrityError:
            QgsLogger.debug(self.tr("Record modifica aggregati gia' presente nel db"), 1)
        except Exception as ex:
            raise(ex)

    
    def updateFab10kModifications(self, modification):
        '''
        Method to a update a fab_10k_modifications in fab_10k_mod table
        @param modificationDict: modification record dictionary - keys have to be the same key of Db
        '''
        # check input
        if type(modification) == dict:
            modificationDict = modification
        elif type(modification) == QgsFeature:
            modificationDict = {}
            modificationDict["local_gid"] = modification["local_gid"]
            modificationDict["gid"] = modification["gid"]
            modificationDict["identif"] = modification["identif"]
            modificationDict["fab_10k_gid"] = modification["fab_10k_gid"]
            modificationDict["mod_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            modificationDict["team_id"] = modification["team_id"]
            modificationDict["upload_time"] = modification["upload_time"]
            modificationDict["the_geom"] = modification.geometry().exportToWkt()
        
        self.checkConnection()
        
        # preare dictionary to be used for DB
        modificationOrdered = self.prepareFab10kModificationDict(modificationDict)

        # create query
        sqlquery = "UPDATE %s SET " % gw.instance().TABLE_GEOM_FAB10K_MODIF
        for k,v in modificationOrdered.items():
            if v == None:
                sqlquery += '%s=%s, ' % (k,"NULL")
                continue
            if k == "local_gid":
                continue
            if k == "the_geom":
                sqlquery += "%s=GeomFromText('%s',%d), " % ( k, v, gw.instance().GEODBDEFAULT_SRID )
                continue
            sqlquery += '%s=%s, ' % (k,adapt(v))
        sqlquery = sqlquery[0:-2] + " "
        sqlquery += "WHERE local_gid=%s" % adapt(modificationDict["local_gid"])
        
        QgsLogger.debug(self.tr("Aggiorna record in %s con la query: %s" % (gw.instance().TABLE_GEOM_FAB10K_MODIF, sqlquery) ), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            
        except Exception as ex:
            raise(ex)
        
        
    def deleteFab10kModifications(self, local_id):
        '''
        Method to a remove a fab_10k_modifications record in fab_10k_mod table
        @param local_id: id of the record to delete
        '''
        self.checkConnection()
        
        # create query
        sqlquery = "DELETE FROM %s " % gw.instance().TABLE_GEOM_FAB10K_MODIF
        sqlquery += "WHERE local_gid=%s" % adapt(local_id)
        
        QgsLogger.debug(self.tr("Rimuovi il record in %s con la query: %s" % (gw.instance().TABLE_GEOM_FAB10K_MODIF, sqlquery) ), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            
        except Exception as ex:
            raise(ex)
    
    def prepareFab10kModificationDict(self, modificationDict):
        '''
        Method to adapt team dictionary to be the same to db fab_10k_mod table
        @param modificationDict: modification record dictionary - keys have to be the same key of Db
        @return: an orderedDict of the key values of the record 
        '''
        # create ordered Dict from dict to be sure of the order of the fields
        ordered = OrderedDict()
        for k,v in modificationDict.items():
            if k == "local_gid":
                continue
            ordered[k]=v

        return ordered
    
    def getLastRowId(self):
        '''
        Method to return the id of the last inserted record. Could not have meaning other than in insert action
        '''
        return self.cursor.lastrowid

    def loadFab10kmod(self, indexes=None):
        '''
        Method to a load fab10kmod from missions_safety table based on idexes
        @param indexes: list of PK index to retrieve. If empty then retrieve all
        @return fab10kmod: list of dict of the retrieved records
        '''
        self.checkConnection()
    
        # create query
        sqlquery = "SELECT *, ST_AsText(the_geom) FROM %s " % gw.instance().TABLE_GEOM_FAB10K_MODIF
        if (indexes != None) and (len(indexes) > 0):
            sqlquery += "WHERE "
            for index in indexes:
                sqlquery += "local_id='%s' OR " % adapt(index)
            sqlquery = sqlquery[0:-4] + " "
        sqlquery += "ORDER BY gid;"
        
        QgsLogger.debug(self.tr("Recupera i record di %s con la query: %s" % (gw.instance().TABLE_GEOM_FAB10K_MODIF, sqlquery) ), 1 )
        try:
            self.cursor.execute(sqlquery)
            columnNames = [descr[0] for descr in self.cursor.description]
            # get index of the_geom and ST_AsText(the_geom)
            geomIndex = columnNames.index("the_geom")
            textGeomIndex = columnNames.index("ST_AsText(the_geom)")
            
            # modify column to erase binary the_geom and substitude with renamed ST_AsText(st_geom)
            columnNames[textGeomIndex] = "the_geom" 
            columnNames.pop(geomIndex)
            
            fab10kmod = []
            for values in self.cursor:
                listValues = [v for v in values]
                listValues.pop(geomIndex)
                fab10kmod.append( dict(zip(columnNames, listValues)) )
            
            return fab10kmod

        except Exception as ex:
            raise(ex)
        
#############################################################################
# utility queries
#############################################################################

    def deleteArchivedFab10kModifications(self):
        '''
        Method to a remove already archived fab_10k_modifications records in fab_10k_mod table
        '''
        self.checkConnection()
        
        # create query
        sqlquery = "DELETE FROM %s " % gw.instance().TABLE_GEOM_FAB10K_MODIF
        sqlquery += "WHERE gid != -1"
        
        QgsLogger.debug(self.tr("Rimuovi il records in %s con la query: %s" % (gw.instance().TABLE_GEOM_FAB10K_MODIF, sqlquery) ), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            
        except Exception as ex:
            raise(ex)
    
    def locationDataByBelfiore(self, codiceBelfiore):
        '''
        Method to a load safeties from missions_safety related to catasto geometry
        @param codiceBelfiore: Belfiore code to identify safeties
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
