# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'GeosismaSchedaVulnerabilitaDlg.ui'
#
# Created: Mon Nov  4 12:25:19 2013
#      by: PyQt4 UI code generator 4.9.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_SchedaVulnerabilitaDlg(object):
    def setupUi(self, SchedaVulnerabilitaDlg):
        SchedaVulnerabilitaDlg.setObjectName(_fromUtf8("SchedaVulnerabilitaDlg"))
        SchedaVulnerabilitaDlg.resize(1050, 694)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(SchedaVulnerabilitaDlg.sizePolicy().hasHeightForWidth())
        SchedaVulnerabilitaDlg.setSizePolicy(sizePolicy)
        self.verticalLayout_2 = QtGui.QVBoxLayout(SchedaVulnerabilitaDlg)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setSizeConstraint(QtGui.QLayout.SetDefaultConstraint)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.pushButton = QtGui.QPushButton(SchedaVulnerabilitaDlg)
        self.pushButton.setObjectName(_fromUtf8("pushButton"))
        self.verticalLayout.addWidget(self.pushButton)
        self.webView = QtWebKit.QWebView(SchedaVulnerabilitaDlg)
        self.webView.setUrl(QtCore.QUrl(_fromUtf8("about:blank")))
        self.webView.setObjectName(_fromUtf8("webView"))
        self.verticalLayout.addWidget(self.webView)
        self.buttonBox = QtGui.QDialogButtonBox(SchedaVulnerabilitaDlg)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslateUi(SchedaVulnerabilitaDlg)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), SchedaVulnerabilitaDlg.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), SchedaVulnerabilitaDlg.reject)
        QtCore.QMetaObject.connectSlotsByName(SchedaVulnerabilitaDlg)

    def retranslateUi(self, SchedaVulnerabilitaDlg):
        SchedaVulnerabilitaDlg.setWindowTitle(QtGui.QApplication.translate("SchedaVulnerabilitaDlg", "Dialog", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButton.setText(QtGui.QApplication.translate("SchedaVulnerabilitaDlg", "Carica Scheda", None, QtGui.QApplication.UnicodeUTF8))

from PyQt4 import QtWebKit
