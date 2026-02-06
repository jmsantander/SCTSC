# -*- coding: utf-8 -*-

import argparse
import sys
import yaml
import logging

import csv, random

from sctcamsoft.run_control_gui.main_window import Ui_PsctRunControlMainWindow
from sctcamsoft.run_control_gui.camera_indicator import ModuleConfigurationDialog, ModuleConf
from sctcamsoft.run_control_gui.diagnostic import DiagnosticView
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, QThread, QTimer, Qt
from sctcamsoft.lib_gui.led import LED
from sctcamsoft.run_control_gui.log import create_logbox_log_adapter, LogControls

from sctcamsoft.lib_gui.camera_comm import CameraComm
from sctcamsoft.lib_gui.camera_handler import CameraHandler
from sctcamsoft.run_control_gui.configuration import ConfigManager, ConfigControls, ApplyStatus
from sctcamsoft.run_control_gui.run_monitoring import RunManager, RunControls

from datetime import datetime, timezone, timedelta

# Configure logging to the terminal that spawned the GUI
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)7s - %(threadName)s - %(message)s')

parser = argparse.ArgumentParser()
parser.add_argument('config_file', help='Path to slow control config file', )
parser.add_argument('commands_file', help='Path to slow control commands file')
args = parser.parse_args()

with open(args.config_file, 'r') as config_file:
    config = yaml.load(config_file, Loader=yaml.SafeLoader)
    ui_config = config['user_interface']

with open(args.commands_file, 'r') as commands_file:
    commands = yaml.load(commands_file, Loader=yaml.SafeLoader)


class mywindow(QtWidgets.QMainWindow, Ui_PsctRunControlMainWindow):
    """RC primary window.

    Extends the UI defined in main_window.py (generated from main_window.ui).
    Hosts camera communication code, ConfigControls/ConfigManager,
    and RunControls/RunManager.

    Run Control is split into two major components: run configuration (handled
    by ConfigManager and drawn by ConfigControls), and run monitoring (handled
    by RunManager and drawn by RunControls). The first is responsible for 
    pre-run settings updates that must be performed before a run and are a part
    of the run's definition. The latter handles start/stopping of runs and 
    handles status updates throughout the run itself.
    """

    def __init__(self):
        """Setup main RC window, begin comm, instantiate top-level components."""

        super(mywindow, self).__init__()
        self.setupUi(self)

        # Configure the log handler and corresponding widgets
        self._logbox_handler = create_logbox_log_adapter()
        self._log_controls = LogControls(self)
        self._logbox_handler.new_record.connect(
            self._log_controls.append_to_textbrowser)
        logging.getLogger().addHandler(self._logbox_handler)

        # Configure and start the camera communication code,
        # then move it to it's own thread.
        self._comm_thread = QThread()
        self._camera_comm = CameraComm(
            ui_config['host'],
            ui_config['input_port'],
            ui_config['output_port'],
            ui_config['header_length'],
            commands)
        # Change the thread affinity
        self._camera_comm.moveToThread(self._comm_thread)
        self._comm_thread.start()  # Start the QThread
        self._camera_comm.init()  # Configure the communication thread

        self._camera_comm.on_connec_state_changed.connect(
            self.on_connect_state_changed)

        # Create a CameraHandler that monitors the server for `target`
        # and `backplane` updates and reacts to all alerts. Other classes 
        # will use this handler to interact with the server.
        self._camera = CameraHandler(
            ['target', 'backplane'], [], 
            self._camera_comm.on_update,
            self._camera_comm.send_command)

        # Set up the configuration manager and GUI elements
        self._config_controls = ConfigControls(self)
        self._config_manager = ConfigManager(self._camera, self._config_controls)

        # Set up the run manager and GUI elements
        self._run_controls = RunControls(self)
        self._run_manager = RunManager(self._camera, self._run_controls)

        self.action_mod_config.triggered.connect(self.open_module_window)

        self.action_diagnostic_view.triggered.connect(self.open_diagnostic_view)

    def open_module_window(self):

        # Grab the modules in the current configuration
        local_conf = self._config_manager.local_conf.config
        included_mods = local_conf.get('module_ids', [])

        # Grab the current module state
        mod_states = self._camera.get_cache().get_val('target', 'state')
        if mod_states:
            states_dict = {int(val.identifier): val.value for val in mod_states}
        else:
            states_dict = {}

        # Read FPM data and create module data
        fpm_config_data = config['target']['fpm_configuration']
        module_confs = []
        with open(fpm_config_data) as csv_file:
            reader = csv.DictReader(csv_file)
            for fpm_config in reader:
                mod_id = int(fpm_config['module_id'])

                mod_data = ModuleConf(
                    mod_id,
                    int(fpm_config['fpm_sector']),
                    int(fpm_config['fpm_position']),
                    mod_id in included_mods,
                    states_dict.get(mod_id, None),
                    []
                )
                module_confs.append(mod_data)

        self.module_window = ModuleConfigurationDialog(module_confs)
        self.module_window.module_conf_changed.connect(self.on_module_conf_changed)
        self.module_window.resize(600, 380)
        self.module_window.exec_()

    def open_diagnostic_view(self):
        self.diagnostic_window = DiagnosticView(
            self._camera,
            self._config_manager.server_conf,
            self._config_manager.local_conf)
        self.diagnostic_window.resize(800, 400)
        self.diagnostic_window.show()

    # def report_progress(self):
    #     try:
    #         if (self._mock_time_elapsed > timedelta(seconds=30)):
    #             self._mock_run_num = self._mock_run_num + 1
    #             self._mock_time_elapsed = timedelta(0)
    #         else:
    #             self._mock_time_elapsed = self._mock_time_elapsed + timedelta(seconds=1)
    #     except AttributeError:
    #         self._mock_run_num = 3
    #         self._mock_time_elapsed = timedelta(0)

    #     self._run_manager.run_id_updated.emit(self._mock_run_num)
    #     self._run_manager.time_elapsed.emit(self._mock_time_elapsed, timedelta(seconds=30))

    def on_connect_state_changed(self, new_val):
        logging.info('Connection state changed, value is now [%r]', new_val)
        self.connected_led.value = new_val

    def on_module_conf_changed(self, module_conf):
        self._config_manager.update_module_enabled_state(
            module_conf.mod_id,
            module_conf.enabled)


app = QtWidgets.QApplication(sys.argv)
window = mywindow()
window.show()
sys.exit(app.exec_())
