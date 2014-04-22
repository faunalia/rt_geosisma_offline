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
from dlgSelectTeamAndNumber_ui import Ui_Dialog
from ArchiveManager import ArchiveManager

class DlgSelectRequestTeamAndNumber(QDialog, Ui_Dialog):

	def __init__(self, selectedRequestId=None, selectedTeamId=None, parent=None):
		QDialog.__init__(self, parent)
		
		self.selectedRequestNumber = selectedRequestId
		self.selectedTeamId = selectedTeamId
		self.selectedSafetyNumber = None
		
		self.requests = None
		self.team_ids = None
		self.safety_numbers = None
		
		#self.setAttribute(Qt.WA_DeleteOnClose)
		self.setupUi(self)
		self.buttonBox.button(QDialogButtonBox.Close).setText(self.tr("Ignora"))

		self.loadRequests()
		self.loadTeams()
		self.loadAllTeamIds()
		self.loadSafetyNumbers()
		
		# init gui basing on value
		for request in self.requests:
			self.requestNumberComboBox.addItem(str(request["id"]))
		self.requestNumberComboBox.addItem("") # means no requesta ssociated
		
		for team_id in 	self.team_ids:
			for team in self.teams:
				if team["id"] == team_id:
					self.teamIdComboBox.addItem( str(team["name"]), team_id)
		
		values = [int(v) for v in self.safety_numbers]
		self.safetyNumberspinBox.setValue( max(values)+1 if len(values)>0 else 0 )
		
		self.safetyNumberspinBox.valueChanged.connect(self.checkNumber)
		self.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(self.setSelection)
		
		# set default value if available in input
		self.initDefault()
		
	def initDefault(self):
		if self.selectedRequestNumber is not None:
			index = self.requestNumberComboBox.findText( str(self.selectedRequestNumber) )
			if index > -1:
				self.requestNumberComboBox.setCurrentIndex(index)
				
		if self.selectedTeamId is not None:
			index = self.teamIdComboBox.findData( str(self.selectedTeamId) )
			if index > -1:
				self.teamIdComboBox.setCurrentIndex(index)

	def setSelection(self):
		self.selectedRequestNumber = self.requestNumberComboBox.currentText()
		
		index = self.teamIdComboBox.currentIndex()
		self.selectedTeamNameAndId = ( self.teamIdComboBox.itemText(index), self.teamIdComboBox.itemData(index) )
		
		self.selectedSafetyNumber = self.safetyNumberspinBox.value()
	
	def loadRequests(self):
		# return list of tuple (number, id)
		self.requests = ArchiveManager.instance().loadRequests()
		
	def loadTeams(self):
		self.teams = ArchiveManager.instance().loadTeams()

	def loadAllTeamIds(self):
		self.team_ids = ArchiveManager.instance().loadAllTeamIds()
		
	def loadSafetyNumbers(self):
		self.safety_numbers = ArchiveManager.instance().loadSafetyNumbers()
		
	def checkNumber(self, value):
		if value in self.safety_numbers:
			self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
		else:
			self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
		