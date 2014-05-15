# -*- coding: utf-8 -*-

"""
/***************************************************************************
Name                 : RT Geosisma Offline
Description          : Geosisma Offline Plugin
Date                 : October 21, 2011 
copyright            : (C) 2013 by Luigi Pirelli (Faunalia)
email                : luigi.pirelli@faunalia.it
 ***************************************************************************/

Works done from Faunalia (http://www.faunalia.it) with funding from Regione 
Toscana - Servizio Sismico (http://www.rete.toscana.it/sett/pta/sismica/)

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from collections import OrderedDict

from dlgUploadSafeties_ui import Ui_Dialog
from ArchiveManager import ArchiveManager

class DlgUploadSafeties(QDialog, Ui_Dialog):

	# signals
	loadTeamsDone = pyqtSignal()
	loadSafetiesDone = pyqtSignal()
	loadTableDone = pyqtSignal()
	
	def __init__(self, currentSafetyId=None, gid=None, parent=None):
		QDialog.__init__(self, parent)
		
		self.currentSafetyId = currentSafetyId
		self.currentGid = gid
		self.currentSafety = {}
		self.buttonSelected = None
		
		self.setAttribute(Qt.WA_DeleteOnClose)
		self.setupUi(self)
		self.buttonBox.button(QDialogButtonBox.Close).setText(self.tr("Ignora"))
		self.buttonBox.button(QDialogButtonBox.Save).setText(self.tr("Upload"))
		self.buttonBox.button(QDialogButtonBox.SaveAll).setText(self.tr("Upload tutte"))

		self.loadTeamsDone.connect(self.updateButtonsState)
		self.loadTeamsDone.connect(self.loadTable)
		self.safetyTableWidget.itemSelectionChanged.connect(self.updateButtonsState)
		self.loadTableDone.connect(self.selectCurrentSafety)
		self.buttonBox.button(QDialogButtonBox.Save).clicked.connect(self.setCurrentSafetyId)
		self.buttonBox.clicked.connect(self.setCurrentClicked)
		
		self.loadSafeties()

		# check if safeties are available
		if len(self.records) == 0:
			return

		self.loadTeams()
		self.loadTable()
		self.safetyTableWidget.sortByColumn(0)
		
	def loadSafeties(self):
		if self.currentGid:
			self.records = ArchiveManager.instance().loadSafetiesByCatasto(self.currentGid)
		else:
			self.records = ArchiveManager.instance().loadSafeties()
		self.loadSafetiesDone.emit()
		
	def loadTeams(self):
		self.teams = ArchiveManager.instance().loadTeams()
		self.loadTeamsDone.emit()
		
	def loadTable(self):
		self.safetyTableWidget.setSortingEnabled(True)
		
		# organize colums
		Hide = True
		Show = False
		columns = OrderedDict()
		columns['local_id'] = ( self.tr(u'Id locale'), Hide )
		columns['number'] = ( self.tr(u'Numero'), Show )
		columns['id'] = ( self.tr(u'Id remoto'), Show )
		columns['request_id'] = ( self.tr(u'Richiesta Sopralluogo'), Show )
		columns['name'] = ( self.tr(u'Team'), Show )
		columns['created'] = ( self.tr(u'Creata'), Show )
		columns['date'] = ( self.tr(u'Aggiornata il'), Show )
		columns['safety'] = ( self.tr(u'Scheda'), Hide )
		columns['gid_catasto'] = ( self.tr(u'Id catasto'), Show )
		columns['the_geom'] = ( self.tr(u'the_geom'), Hide )
		
		# set table size
		self.safetyTableWidget.clear()
		self.safetyTableWidget.setRowCount( len(self.records) )
		self.safetyTableWidget.setColumnCount( len(columns) )
		
		# resizing mode of column
		header = self.safetyTableWidget.horizontalHeader()
		header.setResizeMode(QHeaderView.ResizeToContents)
		
		# fill the table
		self.safetyTableWidget.setHorizontalHeaderLabels( [val[0] for val in columns.values()] )
		for row, record in enumerate(self.records):
			for column, columnKey in enumerate(columns.keys()):
				if columnKey != "name":
					item = QTableWidgetItem()
					try:
						value = int(record[columnKey])
					except:
						value = str(record[columnKey])
					item.setData(Qt.DisplayRole, value)
				else:
					# look for name in teams
					for team in self.teams:
						if team["id"] == record["team_id"]:
							item = QTableWidgetItem( str(team["name"]) )
				
				# add record in the first "local_id" colum
				if column == 0:
					item.setData(Qt.UserRole, record)
				
				self.safetyTableWidget.setItem(row, column, item )
			
				
		# column to be shown
		for index, key in enumerate(columns):
			self.safetyTableWidget.setColumnHidden(index, columns[key][1])
		
		self.loadTableDone.emit()
	
	def selectCurrentSafety(self):
		if self.currentSafetyId is None:
			return
		
		for row in range( self.safetyTableWidget.rowCount() ):
			item = self.safetyTableWidget.item(row, 0)
			if str(self.currentSafetyId) == item.text():
				self.safetyTableWidget.selectRow(row)
				break
	
	def setCurrentSafetyId(self):
		selectedItems = self.safetyTableWidget.selectedItems()
		if len(selectedItems) == 0:
			self.currentSafetyId = None
			self.currentSafety = None
			return
		
		# assume that only one row is selected => get row from an element
		row = selectedItems[0].row()
		
		item = self.safetyTableWidget.item(row, 0)  # assume id is the first column
		self.currentSafetyId = item.text()
		self.currentSafety = item.data(Qt.UserRole)
	
	def updateButtonsState(self):
		if len(self.records) > 0:
			enabled = True
		
		if len(self.safetyTableWidget.selectedItems()) == 0:
			enabled = False
		
		self.buttonBox.button(QDialogButtonBox.Save).setEnabled(enabled)
			
	def setCurrentClicked(self, button):
		if (button is self.buttonBox.button(QDialogButtonBox.Save)):
			self.buttonSelected = "Save"
		if (button is self.buttonBox.button(QDialogButtonBox.SaveAll)):
			self.buttonSelected = "SaveAll"
		if (button is self.buttonBox.button(QDialogButtonBox.Cancel)):
			self.buttonSelected = "Cancel"
