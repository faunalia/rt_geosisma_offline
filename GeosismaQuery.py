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

from PyQt4.QtCore import QUrl
from qgis.core import *
import os, inspect
import collections
import json
import tempfile
import psycopg2
import psycopg2.extensions
# use unicode!
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

DATABASE_HOST = "localhost"
DATABASE_NAME = "geosisma_geo"
#DATABASE_SCHEMA = "public."
DATABASE_SCHEMA = ""
DATABASE_PORT = "5434"
DATABASE_USER = "postgres"
DATABASE_PWD = "postgres"
# SpatiaLite imports
from pyspatialite import dbapi2 as db
# SpatiaLite DB settings
from GeosismaWindow import GeosismaWindow as gw
# dbsFolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"dbs")))
# DATABASE_OUTNAME = os.path.join(dbsFolder, DATABASE_NAME + ".sqlite")
# print DATABASE_OUTNAME

class GeosismaQuery(object):
    '''
    @summary: QueosismaQuery is a base class for Offline queries. Mainly implements 
    writing query results in JSON formated file
    '''
    uri = QgsDataSourceURI()
    
    def __init__(self, fieldList):
        #self.uri.setConnection(DATABASE_HOST, DATABASE_PORT, DATABASE_NAME, DATABASE_USER, DATABASE_PWD)
        #self.connection = psycopg2.connect( self.uri.connectionInfo().encode('utf-8') )
        self.connection = db.connect(gw.instance().GEODATABASE_OUTNAME)
        self.cursor = self.connection.cursor()
        self.fieldList = fieldList
        
        #create unique filename to store query result
        self.resultfile = tempfile.mktemp(".json", "GeosismaQuery_")
        QgsLogger.debug( "queryresult in: " + self.resultfile)

    def saveJson(self):
        jsonresult = {}
        
        # add metadata to query result
        meta = collections.OrderedDict()
        meta["limit"] = 0,
        meta["offset"] = 0,
        meta["total_count"] = self.cursor.rowcount
        jsonresult["meta"] = meta
        
        # add rows
        objects = []
        for row in self.cursor.fetchall():
            oneobject = collections.OrderedDict()
            for fieldid, field in enumerate(self.fieldList):
                # check if field is an alias... than set alias as it's name
                if (' AS ' in field):
                    field = field.split(' AS ')[1]
                if ('(' in field):
                    field = field.split('(')[1].split(')')[0].split(",")[0] # for ST_AsText(field) or to_char(field, "....") 
                oneobject[field] = row[fieldid]
            objects.append(oneobject)
                
        jsonresult["objects"] = objects
        
        # add rows
        with open(self.resultfile, "w") as fp:
            json.dump(jsonresult, fp)
        return

    #===========================================================================
    # def saveJson(self, filename):
    #     with open(filename, "wb") as fp:
    #         json.dump(self.cursor.fetchall(), fp)
    #     return
    #===========================================================================
    
    def getJsonFile(self):
        return QUrl.fromLocalFile( self.resultfile ).toString()

    def getJson(self):
        with open(self.resultfile) as fp:
            jsonresult = json.load(fp)
        return jsonresult
    
    #===========================================================================
    # def getJson(self, filename):
    #     with open(filename) as fp:
    #         jsonresult = json.load(fp)
    #     return jsonresult
    #===========================================================================
        
class QueryProvincia(GeosismaQuery):
    '''
    @summary: implements query on table Provincia
    '''
    TABLENAME = "istat_province"
    FIELDS = ["id_istat", "toponimo", "idregione", "sigla"]
    
    def __init__(self, jsonquery):
        '''
        Constructor
        @param query: json query parameters
        '''
        GeosismaQuery.__init__(self, self.FIELDS)
        
        # load json query parameters
        queryParams = json.loads(jsonquery)
        
        # subset features basing on query
        sqlquery = u"SELECT "
        for field in self.FIELDS:
            sqlquery += field + ", "
        sqlquery = sqlquery[:-2] # trim last ", "
        sqlquery += " FROM "+DATABASE_SCHEMA+self.TABLENAME+" WHERE LOWER(toponimo) LIKE LOWER('"+queryParams["toponimo__istartswith"]+"%')"
        self.cursor.execute(sqlquery)
        
        self.saveJson()
        self.cursor.close()

class QueryComune(GeosismaQuery):
    '''
    @summary: implements query on table istat_comuni
    '''
    TABLENAME = "istat_comuni"
    EXTTABLE = "istat_province"
    FIELDS = ["istat_comuni.id_istat AS id_istat", "istat_comuni.toponimo AS toponimo", "idprovincia"]
    
    def __init__(self, jsonquery):
        '''
        Constructor
        @param query: json query parameters
        '''
        GeosismaQuery.__init__(self, self.FIELDS)
        
        # load json query parameters
        queryParams = json.loads(jsonquery)
        
        # subset features basing on query
        sqlquery = u"SELECT "
        for field in self.FIELDS:
            sqlquery += field + ", "
        sqlquery = sqlquery[:-2] # trim last ", "
        sqlquery += " FROM "+DATABASE_SCHEMA+self.TABLENAME+" , "+DATABASE_SCHEMA+self.EXTTABLE
        sqlquery += " WHERE LOWER("+self.TABLENAME+".toponimo) LIKE LOWER('"+queryParams["toponimo__istartswith"]+"%')"
        sqlquery += " AND "+self.TABLENAME+".idprovincia = "+self.EXTTABLE+".id_istat"
        if ( 'provincia__sigla' in queryParams ):
            sqlquery += " AND "+self.EXTTABLE+".sigla = '"+queryParams['provincia__sigla']+"'"
        
        self.cursor.execute(sqlquery)
        
        self.saveJson()
        self.cursor.close()

