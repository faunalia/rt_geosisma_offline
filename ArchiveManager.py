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
class ArchiveManager(QObject):
    
    _instance = None
    
    @classmethod
    def instance(cls):
        '''
        Singleton interface
        '''
        if cls._instance == None:
            cls._instance = ArchiveManager()
        return cls._instance
    
    def cleanUp(self):
        self.close()
        ArchiveManager._instance = None

    def __init__(self):
        '''
        Constructor
        '''
        QObject.__init__(self)
        QObject.connect(self, SIGNAL("destroyed()"), self.cleanUp)

        self.conn = None
        self.cursor = None
        self.connect()
    
        # status variable
        self.saveAll = False
    
    def connect(self):
        self.conn = db.connect(gw.instance().DATABASE_OUTNAME)
        self.cursor = self.conn.cursor()
        
    def resetDb(self):
        # connect spatialite db
        if "conn" in locals():
            if (self.isOpen()):
                self.close()
        self.connect()
    
    def checkConnection(self, leaveOpened=False):
        if not self.isOpen():
            self.connect()
        else:
            if not leaveOpened:
                self.close()
                self.connect()
    
    def isOpen(self):
        try:
            self.conn.execute("SELECT 1 FROM missions_request LIMIT 1;")
            return True
        except db.ProgrammingError as dbe:
            return False
    
    def commit(self):
        self.conn.commit()
        # close to be sure to avoid locking
        self.close()
        
    def close(self):
        self.conn.close()
    
    def loadTeams(self):
        '''
        Method to retieve teams in organization_team
        @return list of dict of the record
        '''
        self.checkConnection()

        # create query
        sqlquery = "SELECT * FROM organization_team ORDER BY id;"
        QgsLogger.debug(self.tr("Recupera i Team con la query: %s" % sqlquery), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            columnNames = [descr[0] for descr in self.cursor.description]
            
            requests = []
            for values in self.cursor:
                requests.append( dict(zip(columnNames, values)) )
            
            return requests
            
        except Exception as ex:
            raise(ex)
    
    def archiveTeam(self, teamDict):
        '''
        Method to a archive a team in organization_team table
        @param teamDict: team dictiionary - keys have to be the same key of Db
        '''
        self.checkConnection()
        
        # preare dictionary to be used for DB
        teamOdered = self.prepareTeamDict(teamDict)
        
        # create query
        sqlquery = "INSERT INTO organization_team "
        sqlquery += "( "+",".join(teamOdered.keys()) + " ) VALUES ( "
        for v in teamOdered.values():
            sqlquery += "%s, " % adapt(v)
        sqlquery = sqlquery[0:-2] + " );"
        
        QgsLogger.debug(self.tr("Inserisce team con la query: %s" % sqlquery), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            
        except db.IntegrityError:
            message = self.tr("Team %s gia' presente nel db" % teamOdered["id"])
            gw.instance().showMessage(message, QgsMessageLog.WARNING)
            
            # ask if update record
            if not self.saveAll:
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Warning)
                msgBox.setText(self.tr("Team %s gia' presente!" % teamOdered["id"]))
                msgBox.setInformativeText(self.tr("Aggiornare il record duplicato?"))
                msgBox.setStandardButtons(QMessageBox.YesAll | QMessageBox.Yes | QMessageBox.Cancel)
                msgBox.setButtonText(QMessageBox.YesAll, self.tr("Aggiorna tutti"))
                msgBox.setButtonText(QMessageBox.Yes, self.tr("Aggiorna"))
                msgBox.setButtonText(QMessageBox.Cancel, self.tr("Salta"))
                ret = msgBox.exec_()
                
                if ret == QMessageBox.Cancel:
                    return
                if ret == QMessageBox.YesAll:
                    self.saveAll = True

            self.updateTeam(teamDict)
    
    def updateTeam(self, teamDict):
        '''
        Method to a update a team in organization_team table
        @param teamDict: team dictiionary - keys have to be the same key of Db
        '''
        self.checkConnection()
        
        # preare dictionary to be used for DB
        teamOdered = self.prepareTeamDict(teamDict)

        # create query
        sqlquery = "UPDATE organization_team SET "
        for k,v in teamOdered.items():
            if k == "id":
                continue
            sqlquery += '%s=%s, ' % (k,adapt(v))
        sqlquery = sqlquery[0:-2] + " "
        sqlquery += "WHERE id=%s" % adapt(teamOdered["id"])
        
        QgsLogger.debug(self.tr("Aggiorna team con la query: %s" % sqlquery), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            
        except Exception as ex:
            raise(ex)
    
    def prepareTeamDict(self, team):
        '''
        Method to adapt team dictionary to be the same to db organization_team table
        @param team: team dictionary - keys have to be the same key of Db
        @return: an orderedDict of the key values of the record 
        '''
        event = team["event"]
        path,last = os.path.split(event)
        path,event_id = os.path.split(path)
        
        team["event_id"] = event_id
        
        # create ordered Dict from dict to be sure of the order of the fields
        skipThisKeys = ["event", "requests", "safeties", "users"]
        requestOdered = OrderedDict()
        for k,v in team.items():
            if k in skipThisKeys: # skip keys that are not present in DB schema
                continue
            requestOdered[k]=v

        return requestOdered
    
    def archiveRequest(self, team_id, requestDict):
        '''
        Method to a archive a request in missions_request table
        @param team_id: team_id code e.g index in DB table of the team... as returned by rest api
        @param requestDict: request dictiionary - keys have to be the same key of Db
        '''
        self.checkConnection()
        
        # preare dictionary to be used for DB
        requestOdered = self.prepareRequestDict(team_id, requestDict)
        
        # create query
        sqlquery = "INSERT INTO missions_request "
        sqlquery += "( "+",".join(requestOdered.keys()) + " ) VALUES ( "
        for v in requestOdered.values():
            sqlquery += "%s, " % adapt(v)
        sqlquery = sqlquery[0:-2] + " );"
        
        QgsLogger.debug(self.tr("Inserisce request con la query: %s" % sqlquery), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            
        except db.IntegrityError:
            message = self.tr("Richiesta sopralluogo %s gia' presente nel db" % requestOdered["id"])
            gw.instance().showMessage(message, QgsMessageLog.WARNING)
            
            # ask if update record
            if not self.saveAll:
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Warning)
                msgBox.setText(self.tr("Richiesta sopralluogo %s gia' presente!" % requestOdered["id"]))
                msgBox.setInformativeText(self.tr("Aggiornare il record duplicato?"))
                msgBox.setStandardButtons(QMessageBox.YesAll | QMessageBox.Yes | QMessageBox.Cancel)
                msgBox.setButtonText(QMessageBox.YesAll, self.tr("Aggiorna tutti"))
                msgBox.setButtonText(QMessageBox.Yes, self.tr("Aggiorna"))
                msgBox.setButtonText(QMessageBox.Cancel, self.tr("Salta"))
                ret = msgBox.exec_()
                
                if ret == QMessageBox.Cancel:
                    return
                if ret == QMessageBox.YesAll:
                    self.saveAll = True

            self.updateRequest(team_id, requestDict)
    
    def updateRequest(self, team_id, requestDict):
        '''
        Method to a update a request in missions_request table
        @param team_id: team_id code e.g index in DB table of the team... as returned by rest api
        @param requestDict: request dictiionary - keys have to be the same key of Db
        '''
        self.checkConnection()
        
        # preare dictionary to be used for DB
        requestOdered = self.prepareRequestDict(team_id, requestDict)

        # create query
        sqlquery = "UPDATE missions_request SET "
        for k,v in requestOdered.items():
            if k == "id":
                continue
            sqlquery += '%s=%s, ' % (k,adapt(v))
        sqlquery = sqlquery[0:-2] + " "
        sqlquery += "WHERE id=%s" % adapt(requestOdered["id"])
        
        QgsLogger.debug(self.tr("Aggiorna request con la query: %s" % sqlquery), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            
        except Exception as ex:
            raise(ex)
    
    def loadRequests(self, indexes=None):
        '''
        Method to a load requests from missions_request table based on idexes
        @param indexes: list of index to retrieve. If empty then retrieve all
        @return requests: list of dict of the retrieved records
        '''
        self.checkConnection()
    
        # create query
        sqlquery = "SELECT * FROM missions_request "
        if (indexes != None) and (len(indexes) > 0):
            sqlquery += "WHERE "
            for index in indexes:
                sqlquery += "id='%s' OR " % adapt(index)
            sqlquery = sqlquery[0:-4] + " "
        sqlquery += "ORDER BY id;"
        
        QgsLogger.debug(self.tr("Recupera le request con la query: %s" % sqlquery), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            columnNames = [descr[0] for descr in self.cursor.description]
            
            requests = []
            for values in self.cursor:
                requests.append( dict(zip(columnNames, values)) )
            
            return requests
            
        except Exception as ex:
            raise(ex)

    def prepareRequestDict(self, team_id, request):
        '''
        Method to adapt request dictionary to be the same to db missions_request table
        @param team_id: team_id code e.g index in DB table of the team... as returned by rest api
        @param requestDict: request dictiionary - keys have to be the same key of Db
        @return: an orderedDict of the key values of the record 
        '''
        # add team_id and event_id
        request["team_id"] = team_id
        
        event = request["event"]
        path,last = os.path.split(event)
        path,event_id = os.path.split(path)
        
        request["event_id"] = event_id
        
        # create ordered Dict from dict to be sure of the order of the fields
        skipThisKeys = ["event", "reports"]
        requestOdered = OrderedDict()
        for k,v in request.items():
            if k in skipThisKeys: # skip keys that are not present in DB schema
                continue
            requestOdered[k]=v

        return requestOdered
    
    def loadSafeties(self, indexes=None):
        '''
        Method to a load safeties from missions_safety table based on idexes
        @param indexes: list of index to retrieve. If empty then retrieve all
        @return safeties: list of dict of the retrieved records
        '''
        self.checkConnection()
    
        # create query
        sqlquery = "SELECT *, ST_AsText(the_geom) FROM missions_safety "
        if (indexes != None) and (len(indexes) > 0):
            sqlquery += "WHERE "
            for index in indexes:
                sqlquery += "id='%s' OR " % adapt(index)
            sqlquery = sqlquery[0:-4] + " "
        sqlquery += "ORDER BY id;"
        
        QgsLogger.debug(self.tr("Recupera le safety con la query: %s" % sqlquery), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            columnNames = [descr[0] for descr in self.cursor.description]
            # get index of the_geom and ST_AsText(the_geom)
            geomIndex = columnNames.index("the_geom")
            textGeomIndex = columnNames.index("ST_AsText(the_geom)")
            
            # modify column to erase binary the_geom and substitude with renamed ST_AsText(st_geom)
            columnNames[textGeomIndex] = "the_geom" 
            columnNames.pop(geomIndex)
            
            safeties = []
            for values in self.cursor:
                listValues = [v for v in values]
                listValues.pop(geomIndex)
                safeties.append( dict(zip(columnNames, listValues)) )
            
            return safeties
            
        except Exception as ex:
            raise(ex)

    def getLastRowId(self):
        '''
        Method to return the id of the last inserted record. Could not have meaning in other thatn isert action
        '''
        return self.cursor.lastrowid
    
    def archiveSafety(self, request_id, team_id, safetyDict, overwrite=False):
        '''
        Method to a archive a safety in missions_safety table
        @param request_id: request_id code e.g index in DB table of the missions_request... as returned by rest api
        @param team_id: team_id code e.g index in DB table of the team... as returned by rest api
        @param safetyDict: request dictiionary - keys have to be the same key of Db
        '''
        self.checkConnection()
        
        # preare dictionary to be used for DB
        safetyOdered = self.prepareSafetyDict(request_id, team_id, safetyDict)

        # if "local_id" = None => is a pure insertion of a new record
        # control this in the original not ordered or prepared safety dictionary
        # but modify orderedDict
        if safetyDict["local_id"] == None :
            del safetyOdered["local_id"]
            safetyOdered["id"] = -1
        
        # create query
        sqlquery = "INSERT INTO missions_safety "
        sqlquery += "( "+",".join(safetyOdered.keys()) + " ) VALUES ( "
        for k,v in safetyOdered.items():
            if v == None and k != "the_geom":
                sqlquery += "NULL, "
                continue
            if k == "the_geom":
                if v == None:
                    sqlquery += "NULL, "
                else:
                    sqlquery += "GeomFromText('%s',%d), " % ( v, gw.instance().DEFAULT_SRID )
                continue
            sqlquery += "%s, " % adapt(v)
                
        sqlquery = sqlquery[0:-2] + " );"
        
        QgsLogger.debug(self.tr("Inserisce scheda con la query: %s" % sqlquery), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            
        except db.IntegrityError:
            
            message = self.tr("Scheda %s gia' presente nel db" % safetyOdered["local_id"])
            gw.instance().showMessage(message, QgsMessageLog.WARNING)

            if not overwrite:
                # ask if update record
                if not self.saveAll:
                    msgBox = QMessageBox()
                    msgBox.setIcon(QMessageBox.Warning)
                    msgBox.setText(self.tr("Scheda %s gia' presente!" % safetyOdered["local_id"]))
                    msgBox.setInformativeText(self.tr("Aggiornare il record duplicato?"))
                    msgBox.setStandardButtons(QMessageBox.YesAll | QMessageBox.Yes | QMessageBox.Cancel)
                    msgBox.setButtonText(QMessageBox.YesAll, self.tr("Aggiorna tutti"))
                    msgBox.setButtonText(QMessageBox.Yes, self.tr("Aggiorna"))
                    msgBox.setButtonText(QMessageBox.Cancel, self.tr("Salta"))
                    ret = msgBox.exec_()
                    
                    if ret == QMessageBox.Cancel:
                        return
                    if ret == QMessageBox.YesAll:
                        self.saveAll = True
                
            self.updateCurrentSafety(request_id, team_id, safetyDict)
    
    def updateCurrentSafety(self, request_id, team_id, safetyDict):
        '''
        Method to a update a safety in missions_safety table
        @param request_id: request_id code e.g index in DB table of the missions_request... as returned by rest api
        @param team_id: team_id code e.g index in DB table of the team... as returned by rest api
        @param safetyDict: safety dictiionary - keys have to be the same key of Db
        '''
        self.checkConnection()
        
        # preare dictionary to be used for DB
        safetyOdered = self.prepareSafetyDict(request_id, team_id, safetyDict)

        # create query
        sqlquery = "UPDATE missions_safety SET "
        for k,v in safetyOdered.items():
            if k == "local_id":
                continue
            if v == None and k != "the_geom":
                sqlquery += "%s=NULL, " % k
                continue
            if k == "the_geom":
                if v == None:
                    sqlquery += "%s=NULL, " % k
                else:
                    sqlquery += "%s=GeomFromText('%s',%d), " % ( k, v, gw.instance().DEFAULT_SRID )
                continue
            sqlquery += '%s=%s, ' % (k,adapt(v))
            
        sqlquery = sqlquery[0:-2] + " "
        sqlquery += "WHERE local_id=%s" % adapt(safetyOdered["local_id"])
        
        QgsLogger.debug(self.tr("Aggiorna safety con la query: %s" % sqlquery), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            
        except Exception as ex:
            raise(ex)
    
    def prepareSafetyDict(self, request_id, team_id, safety):
        '''
        Method to adapt safety dictionary to be the same to db missions_safety table
        @param team_id: team_id code e.g index in DB table of the team... as returned by rest api
        @param safetyDict: safety dictiionary - keys have to be the same key of Db
        @return: an orderedDict of the key values of the record 
        '''
        # add team_id and event_id
        safety["team_id"] = team_id
        safety["request_id"] = request_id
        
        # create ordered Dict from dict to be sure of the order of the fields
        skipThisKeys = ["resource_uri"]
        safetyOdered = OrderedDict()
        for k,v in safety.items():
            if k in skipThisKeys: # skip keys that are not present in DB schema
                continue
            safetyOdered[k]=v

        return safetyOdered
    
    def deleteSafety(self, safetyId):
        '''
        Method to delete safety from missions_safety
        @param safetyId
        '''
        self.checkConnection()

        # create query
        sqlquery = "DELETE FROM missions_safety WHERE local_id=%s;" % int(safetyId)
        
        QgsLogger.debug(self.tr("Cancella safety con la query: %s" % sqlquery), 1 )
        self.cursor.execute(sqlquery)

    def createNewAttachment(self, attachmentsDict):
        '''
        Method to a archive a attachments in missions_attachments table
        @param attachmentsDict: attachments dictionary - keys have to be the same key of Db
        '''
        self.checkConnection()
        
        # create query
        sqlquery = "INSERT INTO missions_attachment "
        sqlquery += "( "+",".join(attachmentsDict.keys()) + " ) VALUES ( "
        for v in attachmentsDict.values():
            sqlquery += "%s, " % adapt(v)
        sqlquery = sqlquery[0:-2] + " );"
        
        QgsLogger.debug(self.tr("Inserisce attachment con la query: %s" % sqlquery), 1 )
        self.cursor.execute(sqlquery)
    
    def loadAttachments(self, safetyId=None):
        '''
        Method to a load attachments from missions_attachment table based on idexes
        @param safetyId: select only records related to the safetyId
        @return attachments: list of dict of the retrieved records
        '''
        self.checkConnection()
    
        # create query
        sqlquery = "SELECT * FROM missions_attachment "
        if safetyId != None:
            sqlquery += "WHERE safety_id = '%s' " % safetyId
        sqlquery += "ORDER BY id;"
        
        QgsLogger.debug(self.tr("Recupera gli attachments con la query: %s" % sqlquery), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            columnNames = [descr[0] for descr in self.cursor.description]
            
            attachments = []
            for values in self.cursor:
                attachments.append( dict(zip(columnNames, values)) )
            
            return attachments
            
        except Exception as ex:
            raise(ex)

    def deleteAttachments(self, indexes=None):
        '''
        Method to a delete attachments from missions_attachment table based on idexes
        @param indexes: indexes of attachments to delete
        '''
        self.checkConnection()
    
        # create query
        sqlquery = "DELETE FROM missions_attachment "
        if (indexes != None) and (len(indexes) > 0):
            sqlquery += "WHERE "
            for index in indexes:
                sqlquery += "id=%s OR " % adapt(index)
            sqlquery = sqlquery[0:-4]
        sqlquery += ";"
        
        QgsLogger.debug(self.tr("Rimozione attachments con la query: %s" % sqlquery), 1 )
        self.cursor.execute(sqlquery)


#############################################################################
# utility queries
#############################################################################

    def deleteAttachmentsBySasfety(self, safetyId):
        '''
        Method to a delete attachments from missions_attachment related to a specified safety
        @param indexes: indexes of attachments to delete
        '''
        self.checkConnection()
    
        # create query
        sqlquery = "DELETE FROM missions_attachment "
        sqlquery += "WHERE safety_id='%s';" % str(safetyId)
        
        QgsLogger.debug(self.tr("Rimozione attachments con la query: %s" % sqlquery), 1 )
        self.cursor.execute(sqlquery)

    def loadUnlikedSafeties(self):
        '''
        Method to a load safeties without linked Particella
        @return safeties: list of dict of the retrieved records
        '''
        self.checkConnection()
    
        # create query
        sqlquery = "SELECT *,ST_AsText(the_geom) FROM missions_safety WHERE gid_catasto == '' OR gid_catasto == 'None' OR gid_catasto IS NULL "
        sqlquery += "ORDER BY id;"
        
        QgsLogger.debug(self.tr("Recupera le safety non associate a particelle"), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            columnNames = [descr[0] for descr in self.cursor.description]
            # get index of the_geom and ST_AsText(the_geom)
            geomIndex = columnNames.index("the_geom")
            textGeomIndex = columnNames.index("ST_AsText(the_geom)")
            
            # modify column to erase binary the_geom and substitude with renamed ST_AsText(st_geom)
            columnNames[textGeomIndex] = "the_geom" 
            columnNames.pop(geomIndex)
            
            safeties = []
            for values in self.cursor:
                listValues = [v for v in values]
                listValues.pop(geomIndex)
                safeties.append( dict(zip(columnNames, listValues)) )
            
            return safeties
            
        except Exception as ex:
            raise(ex)

    def loadSafetiesByCatasto(self, gid_catasto):
        '''
        Method to a load safeties from missions_safety related to catasto geometry
        @param gid_catasto: index of catasto geometry
        @return safeties: list of dict of the retrieved records
        '''
        self.checkConnection()
    
        # create query
        str_gid_catasto = "_%d_" % gid_catasto
        sqlquery = "SELECT *,ST_AsText(the_geom) FROM missions_safety WHERE gid_catasto LIKE '%" + str_gid_catasto + "%' "
        sqlquery += "ORDER BY id;"
        
        QgsLogger.debug(self.tr("Recupera le safety legate al poligono catastale con la query: %s" % sqlquery), 1 )
        try:
            
            self.cursor.execute(sqlquery)
            columnNames = [descr[0] for descr in self.cursor.description]
            # get index of the_geom and ST_AsText(the_geom)
            geomIndex = columnNames.index("the_geom")
            textGeomIndex = columnNames.index("ST_AsText(the_geom)")
            
            # modify column to erase binary the_geom and substitude with renamed ST_AsText(st_geom)
            columnNames[textGeomIndex] = "the_geom" 
            columnNames.pop(geomIndex)
            
            safeties = []
            for values in self.cursor:
                listValues = [v for v in values]
                listValues.pop(geomIndex)
                safeties.append( dict(zip(columnNames, listValues)) )
            
            return safeties
            
        except Exception as ex:
            raise(ex)

    def loadSafetyNumbers(self):
        '''
        Method to retieve missions_safety numbers (useful to select the number of a new safety)
        @return list of numbers
        '''
        self.checkConnection()

        # create query
        sqlquery = "SELECT number FROM missions_safety ORDER BY number;"
        
        QgsLogger.debug(self.tr("Recupera la lista dei numeri di scheda con la query: %s" % sqlquery), 1 )
        self.cursor.execute(sqlquery)
        
        result = []
        for number in self.cursor:
            result.append(number[0])
        return result
    
    def loadRequestNumbers(self):
        '''
        Method to retieve missions_request numbers
        @return list of numbers
        '''
        self.checkConnection()

        # create query
        sqlquery = "SELECT number, id FROM missions_request ORDER BY number;"
        
        QgsLogger.debug(self.tr("Recupera la lista dei numeri di sopralluoghi con la query: %s" % sqlquery), 1 )
        self.cursor.execute(sqlquery)
        
        result = []
        for number, request_id in self.cursor:
            result.append( (number, request_id) )
        return result
    
    def loadAllTeamIds(self):
        '''
        Method to retieve all available team_id in missions_request e missions_safety
        @return list of distinct team_id
        '''
        self.checkConnection()

        # create query
        sqlquery = "SELECT DISTINCT team_id FROM (SELECT team_id FROM missions_request UNION SELECT team_id FROM missions_safety);"
        
        QgsLogger.debug(self.tr("Recupera i team_id con la query: %s" % sqlquery), 1 )
        self.cursor.execute(sqlquery)
        
        result = []
        for team_id in self.cursor:
            result.append(team_id[0])
        return result
    
