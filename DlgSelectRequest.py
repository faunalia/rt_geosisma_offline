# -*- coding: utf-8 -*-

"""
/***************************************************************************
Name                 : RT Geosisma Offline
Description          : Geosisma Offline Plugin
Date                 : October 21, 2011 
copyright            : (C) 2011 by Giuseppe Sucameli (Faunalia)
modified             : (C) 2013 by Luigi Pirelli (Faunalia)
email                : sucameli@faunalia.it - luigi.pirelli@faunalia.it
 ***************************************************************************/

This code has been extracted from rt omero plugin to be resused in rt geosisma offline plugin

Omero plugin
Works done from Faunalia (http://www.faunalia.it) with funding from Regione 
Toscana - S.I.T.A. (http://www.regione.toscana.it/territorio/cartografia/index.html)

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

from dlgSelectRequest_ui import Ui_Dialog
from ArchiveManager import ArchiveManager

class DlgSelectRequest(QDialog, Ui_Dialog):

	# signals
	loadRequestsDone = pyqtSignal()
	loadTableDone = pyqtSignal()
	
	def __init__(self, currentRequestId=None, parent=None):
		QDialog.__init__(self, parent)
		
		self.currentRequestId = currentRequestId
		self.currentRequest = None
		
		self.setAttribute(Qt.WA_DeleteOnClose)
		self.setupUi(self)
		self.buttonBox.button(QDialogButtonBox.Close).setText(self.tr("Ignora"))

		self.loadRequestsDone.connect(self.updateButtonsState)
		self.loadRequestsDone.connect(self.loadTable)
		self.requestsTableWidget.itemSelectionChanged.connect(self.updateButtonsState)
		self.loadTableDone.connect(self.selectCurrentRequest)
		self.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(self.setCurrentRequest)
		
		self.loadRequests()
		self.loadTable()
		
	def loadRequests(self):
		self.records = ArchiveManager.instance().loadRequests()
		self.loadRequestsDone.emit()
		
	def loadTable(self):
		self.requestsTableWidget.setSortingEnabled(True)
		
		# organize colums
		Hide = True
		Show = False
		columns = OrderedDict()
		columns['id'] = ( self.tr(u'id'), Show )
		columns['event_id'] = ( self.tr(u'Evento'), Show )
		columns['s1prov'] = ( self.tr(u'Provincia'), Show )
		columns['s1com'] = ( self.tr(u'Comune'), Show )
		columns['s1loc'] = ( self.tr(u'Localitá'), Show )
		columns['s1via'] = ( self.tr(u'Via'), Show )
		columns['s1civico'] = ( self.tr(u'Civico'), Show )
		columns['s1catpart1'] = ( self.tr(u'Particella'), Show )
		columns['s1catfoglio'] = ( self.tr(u'Foglio'), Show )
		columns['created'] = ( self.tr(u'Data di creazione'), Show )
		columns['number'] = ( self.tr(u'Squadra'), Show )
		columns['team_id'] = ( self.tr(u'Id della Squadra'), Hide )
		columns['s1name'] = ( self.tr(u'Richiesto da'), Show )

		# set table size
		self.requestsTableWidget.clear()
		self.requestsTableWidget.setRowCount( len(self.records) )
		self.requestsTableWidget.setColumnCount( len(columns) )
		
		# resizing mode of column
		header = self.requestsTableWidget.horizontalHeader()
		header.setResizeMode(QHeaderView.ResizeToContents)
		
		# fill tha table
		self.requestsTableWidget.setHorizontalHeaderLabels( [val[0] for val in columns.values()] )
		for row, record in enumerate(self.records):
			for column, columnKey in enumerate(columns.keys()):
				item = QTableWidgetItem( str(record[columnKey]) )
				
				# add record in the first "id" colum
				if columnKey == "id":
					item.setData(Qt.UserRole, record)
				
				self.requestsTableWidget.setItem(row, column, item )
				
		# column to be shown
		for index, key in enumerate(columns):
			self.requestsTableWidget.setColumnHidden(index, columns[key][1])
		
		self.loadTableDone.emit()
	
	def selectCurrentRequest(self):
		if self.currentRequestId is None:
			return
		
		for row in range( self.requestsTableWidget.rowCount() ):
			item = self.requestsTableWidget.item(row, 0)
			if str(self.currentRequestId) == item.text():
				self.requestsTableWidget.selectRow(row)
				break
	
	def setCurrentRequest(self):
		selectedItems = self.requestsTableWidget.selectedItems()
		if len(selectedItems) == 0:
			self.currentRequestId = None
			self.currentRequest = None
			return
		
		# assume that only one row is selected => get row from an element
		row = selectedItems[0].row()
		
		item = self.requestsTableWidget.item(row, 0) # assume id is the first column
		self.currentRequestId = item.text()
		self.currentRequest = item.data(Qt.UserRole)
	
	def updateButtonsState(self):
		if len(self.records) > 0:
			enabled = True
		
		if len(self.requestsTableWidget.selectedItems()) == 0:
			enabled = False
			
		self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(enabled)
