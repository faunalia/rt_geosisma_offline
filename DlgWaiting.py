# -*- coding: utf-8 -*-

"""
/***************************************************************************
Name                 : Omero RT
Description          : Omero plugin
Date                 : October 21, 2011 
copyright            : (C) 2011 by Giuseppe Sucameli (Faunalia)
email                : sucameli@faunalia.it
 ***************************************************************************/

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

class DlgWaiting(QDialog):

	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		self.singleFinished = False
		self.setupUi()

	def setupUi(self):
		self.setWindowTitle( self.tr( "Attendi..." ) )
		self.setLayout( QVBoxLayout() )
		self.progress = QProgressBar(self)
		self.layout().addWidget( self.progress )
		self.resize(300, self.sizeHint().height())

	def reset(self):
		self.progress.reset()
		self.onProgress(0)

	def setRange(self, minimum, maximum):
		self.progress.setRange(minimum, maximum)
		self.maximum = maximum
		self.reset()
	
	def onProgress(self, n=None):
		if n == None:
			self.progress.setValue( self.progress.value()+1 )
		elif n < 0:
			self.progress.setValue( self.progress.maximum() )
		else:
			self.progress.setValue(n)
		self.update()
		QCoreApplication.processEvents( QEventLoop.ExcludeUserInputEvents )

	def closeEvent(self, event):
		event.ignore() if not self.singleFinished else event.accept()

	def exec_(self):
		QTimer.singleShot(500, self.run)
		return QDialog.exec_(self)

	def run(self):
		self.singleFinished = True
		self.done(self.singleFinished)

