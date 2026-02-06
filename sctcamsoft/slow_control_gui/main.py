#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue May 15 22:01:54 2018

@author: weidong
"""

# -*- coding: utf-8 -*-  

import argparse
import sys
import yaml
  
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QThread
import numpy as np
from PyQt5.QtWidgets import QMessageBox


from dialog import Ui_MainWindow
from sctcamsoft.lib_gui.camera_comm import CameraComm
from sctcamsoft.slow_control_gui.device_controls.fan import FanControls
from sctcamsoft.slow_control_gui.device_controls.power import PowerControls
from sctcamsoft.slow_control_gui.device_controls.module import ModuleControls
from sctcamsoft.slow_control_gui.device_controls.fee_temp import FeeTempControls
from sctcamsoft.slow_control_gui.device_controls.network import network
from sctcamsoft.slow_control_gui.device_controls.chiller import ChillerControls
from sctcamsoft.slow_control_gui.device_controls.shutter import ShutterControls
from sctcamsoft.slow_control_gui.device_controls.Backplane import BackplaneControls
from sctcamsoft.slow_control_gui.device_controls.target import TargetControls
from sctcamsoft.slow_control_gui.device_controls.alert import alert
from sctcamsoft.slow_control_gui.device_controls.led_control import led_control
import os

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

parser = argparse.ArgumentParser()
parser.add_argument('config_file', help='Path to slow control config file')
parser.add_argument('commands_file', help='Path to slow control commands file')
args = parser.parse_args()

with open(args.config_file, 'r') as config_file:
    config = yaml.load(config_file, Loader=yaml.SafeLoader)
    ui_config = config['user_interface']

with open(args.commands_file, 'r') as commands_file:
    commands = yaml.load(commands_file, Loader=yaml.SafeLoader)

class mywindow(QtWidgets.QMainWindow,Ui_MainWindow):
    """SC primary window.
    
    Extends the UI defined in dialog.py (which is generated from the source in
    dialog.ui, editable with Qt Designer). Hosts camera communication code and
    instances of DeviceControls, each of which encapsulates the behavior of 
    some group of front-end widgets associate with a specific 
    Camera device/subsystem.
    """

    def __init__(self):      
        """Set's up main SC window, begins camera comm, creates DeviceControls."""
        super(mywindow,self).__init__()      
        self.setupUi(self)

        self._comm_thread = QThread()
        self._camera_comm = CameraComm(
            ui_config['host'],
            ui_config['input_port'],
            ui_config['output_port'],
            ui_config['header_length'],
            commands)
        self._camera_comm.moveToThread(self._comm_thread)
        self._comm_thread.start()
        self._camera_comm.init()

        self._camera_comm.on_connec_state_changed.connect(
            lambda newVal: print(f'New connection status: {newVal}'))
        
        # Start a timer, provided to controls objects so they
        # can check for stale values
        self.timer_1000 = QtCore.QTimer()
        self.timer_1000.start(1000)

        self.timer_3000 = QtCore.QTimer()
        self.timer_3000.start(3000)

        # Register buttons not associated with any DeviceControls object
        self.sysInitializeButton.clicked.connect(
            lambda: self._camera_comm.send_command('initialize_system'))
        # self.sysInitializeButton.clicked.connect(
        #     lambda: led_control('on', self._led1))
        self.sysShutdownButton.clicked.connect(
            lambda: self._camera_comm.send_command('shutdown'))
        # self.sysShutdownButton.clicked.connect(
        #     lambda: led_control('off', self._led1))

        self.fan = FanControls(
            self, self._camera_comm.on_update,
            self.timer_1000.timeout, self._camera_comm.send_command)

        self.power = PowerControls(
            self, self._camera_comm.on_update,
            self.timer_1000.timeout, self._camera_comm.send_command)

        self.modules = ModuleControls(
            self, self._camera_comm.on_update,
            self.timer_1000.timeout, self._camera_comm.send_command)

        self.temp1 = FeeTempControls(
            self, self._camera_comm.on_update,
            self.timer_1000.timeout, self._camera_comm.send_command)

        self.network1 = network(
            self, self._camera_comm.on_update,
            self.timer_1000.timeout, self._camera_comm.send_command)

        self.chiller = ChillerControls(
            self, self._camera_comm.on_update,
            self.timer_1000.timeout, self._camera_comm.send_command)

        self.backplane = BackplaneControls(
            self, self._camera_comm.on_update,
            self.timer_1000.timeout, self._camera_comm.send_command)

        self.shutter = ShutterControls(
            self, self._camera_comm.on_update,
            self.timer_1000.timeout, self._camera_comm.send_command)

        self.target = TargetControls(
             self, self._camera_comm.on_update,
             self.timer_1000.timeout, self._camera_comm.send_command)

        self.alert=alert(self,self.timer_3000.timeout,ui_config['host'])
        self.msgBox = QMessageBox()
    def print_message_window(self):
        with  open(os.path.join(__location__, 'slow_control_manual.md')) as f:
             self.msgBox.setWindowTitle("Slow Control GUI Manual")
             self.msgBox.setText(f.read())
             self.msgBox.setStyleSheet("QLabel{min-width:7000 px; font-size: 15px;} QPushButton{ width:250px; font-size: 18px; }")
             self.msgBox.exec()



app = QtWidgets.QApplication(sys.argv)
window = mywindow()
window.show()
window.actionAbout.triggered.connect(lambda:window.print_message_window())
sys.exit(app.exec_())


