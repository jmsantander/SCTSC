# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'diagnostic_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_diagnostic_view_dialog(object):
    def setupUi(self, diagnostic_view_dialog):
        diagnostic_view_dialog.setObjectName("diagnostic_view_dialog")
        diagnostic_view_dialog.resize(744, 449)
        self.gridLayout = QtWidgets.QGridLayout(diagnostic_view_dialog)
        self.gridLayout.setObjectName("gridLayout")
        spacerItem = QtWidgets.QSpacerItem(50, 20, QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 5, 3, 1, 1)
        self.send_command_button = QtWidgets.QPushButton(diagnostic_view_dialog)
        self.send_command_button.setAutoDefault(False)
        self.send_command_button.setDefault(False)
        self.send_command_button.setFlat(False)
        self.send_command_button.setObjectName("send_command_button")
        self.gridLayout.addWidget(self.send_command_button, 5, 2, 1, 1)
        self.command_input = QtWidgets.QLineEdit(diagnostic_view_dialog)
        self.command_input.setObjectName("command_input")
        self.gridLayout.addWidget(self.command_input, 5, 1, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(50, 20, QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 5, 0, 1, 1)
        self.diagnostic_tabs = QtWidgets.QTabWidget(diagnostic_view_dialog)
        self.diagnostic_tabs.setObjectName("diagnostic_tabs")
        self.camera_update_cache_panel = QtWidgets.QWidget()
        self.camera_update_cache_panel.setObjectName("camera_update_cache_panel")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.camera_update_cache_panel)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.camera_update_view_textbrowser = QtWidgets.QTextBrowser(self.camera_update_cache_panel)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(2)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.camera_update_view_textbrowser.sizePolicy().hasHeightForWidth())
        self.camera_update_view_textbrowser.setSizePolicy(sizePolicy)
        self.camera_update_view_textbrowser.setObjectName("camera_update_view_textbrowser")
        self.gridLayout_2.addWidget(self.camera_update_view_textbrowser, 0, 1, 1, 1)
        self.camera_cache_table = QtWidgets.QTableWidget(self.camera_update_cache_panel)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(3)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.camera_cache_table.sizePolicy().hasHeightForWidth())
        self.camera_cache_table.setSizePolicy(sizePolicy)
        self.camera_cache_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.camera_cache_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.camera_cache_table.setShowGrid(True)
        self.camera_cache_table.setRowCount(0)
        self.camera_cache_table.setObjectName("camera_cache_table")
        self.camera_cache_table.setColumnCount(0)
        self.gridLayout_2.addWidget(self.camera_cache_table, 0, 0, 1, 1)
        self.diagnostic_tabs.addTab(self.camera_update_cache_panel, "")
        self.conf_panel = QtWidgets.QWidget()
        self.conf_panel.setObjectName("conf_panel")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.conf_panel)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.server_conf_textbrowser = QtWidgets.QTextBrowser(self.conf_panel)
        self.server_conf_textbrowser.setObjectName("server_conf_textbrowser")
        self.gridLayout_3.addWidget(self.server_conf_textbrowser, 1, 0, 1, 1)
        self.local_conf_textbrowser = QtWidgets.QTextBrowser(self.conf_panel)
        self.local_conf_textbrowser.setObjectName("local_conf_textbrowser")
        self.gridLayout_3.addWidget(self.local_conf_textbrowser, 1, 1, 1, 1)
        self.server_conf_label = QtWidgets.QLabel(self.conf_panel)
        self.server_conf_label.setObjectName("server_conf_label")
        self.gridLayout_3.addWidget(self.server_conf_label, 0, 0, 1, 1)
        self.local_conf_label = QtWidgets.QLabel(self.conf_panel)
        self.local_conf_label.setObjectName("local_conf_label")
        self.gridLayout_3.addWidget(self.local_conf_label, 0, 1, 1, 1)
        self.diagnostic_tabs.addTab(self.conf_panel, "")
        self.gridLayout.addWidget(self.diagnostic_tabs, 3, 0, 1, 4)

        self.retranslateUi(diagnostic_view_dialog)
        self.diagnostic_tabs.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(diagnostic_view_dialog)

    def retranslateUi(self, diagnostic_view_dialog):
        _translate = QtCore.QCoreApplication.translate
        diagnostic_view_dialog.setWindowTitle(_translate("diagnostic_view_dialog", "Diagnostic View"))
        self.send_command_button.setText(_translate("diagnostic_view_dialog", "Send Command"))
        self.diagnostic_tabs.setTabText(self.diagnostic_tabs.indexOf(self.camera_update_cache_panel), _translate("diagnostic_view_dialog", "Update Cache"))
        self.server_conf_label.setText(_translate("diagnostic_view_dialog", "Server Config"))
        self.local_conf_label.setText(_translate("diagnostic_view_dialog", "Local Conf"))
        self.diagnostic_tabs.setTabText(self.diagnostic_tabs.indexOf(self.conf_panel), _translate("diagnostic_view_dialog", "Configurations"))

