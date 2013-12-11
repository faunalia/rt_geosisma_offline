# -*- coding: utf-8 -*-

"""
/***************************************************************************
Name                 : RT Geosisma Offline
Description          : Geosisma Offline Plugin
Date                 : October 21, 2011 
modified             : (C) 2013 by Luigi Pirelli (Faunalia)
email                : sucameli@faunalia.it - luigi.pirelli@faunalia.it
 ***************************************************************************/

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

from datetime import date
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from collections import OrderedDict

from dlgManageAttachments_ui import Ui_Dialog
from ArchiveManager import ArchiveManager

class DlgManageAttachments(QDialog, Ui_Dialog):

	# signals
	loadAttachmentsDone = pyqtSignal()
	loadAttachmentTableDone = pyqtSignal()
	
	def __init__(self, currentSafetyId=None, currentTeamId=None, parent=None):
		QDialog.__init__(self, parent)
		
		self.currentSafetyId = currentSafetyId
		self.currentTeamId = currentTeamId
		
		self.setAttribute(Qt.WA_DeleteOnClose)
		self.setupUi(self)
		self.buttonBox.button(QDialogButtonBox.Close).setText(self.tr("Chiudi"))
		self.buttonBox.button(QDialogButtonBox.Reset).setText(self.tr("Rimuovi"))
		self.buttonBox.button(QDialogButtonBox.Apply).setText(self.tr("Aggiungi"))

		self.loadAttachmentsDone.connect(self.updateButtonsState)
		self.loadAttachmentsDone.connect(self.loadTable)
		self.attachmentsTableWidget.itemSelectionChanged.connect(self.updateButtonsState)
		self.buttonBox.button(QDialogButtonBox.Reset).clicked.connect(self.removeSelectedAttachments)
		self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.addNewAttachment)
		
		self.loadAttachments()
		
	def loadAttachments(self):
		self.records = ArchiveManager.instance().loadAttachments(self.currentSafetyId)
		self.loadAttachmentsDone.emit()
		
	def loadTable(self):
		self.attachmentsTableWidget.setSortingEnabled(True)
		
		# organize colums
		Hide = True
		Show = False
		columns = OrderedDict()
		columns['id'] = ( self.tr(u'id'), Show )
		columns['attached_when'] = ( self.tr(u'Data'), Show )
		columns['attached_by_id'] = ( self.tr(u'Team'), Show )
		columns['safety_id'] = ( self.tr(u'Id locale scheda'), Show )
		columns['attached_file'] = ( self.tr(u'Path'), Show )

		# set table size
		self.attachmentsTableWidget.clear()
		self.attachmentsTableWidget.setRowCount( len(self.records) )
		self.attachmentsTableWidget.setColumnCount( len(columns) )
		
		# resizing mode of column
		header = self.attachmentsTableWidget.horizontalHeader()
		header.setResizeMode(QHeaderView.ResizeToContents)
		
		# fill tha table
		self.attachmentsTableWidget.setHorizontalHeaderLabels( [val[0] for val in columns.values()] )
		for row, record in enumerate(self.records):
			for column, columnKey in enumerate(columns.keys()):
				item = QTableWidgetItem( str(record[columnKey]) )
				
				# add record in the first "id" colum
				if columnKey == "id":
					item.setData(Qt.UserRole, record)
				
				self.attachmentsTableWidget.setItem(row, column, item )
				
		# column to be shown
		for index, key in enumerate(columns):
			self.attachmentsTableWidget.setColumnHidden(index, columns[key][1])
		
		self.loadAttachmentTableDone.emit()
	
	def removeSelectedAttachments(self):
		selectedItems = self.attachmentsTableWidget.selectedItems()
		if len(selectedItems) == 0:
			return
		
		for item in selectedItems:
			row = item.row()
			item = self.attachmentsTableWidget.item(row, 0) # assume id is the first column
			ArchiveManager.instance().deleteAttachments([item.text()])
			ArchiveManager.instance().commit()
		
		# reload list
		self.loadAttachments()
	
	def addNewAttachment(self):
		filename = QFileDialog.getOpenFileName(self, self.tr("Seleziona Allegato"))
		if filename is None:
			return
		
		currentDate = date.today()
		dateIso = currentDate.isoformat()
 
		attachment = OrderedDict()
		attachment['attached_when'] = dateIso
		attachment['attached_by_id'] = self.currentTeamId
		attachment['safety_id'] = self.currentSafetyId
		attachment['attached_file'] = filename
		
		ArchiveManager.instance().createNewAttachment(attachment)
		ArchiveManager.instance().commit()
		
		# reload list
		self.loadAttachments()
	
	def updateButtonsState(self):
		enabled = True
		if len(self.attachmentsTableWidget.selectedItems()) == 0:
			enabled = False
			
		self.buttonBox.button(QDialogButtonBox.Reset).setEnabled(enabled)