class QueryLocalita(GeosismaQuery):
    '''
    @summary: implements query on table istat_loc
    '''
    TABLENAME = "istat_loc"
    FIELDS = [
        "alloggi",
        "altitudine",
        "centro_cl",
        "cod_com",
        "cod_loc",
        "cod_pro",
        "denom_com",
        "denom_loc",
        "denom_pro",
        "edifici",
        "famiglie",
        "loc2001",
        "maschi",
        "popres",
        "sez2001",
        "sigla_prov",
        "the_geom",
        "tipo_loc"
    ]
    def __init__(self, jsonquery):
        '''
        Constructor
        @param query: json query parameters
        '''
        GeosismaQuery.__init__(self, self.FIELDS)
        
        # load json query parameters
        queryParams = json.loads(jsonquery)
        
        # subset features basing on query
        sqlquery = u"SELECT "
        for field in self.FIELDS:
            if (field == "the_geom"):
                sqlquery += "ST_AsText("+field+"), "
            else:
                sqlquery += field + ", "
        sqlquery = sqlquery[:-2] # trim last ", "
        sqlquery += " FROM "+DATABASE_SCHEMA+self.TABLENAME+" WHERE LOWER(denom_loc) LIKE LOWER('"+queryParams["denom_loc__istartswith"]+"%')"
        if ( 'cod_pro' in queryParams ):
            sqlquery += " AND cod_pro = '"+queryParams["cod_pro"]+"'"
        if ( 'cod_com' in queryParams ):
            sqlquery += " AND cod_com = '"+queryParams["cod_com"]+"'"
        self.cursor.execute(sqlquery)
        
        self.saveJson()
        self.cursor.close()

class QueryCatasto2010_2(GeosismaQuery):
    '''
    @summary: implements query on table catasto_2010
    '''
    TABLENAME = "catasto_2010"
    EXTTABLENAME = "codici_belfiore"
# this is the fileds code for postgis
#     FIELDS = [
#         "allegato",
#         "to_char(ang, 'FM999D99999')",
#         "belfiore",
#         "codbo",
#         "to_char(dim, 'FM9999999999')", # <--- numeric are not serialised by json.dump()
#         "esterconf",
#         "fog_ann",
#         "foglio",
#         "gid",
#         "label",
#         "orig",
#         "to_char(pintx, 'FM9999999999D999')",
#         "to_char(pinty, 'FM9999999999D999')",
#         "to_char(posx, 'FM9999999999D999')",
#         "to_char(posy, 'FM9999999999D999')",
#         "to_char(sup, 'FM999999999999')", # <--- numeric are not serialised by json.dump()
#         "sviluppo",
#         "the_geom",
#         "tipo",
#         "valenza",
#         "zona_cens"
#     ]
    # this fieds are for spatialite
    FIELDS = [
        "allegato",
        "ang",
        "belfiore",
        "codbo",
        "dim",
        "esterconf",
        "fog_ann",
        "foglio",
        "gid",
        "label",
        "orig",
        "pintx",
        "pinty",
        "posx",
        "posy",
        "sup",
        "sviluppo",
        "the_geom",
        "tipo",
        "valenza",
        "zona_cens"
    ]
    def __init__(self, jsonquery):
        '''
        Constructor
        @param query: json query parameters
        '''
        GeosismaQuery.__init__(self, self.FIELDS)
        
        # load json query parameters
        queryParams = json.loads(jsonquery)
        
        # subset features basing on query
        sqlquery = u"SELECT "
        for field in self.FIELDS:
            if (field == "the_geom"):
                sqlquery += "ST_AsText("+field+"), "
            else:
                sqlquery += field + ", "
        sqlquery = sqlquery[:-2] # trim last ", "
        sqlquery += " FROM "+DATABASE_SCHEMA+self.TABLENAME+", "+DATABASE_SCHEMA+self.EXTTABLENAME
        sqlquery += " WHERE codici_belfiore.id = catasto_2010.belfiore"
        sqlquery += "   AND LOWER(codici_belfiore.id_provincia) LIKE LOWER('"+queryParams["belfiore__provincia__id_istat"]+"%')"
        sqlquery += "   AND LOWER(codici_belfiore.id_comune) LIKE LOWER('"+queryParams["belfiore__comune__id_istat"]+"%')"
        sqlquery += "   AND LOWER(catasto_2010.foglio) LIKE LOWER('"+queryParams["foglio"]+"%')"
        sqlquery += "   AND LOWER(catasto_2010.codbo) LIKE LOWER('"+queryParams["codbo"]+"%')"
        self.cursor.execute(sqlquery)

        self.saveJson()
        self.cursor.close()

    