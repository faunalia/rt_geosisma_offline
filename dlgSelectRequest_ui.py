# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dlgSelectRequest.ui'
#
# Created: Wed Nov 20 22:00:17 2013
#      by: PyQt4 UI code generator 4.9.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(1032, 479)
        Dialog.setModal(True)
        self.gridLayout_3 = QtGui.QGridLayout(Dialog)
        self.gridLayout_3.setObjectName(_fromUtf8("gridLayout_3"))
        self.listaSchedeGroup = QtGui.QGroupBox(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.listaSchedeGroup.sizePolicy().hasHeightForWidth())
        self.listaSchedeGroup.setSizePolicy(sizePolicy)
        self.listaSchedeGroup.setAlignment(QtCore.Qt.AlignCenter)
        self.listaSchedeGroup.setObjectName(_fromUtf8("listaSchedeGroup"))
        self.gridLayout = QtGui.QGridLayout(self.listaSchedeGroup)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.requestsTableWidget = QtGui.QTableWidget(self.listaSchedeGroup)
        self.requestsTableWidget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.requestsTableWidget.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.requestsTableWidget.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.requestsTableWidget.setObjectName(_fromUtf8("requestsTableWidget"))
        self.requestsTableWidget.setColumnCount(0)
        self.requestsTableWidget.setRowCount(0)
        self.requestsTableWidget.verticalHeader().setVisible(False)
        self.gridLayout.addWidget(self.requestsTableWidget, 0, 0, 1, 2)
        self.gridLayout_3.addWidget(self.listaSchedeGroup, 0, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.buttonBox.sizePolicy().hasHeightForWidth())
        self.buttonBox.setSizePolicy(sizePolicy)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Close|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout_3.addWidget(self.buttonBox, 2, 0, 1, 1)

        self.retranslateUi(Dialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), Dialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Riepilogo Sopralluoghi", None, QtGui.QApplication.UnicodeUTF8))

