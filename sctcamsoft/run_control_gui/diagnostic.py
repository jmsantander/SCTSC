import sys
import logging
import yaml
import argparse
import pprint
import datetime

from PyQt5.QtWidgets import QApplication, QDialog, QTableWidgetItem
from PyQt5.QtCore import QThread, QTimer

from sctcamsoft.lib_gui.camera_comm import CameraComm
from sctcamsoft.lib_gui.camera_handler import CameraHandler, VariableUpdate
from sctcamsoft.run_control_gui.diagnostic_dialog import Ui_diagnostic_view_dialog
from sctcamsoft.run_control_gui.configuration import ServerConfiguration, LocalConfiguration

class DiagnosticView(QDialog, Ui_diagnostic_view_dialog):
    """Top-level window for a class for the RC diagnostic view.
    
    This window is meant for an expert observer or a developer. It provides 
    views for the entire CameraUpdateCache, as well as views for the RC
    configuration objects. Finally, it permits sending custom commands.
    """
    
    def __init__(self, 
                camera: CameraHandler, 
                server_conf: ServerConfiguration=None, 
                local_conf: LocalConfiguration=None):
        """DiagnosticView constructor.

        Args:
            camera: A CameraHandler that will be monitored to update
                the camera_cache_table.
            server_conf: A reference to a ServerConfiguration that will
                be displayed on the view.
            local_conf: A reference to a LocalConfiguration that will
                be displayed on the view.
        """

        super().__init__()
        self.setupUi(self)

        self._camera = camera
        self._server_conf = server_conf
        self._local_conf = local_conf

        self.var_to_row = {}

        self._create_camera_cache_table()
        self._reset_camera_cache_table_from_cache(
            self._camera.get_cache())
        self._set_camera_cache_selected_update(None)
        self.camera_cache_table.itemSelectionChanged.connect(
            self._camera_cache_table_selection)
        self._selected_update_pprinter = pprint.PrettyPrinter(indent=2)

        self.command_input.returnPressed.connect(self._send_command)
        self.send_command_button.clicked.connect(self._send_command)

        self._camera.on_update.connect(self.on_camera_update)

        self.timer_1000 = QTimer()
        self.timer_1000.start(1000)
        self.timer_1000.timeout.connect(self._update_conf_displays)

    def _create_camera_cache_table(self):
        self.table_cols = VariableUpdate._fields
        self.camera_cache_table.setColumnCount(len(self.table_cols))
        self.camera_cache_table.setHorizontalHeaderLabels(self.table_cols)

    def _reset_camera_cache_table_from_cache(self, cache):
        # First, get a list of all the vars that will be displayed.
        all_vars = []
        for device in self._camera.monitored_devices:
            var_names = cache.get_device_var_names(device)
            for var_name in var_names:
                all_vars.append((device, var_name))
        
        # Then, fill the table with the update data by iterating
        # through each column for each variable extracted above
        self.camera_cache_table.clearContents()
        for row, (device, var_name) in enumerate(all_vars):
            update = cache.get_var_update(device, var_name)
            self._handle_camera_cache_update(update)

    def _handle_camera_cache_update(self, update):
        # Check to see if this update is already in the table
        var_identifier = (update.device, update.variable)

        # Expand the table if necessary, and keep track of 
        # which row should be updated
        if (var_identifier in self.var_to_row):
            row = self.var_to_row[var_identifier]
        else:
            row = self.camera_cache_table.rowCount()
            self.var_to_row[var_identifier] = row
            self.camera_cache_table.setRowCount(row + 1)

        self._fill_camera_cache_table_row(row, update)

    def _fill_camera_cache_table_row(self, row, update):
        for col, update_field in enumerate(self.table_cols):
            update_field_val = getattr(update, update_field)

            if isinstance(update_field_val, datetime.datetime):
                dt = update_field_val # Readability
                item_text = f'{dt.hour:02}:{dt.minute:02}:{dt.second:02}.{int(dt.microsecond / 1000):03}'
            else:
                item_text = str(update_field_val)

            table_item = QTableWidgetItem(item_text)
            self.camera_cache_table.setItem(row, col, table_item)

    def _camera_cache_table_selection(self):
        selected_items = self.camera_cache_table.selectedItems()

        if not selected_items:
            self._set_camera_cache_selected_update(None)
            return 

        # All items selected should be the same row - so just grab the first
        selected_row = selected_items[0].row()

        # Find the variable in this row
        selected_var = None
        for (var_identifier, var_row) in self.var_to_row.items():
            if (selected_row == var_row):
                selected_var = var_identifier
                break

        update = self._camera.get_cache().get_var_update(*selected_var)
        self._set_camera_cache_selected_update(update)

    def _set_camera_cache_selected_update(self, update):
        self.camera_cache_selected_update = update

        if not update:
            self.camera_update_view_textbrowser.setText('')
        else:
            update_str = self._selected_update_pprinter.pformat(dict(update._asdict()))
            self.camera_update_view_textbrowser.setText(update_str)

    def _update_camera_cache_selected_update(self):
        self._set_camera_cache_selected_update(
            self.camera_cache_selected_update)

    def on_camera_update(self, update, cache):
        self._handle_camera_cache_update(update)

        if (self.camera_cache_selected_update is not None and
            update.device == self.camera_cache_selected_update.device and
            update.variable == self.camera_cache_selected_update.variable):
            self._set_camera_cache_selected_update(update)

    def _update_conf_displays(self):
        if (self._server_conf):
            server_conf_string = yaml.dump(
                self._server_conf.config,
                default_flow_style=None)
            self.server_conf_textbrowser.setText(server_conf_string)

        if (self._local_conf):
            local_conf_string = yaml.dump(
                self._local_conf.config,
                default_flow_style=None)
            self.local_conf_textbrowser.setText(local_conf_string)

    def _send_command(self):
        command_to_send = self.command_input.text()

        if command_to_send:
            self._camera.send_command(command_to_send)
        
        self.command_input.selectAll()

