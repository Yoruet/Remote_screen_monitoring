# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'list.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_list(object):
    def setupUi(self, list):
        list.setObjectName("list")
        list.resize(251, 700)
        list.setMinimumSize(QtCore.QSize(251, 700))
        list.setMaximumSize(QtCore.QSize(1500, 1200))
        self.verticalLayout = QtWidgets.QVBoxLayout(list)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(list)
        self.label.setStyleSheet("font: 87 20pt \"Arial Black\";")
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label, 0, QtCore.Qt.AlignHCenter)
        self.listView = QtWidgets.QListView(list)
        self.listView.setObjectName("listView")
        self.verticalLayout.addWidget(self.listView)

        self.retranslateUi(list)
        self.listView.clicked['QModelIndex'].connect(list.client_tree_set) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(list)

    def retranslateUi(self, list):
        _translate = QtCore.QCoreApplication.translate
        list.setWindowTitle(_translate("list", "Form"))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("./assert/icon.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        list.setWindowIcon(icon)
        self.label.setText(_translate("list", "List"))