def main():
    """Main method, allows opening the diagnostic view w/o opening the RC GUI.

    Instantiates the necessary camera communication code, and creates a 
    CameraHandler that listens to all subsystems and all alerts. Note, the
    ServerConfiguration and LocalConfiguration displays will simply be blank
    when the diagnostic view is opened directly.
    """

    # Configure logging to the terminal that spawned the GUI
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)7s - %(threadName)s - %(message)s')
    
    app = QApplication(sys.argv)

    parser = argparse.ArgumentParser()
    parser.add_argument('config_file', help='Path to slow control config file', )
    parser.add_argument('commands_file', help='Path to slow control commands file')
    args = parser.parse_args()

    with open(args.config_file, 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.SafeLoader)
        ui_config = config['user_interface']

    with open(args.commands_file, 'r') as commands_file:
        commands = yaml.load(commands_file, Loader=yaml.SafeLoader)

    # Configure and start the camera communication code,
    # then move it to it's own thread.
    _comm_thread = QThread()
    _camera_comm = CameraComm(
        ui_config['host'],
        ui_config['input_port'],
        ui_config['output_port'],
        ui_config['header_length'],
        commands)
    # Change the thread affinity
    _camera_comm.moveToThread(_comm_thread)
    _comm_thread.start()  # Start the QThread
    _camera_comm.init()  # Configure the communication thread

    def on_connect_state_changed(new_val):
        logging.info('Connection state changed, value is now [%r]', new_val)

    _camera_comm.on_connec_state_changed.connect(
            on_connect_state_changed)

    # Create a CameraHandler other classes can use
    # to interface with the lower-level CameraComm obj
    _camera = CameraHandler(
        [], [], 
        _camera_comm.on_update,
        _camera_comm.send_command)

    # Create the ModuleConfig dialog
    dialog = DiagnosticView(_camera)
    dialog.resize(800, 480)
    dialog.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
