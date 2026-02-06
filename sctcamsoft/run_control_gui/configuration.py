import logging
from enum import Enum, auto
from datetime import datetime, timezone
from dataclasses import dataclass, field, replace

from pathlib import Path
from os.path import commonpath
from functools import reduce
import yaml

from sctcamsoft.lib_gui.camera_handler import VariableUpdate, CameraHandler, CameraUpdateCache

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot


class ConfigControls(QObject):
    """Methods for updating the GUI according to config behaviors."""

    new_file_browsed = pyqtSignal(Path)
    config_selected = pyqtSignal(int)
    config_needs_save = pyqtSignal()

    apply_config_requested = pyqtSignal()
    force_config_apply = pyqtSignal()
    reset_module_list = pyqtSignal()
    config_apply_canceled = pyqtSignal()

    initialize_mods = pyqtSignal()
    shutdown_mods = pyqtSignal()

    def __init__(self, window):
        """ConfigControls constructor.

        Args:
            window: The pyqt main window instance, which should have (as 
                attributes) all pyqt widgets that are a part of the main GUI.
        """

        super().__init__()

        self.window = window
        self.load_config_button = window.load_config_button
        self.config_path_dropdown = window.config_path_dropdown
        self.config_textbrowser = window.config_textbrowser
        self.apply_status_textbox = window.apply_status_textbox


        self.load_config_button.clicked.connect(self._browse_for_file)
        self.config_path_dropdown.currentIndexChanged.connect(
            self._select_config_file)

        config_font = QFont('Courier')
        config_font.setStyleHint(QFont.Monospace)
        config_font.setPointSize(12)
        self.config_textbrowser.setFont(config_font)

        self.apply_button = window.apply_button
        self.apply_button.clicked.connect(self.apply_config_requested)

        self.init_button = window.initialize_button
        self.init_button.clicked.connect(self.initialize_mods)
        self.shdn_button = window.shutdown_button
        self.shdn_button.clicked.connect(self.shutdown_mods)

    @pyqtSlot(object)
    def update_apply_status(self, new_apply_status):
        # Update the config "applied" status
        if new_apply_status == ApplyStatus.UNAPPLIED:
            self.apply_status_textbox.setText('Not applied')
        elif new_apply_status == ApplyStatus.APPLY_STARTED:
            self.apply_status_textbox.setText('Apply Started')
        elif new_apply_status == ApplyStatus.NEEDS_INIT:
            self.apply_status_textbox.setText('Applied - needs module reinit')
        elif new_apply_status == ApplyStatus.APPLIED:
            self.apply_status_textbox.setText('Applied')

    @pyqtSlot(dict)
    def on_config_changed(self, new_config: dict):
        # Update the config texbox
        yaml_string = yaml.dump(
            new_config,
            default_flow_style=None)
        self.config_textbrowser.setText(yaml_string)

    @pyqtSlot()
    def show_module_reinit_warning(self):
        warning_box = QMessageBox()
        warning_box.setIcon(QMessageBox.Warning)
        warning_box.setText(
            'Applying this configuration will take a long time.')
        warning_box.setInformativeText(
            'This configuration changes the module list, and will '
            'require reinitializing all camera modules. You can apply this '
            'configuration as is, or reset the module list to match those '
            'current initialized.')
        apply_btn = warning_box.addButton(
            'Apply Anyways', QMessageBox.AcceptRole)
        reset_mods_btn = warning_box.addButton(
            'Reset Module List', QMessageBox.DestructiveRole)
        cancel_btn = warning_box.addButton('Cancel', QMessageBox.RejectRole)
        warning_box.exec()

        clicked_btn = warning_box.clickedButton()
        if (clicked_btn == apply_btn):
            self.force_config_apply.emit()
        elif (clicked_btn == reset_mods_btn):
            self.reset_module_list.emit()
        elif (clicked_btn == cancel_btn):
            self.config_apply_canceled.emit()

    def _browse_for_file(self):
        # Start the file dialog
        file_path_string, _ = QFileDialog.getOpenFileName(
            self.window,
            'Open File',
            '',
            'Yaml Files (*.yaml *.yml);;All Files (*)',
            None,
            QFileDialog.DontUseNativeDialog)

        # If the dialog was canceled, return early
        if not file_path_string:
            return

        file_path = Path(file_path_string)
        file_path = file_path.resolve()
        self.new_file_browsed.emit(file_path)

    def _select_config_file(self, index):
        self.config_selected.emit(index)

    def available_configs_updated(self, paths: list):
        # Create the display names for the the dropdown
        if len(paths) == 1:
            # If there's just one option, we only need the filename
            file_short_names = [paths[0].name]
        else:
            # If there are multiple, they are distinguished by
            # path. Strip off some of the common root path to keep
            # the string lengths readable.
            try:
                prefix = commonpath(paths)
                prefix_end = len(str(Path(prefix).parent)) + 1
            except ValueError as err:
                prefix_end_index = 0
            finally:
                file_short_names = \
                    [str(path)[prefix_end:] for path in paths]

        # Update the dropdown, blocking the redundant signals
        self.config_path_dropdown.blockSignals(True)
        self.config_path_dropdown.clear()
        self.config_path_dropdown.addItems(file_short_names)
        self.config_path_dropdown.blockSignals(False)

        logging.debug(
            'The selectable config file options have been updated:\n%r',
            paths)

    def on_file_loaded(self, config, new_index):
        """Select the right one from the list."""
        self.config_path_dropdown.blockSignals(True)
        self.config_path_dropdown.setCurrentIndex(new_index)
        self.config_path_dropdown.blockSignals(False)

        self.on_config_changed(config)


class ConfigManager(QObject):
    """The top-level class responsible for all aspects of run configuration.

    Run "configuration" refers to updating the Camera's (via the camera server)
    settings for a particular observing run. Configurable parameters are
    stored locally in YAML files, and the camera is according to those 
    parameters via a set of commands.

    ConfigManager orchestrates config file management (using ConfigFileManager),
    keeps track of the server's current configuration (using 
    ServerConfiguration), keeps track of the GUI's loaded "local" configuration
    (using LocalConfiguration), and updates the front-end widgets when necessary
    (using ConfigControls).

    Finally, ConfigManager implements the procedure for "applying" a 
    configuration - that is, sending the server the commands required to update
    the server's settings to match parameters defined in the local configuration.
    The status of this application process is also tracked by ConfigManager.

    Note that in many of the docstring comments, "the LocalConfiguration" refers
    to the `self.local_conf` object, and "the ServerConfiguration" referes to
    the `self.server_conf` object.

    Attributes:
        local_conf: A LocalConfiguration object that holds the run config
            currently loaded into the GUI.
        server_conf: A ServerConfiguration object that tracks the run config
            already configured on the server.
        apply_status: An ApplyStatus value indicating what stage of config
            application the ConfigManager is in. 
    """ 

    def __init__(self, camera: CameraHandler, config_controls: ConfigControls):
        """Create the ConfigManager object.

        Args:
            camera: A CameraHandler object that recieves "target" and
                "backplane" subsystem updates and provides functionality 
                for ConfigManager to send commands to the server.
            config_controls: A ConfigControls object, which will be used
                to update the GUI according to events in managed in 
                ConfigManager.
        """

        super().__init__()

        self._camera = camera
        self._camera.on_error.connect(self.on_error)

        self._file_manager = ConfigFileManager()

        self.local_conf = LocalConfiguration()
        self.server_conf = ServerConfiguration(camera)
        self.server_conf.server_config_changed.connect(self._update_apply_status)
        self.server_conf.request_config_from_server()

        self._config_controls = config_controls
        self._config_controls.new_file_browsed.connect(
            self._file_manager.add_and_load_configuration)
        self._config_controls.config_selected.connect(
            self._file_manager.load_configuration)
        self._file_manager.config_list_updated.connect(
            self._config_controls.available_configs_updated)
        self._file_manager.config_file_loaded.connect(
            self.set_conf)

        self._config_controls.apply_config_requested.connect(
            self.pre_apply_config)
        self._config_controls.force_config_apply.connect(
            self.apply_local_config)
        self._config_controls.reset_module_list.connect(
            self.reset_module_list)
        self._config_controls.initialize_mods.connect(
            self.initialize_mods)
        self._config_controls.shutdown_mods.connect(
            self.shutdown_mods)

        self.apply_started = None
        self.apply_status = ApplyStatus.UNAPPLIED
        self._update_apply_status()

        self._file_manager.setup_defaults()

    def on_error(self, error):
        """Prints error messages from the server."""

        logging.error('The camera reported an error:\n %r', error)

    def set_conf(self, conf: dict, new_index: int):
        """Update local_conf with a new config from ConfigFileManager's list.
        
        Args:
            conf: The new configuration dictionary with with to update 
                `local_conf`.
            new_index: The index of the new config in the caller's list
                of available configurations.
        """

        self.local_conf.config = conf

        logging.debug('Validating new configuration... ')
        validation_result = self.local_conf.validate()
        if (self.local_conf.is_valid()):
            logging.info('The new local configuration is valid.')
        else:
            logging.info('The new configuration is not valid. The validation '
                         'process yielded the following result:\n%r', 
                         validation_result)    
            
        self._update_apply_status()
        self._config_controls.on_file_loaded(conf, new_index)
        self._config_controls.on_config_changed(conf)

    def update_module_enabled_state(self, mod_id, request_enabled):

        id_list = self.local_conf.config['module_ids']
        if (request_enabled):
            if (mod_id not in id_list):
                id_list.append(mod_id)
        else:
            try:
                id_list.remove(mod_id)
            except ValueError: pass  

        self._config_controls.on_config_changed(self.local_conf.config)
        self._update_apply_status()

    def pre_apply_config(self):
        """Procedure first run when the GUI requests a config be applied.

        pre_apply_config does not apply LocalConfiguration to the camera 
        immeadiately. First, it checks the current ServerConfiguration against
        the LocalConfiguration to see if applying the LocalConfiguration would
        require reinitializing/reconnecting to all Camera modules (that is, 
        if the LocalConfiguration changes the enabled module list in the 
        server). 
        
        If applying the LocalConfiguration requires changing the module list,
        a warning is displayed. If it does not require changing the list,
        the config is applied using `apply_local_config()`.
        """

        if (not self._are_mod_lists_eq()):
            logging.warning('This configuration will require module '
                            'reinitialization. Please confirm you '
                            'want to apply.')
            self._config_controls.show_module_reinit_warning()
        else:
            self.apply_local_config()

    def reset_module_list(self):
        """Resets the enabled module list in LocalConfiguration."""

        logging.info(f'Resetting the configuration\'s module list '
                     f'to match those already initialized on '
                     f'the server: {self.server_conf.config["module_ids"]}')
        self.local_conf.config['module_ids'] = self.server_conf.config['module_ids']
        self._config_controls.on_config_changed(self.local_conf.config)
        self._update_apply_status()

    def apply_local_config(self):
        """Performs application of a LocalConfiguration.

        Submits a series of server commands to update Camera settings according
        to the parameters set by the `self.local_conf` LocalConfiguration 
        object. Updates ApplyStatus accordingly.

        Notice that in most cases, there are two commands to set an individual
        setting. The first notifies the server of the requested value 
        ("request" commands), and the second directs the server to apply that 
        value (which is has stored internally) to the camera hardware ("set"
        commands).

        For the most up-to-date information on configuration application 
        commands, review the `commands.yml` file.
        """

        logging.debug('Configuration application is starting.')
        self.apply_started = datetime.now(timezone.utc)

        conf = self.local_conf.config

        if (conf['run_type'] != 'data'):
            raise NotImplementedError(
                "Only datataking runs are implemented.")

        # First, if necessary, enable and disable modules according to
        # the local configuration's list.
        self._en_disable_mods('module_ids', 
                              'target/enable_module {}', 
                              'target/disable_module {}')

        # Enable and disable triggering modules according to the local
        # config trigger list.
        self._en_disable_mods('trigger_module_ids', 
                              'target/enable_trigger_module {}', 
                              'target/disable_trigger_module {}') 

        if (conf['run_type'] == 'data'):
            # Set the readout parameters
            self._request_readout_param('channels_per_packet', 
                                        conf['channels_per_packet'])
            self._request_readout_param('trigger_delay', 
                                        conf['trigger_delay'])
            self._request_readout_param('packet_separation',
                                        conf['packet_separation'])
            self._request_readout_param('thresh',
                                        conf['thresh'])

        # Apply those config changes
        # TODO: Should this be happening on "initialize"?
        # self._camera.send_command('target/set_readout_parameters')

        # TODO: Why is this here?
        # self._camera.send_command('target/set_asic_parameters')

        # Next, set the tuning paramters
        self._request_tuning_param('hv_on', conf['hv_on'])
        self._request_tuning_param('add_bias', conf['add_bias'])
        if (conf['run_type'] == 'data'):
            self._request_tuning_param('num_blocks', conf['num_blocks'])


        # Tell the server to apply the new parameters
        # self._camera.send_command('target/set_tuning_parameters')

        ##add by Atreya Acharyya
        self._camera.send_command('prepare_modules')

    def _en_disable_mods(self, param, enable_command, disable_command):
        """Send enable/disable commands to update server module lists. 

        Enable/disable modules according to differences between the server 
        and local module lists. This method efficiently updates a server module
        list using a series of individual enable_command and disable_command 
        commands. It sends an enable_command for each module that exists in
        the LocalConfiguration that does not exist in the ServerConfiguration,
        and sends a disable_command for each module that exists in the 
        ServerConfiguration that does not exist in the LocalConfiguration.

        Returns:
            Boolean flag indicating if any modules were enabled or disabled.
        """

        server_mods = set(self.server_conf.config[param])
        conf_mods = set(self.local_conf.config[param])

        mods_to_enable = conf_mods - server_mods
        for mod_id in mods_to_enable:
            self._camera.send_command(enable_command.format(mod_id))

        mods_to_disable = server_mods - conf_mods
        for mod_id in mods_to_disable: 
            self._camera.send_command(disable_command.format(mod_id))

        return (mods_to_enable or mods_to_disable)

    def _request_tuning_param(self, parameter, value):
        """Convenience function, eases sending a tuning parameter request."""

        self._camera.send_command(
            'target/request_tuning_parameter {param} {val}'.format(
                param=parameter, val=value))

    def _request_readout_param(self, parameter, value):
        """Convenience function, eases sending a readout parameter request."""

        self._camera.send_command(
            'target/request_readout_parameter {param} {val}'.format(
                param=parameter, val=value))

    def _are_mod_lists_eq(self):
        """Compare enabled module lists in `local_conf` and `server_conf`."""

        mods_param = 'module_ids'
        if (mods_param not in self.local_conf.config and
                mods_param not in self.server_conf.config):
            return True
        else:
            try:
                return (set(self.local_conf.config[mods_param]) ==
                        set(self.server_conf.config[mods_param]))
            except:
                return False

    def _update_apply_status(self):
        """Updates the "ApplyStatus" widget according to current state.
        
        Uses `self.local_conf` and `self.server_conf` to determine whether or 
        not the LocalConfiguration has been fully applied to the camera."""

        def confs_eq_without_mod_lists(conf_one: BaseConfiguration, 
                                       conf_two: BaseConfiguration):
            """Copy configs and compare them after deleting "module_ids" list."""
            
            mods_param = 'module_ids'
            conf_one_copy = dict(conf_one.config)
            conf_one_copy.pop(mods_param, None)

            conf_two_copy = dict(conf_two.config)
            conf_two_copy.pop(mods_param, None)

            return conf_one_copy == conf_two_copy

        # If the configurations are completely equal, then it has been applied.
        if (self.local_conf == self.server_conf):
            self.apply_status = ApplyStatus.APPLIED

        # If the configurations are equal EXCEPT for the enabled module lists,
        # the camera needs to be reinitialized.
        elif (confs_eq_without_mod_lists(self.local_conf, self.server_conf) 
                and not self._are_mod_lists_eq()):
            self.apply_status = ApplyStatus.NEEDS_INIT

        # If neither of the above are true, but an application process has 
        # been started, then "APPLY_STARTED."
        elif (self.apply_started is not None):
            self.apply_status = ApplyStatus.APPLY_STARTED

        # Finally, if none of the above are true, then the configuration is
        # completely "UNAPPLIED."
        else:
            self.apply_status = ApplyStatus.UNAPPLIED

        # Once apply_status has been calculated, update the GUI accordingly.
        self._config_controls.update_apply_status(self.apply_status)

    def initialize_mods(self):
        logging.info('Sending \'prepare_modules\' command. Modules will be initialized '
                     'according to the last applied configuration.')
        self._camera.send_command('prepare_modules')

    def shutdown_mods(self):
        logging.error('The function is not yet implemented.')


class ApplyStatus(Enum):
    UNAPPLIED = auto()
    APPLY_STARTED = auto()
    NEEDS_INIT = auto()
    APPLIED = auto()


class ConfigFileManager(QObject):
    """Maintains list of config files and permits loading them from FS.
    
    Attributes:
        config_list_updated: pyqtSignal emitted when the list of accessible
            config file Paths is update. The updated list is emitted.
        config_file_loaded: pyqtSignal emitted when a "load_configuration" has
            completed and the config file's data is available. The loaded data
            and the list index of the loaded file are emitted.
    """

    config_list_updated = pyqtSignal(list)
    config_file_loaded = pyqtSignal(dict, int)

    def __init__(self):
        """Create ConfigFileManager object with empty list of paths."""

        super().__init__()

        # Create the list of configurations and add defaults
        self._config_paths = []

    def setup_defaults(self):
        """Reset to default list of config_paths and notify listeners.""" 

        this_modules_directory = Path(__file__).parent.resolve()
        self._config_paths = [
            this_modules_directory / 'run_config.default.yml',
            this_modules_directory / 'rate_scan_config.default.yml'
        ]
        self.config_list_updated.emit(self._config_paths)
        self.load_configuration(0)

    def add_configuration(self, file_path: Path):
        """Add a config path to the list, or moves it to the top if it exists."""

        try:
            # If this config is already in the list, move
            # it to the top.
            self._config_paths.remove(file_path)

            # Add the path to the front of the list
            self._config_paths.insert(0, file_path)

        except ValueError:
            # If we get here, the config was not in the list
            self._config_paths.append(file_path)

        self.config_list_updated.emit(self._config_paths)

        return len(self._config_paths) - 1

    def load_configuration(self, config_index: int):
        """Loads a configuration from the file system by list index."""

        # Load the configuration
        try:
            conf_path = self._config_paths[config_index]
            with open(conf_path, 'r') as conf:
                config = yaml.safe_load(conf)
                logging.info('Loaded config from file:\n%r', config)
        except:
            logging.exception('Error reading the configuration file.')

        self.config_file_loaded.emit(config, config_index)

    def add_and_load_configuration(self, file_path: Path):
        """Convienence method for adding and loading a new path at once."""

        new_index = self.add_configuration(file_path)
        self.load_configuration(new_index)

class BaseConfiguration():
    """A run configuration.

    BaseConfiguration wraps a `config` dictionary (which may have be read
    directly from a YAML run configuration file). It also provides the ability 
    to compare BaseConfiguration's for equality, and run a validation process 
    on the config dictionary itself. 

    Attributes:
        config: The configuration dictionary. Configured parameters are 
            members of this dict.
    """

    def __init__(self, config: dict = {}):
        self.config = config

    def __eq__(self, other):
        """Compare Configuration wrappers based on the config field."""

        if not isinstance(other, BaseConfiguration): 
            raise NotImplementedError
            
        return self.config == other.config

    def validate(self):
        """Validate this configuration.

        Analyze the `config` dictionary and confirm that it contains 
        the correct keys. Assemble a ValidationResult object summarizing
        any missing parameters, invalid parameters, or parameters that are 
        attached to the object but shouldn't be.

        Returns:
            A ValidationResult containing the results of the config check.
        """

        val_result = ValidationResult()

        if 'run_type' not in self.config:
            val_result.missing_params.append('run_type')

            # No further validation steps possible without knowing the run type
            return val_result  

        if self.config['run_type'] not in ['data', 'rate_scan']:
            val_result.invalid_param_values.append('run_type')

        required_run_params = [
            'run_type',
            'module_ids',
            'trigger_module_ids',
            'hv_on',
            'read_temperatures',
            'read_currents',
            'add_bias'
        ]

        if self.config['run_type'] == 'data':
            required_run_params.extend([
                'run_duration',
                'thresh',
                'num_blocks',
                'read_adc_period',
                'channels_per_packet',
                'packet_separation',
                'trigger_delay'
            ])

        elif self.config['run_type'] == 'rate_scan':
            required_run_params.extend([
                'pe_thresholds_bounds',
                'pe_thresholds_step',
                'desired_rate'
            ])

        # Check that all required parameters exist
        for param in required_run_params:
            if param not in self.config:
                val_result.missing_params.append(param)

        # Catalog any extra parameters that should not be included
        for param in self.config:
            if param not in required_run_params:
                val_result.extraneous_params.append(param)

        # TODO: Validate that the existent parameters are legal values

        return val_result

    def is_valid(self):
        """Convience method returns true if the config is valid.

        Runs `validate()`, then checks the returned ValidationResult for 
        missing parameters or invalid parameters. 

        Returns:
            True if there are no missing or invalid parameters, false otherise.
        """

        validation_result = self.validate()

        return (len(validation_result.missing_params) == 0
            and len(validation_result.invalid_param_values) == 0)


@dataclass
class ValidationResult:
    """A simple dataclass container for results of the config validation check."""

    missing_params: list = field(default_factory=list)
    extraneous_params: list = field(default_factory=list)
    invalid_param_values: list = field(default_factory=list)


class LocalConfiguration(BaseConfiguration):
    """A convienence class, renames BaseConfiguration.
    
    Wraps BaseConfiguration with a new name to distinguish it 
    from ServerConfiguration. See documentation for BaseConfiguration
    for behavior.
    """

    def __init__(self, config: dict = {}):
        super().__init__(config)


class ServerConfiguration(QObject, BaseConfiguration):
    """Maintains a config dictionary based on Camera server updates.

    ServerConfiguration is an instance of BaseConfiguration that updates 
    its `self.config` dict based on updates recieved from the server (via
    a CameraHandler object).

    The Camera server should broadcast an update each time a configurable 
    parameter is set on the camera. This class recieves those updates, then 
    updates the internal config dictionary with the broadcast value. The 
    criteria for a valid ServerConfiguration and LocalConfiguration are the 
    same - that is, ServerConfiguration uses the CameraHandler to create a 
    config dict that is compatible with and comparable to the LocalConfiguration.

    Attributes: 
        server_config_changed: A pyqtSignal emitted each time the config dict is
            changed according to a new camera update.
    """

    server_config_changed = pyqtSignal(dict)

    def __init__(self, camera: CameraHandler, cache=None):
        """ServerConfiguration constructor.

        Args:
            camera: A CameraHandler object that recieves 'target' and 
                'backplane' updates.
            cache: Optional. A CameraUpdateCache that will be used to 
                immeadiately populate the `self.config` object according to
                updates recieved before this ServerConfiguration was 
                instantiated.
        """

        super().__init__()
        
        self._camera = camera
        self._camera.on_update.connect(self._on_update)

        self.config['module_ids'] = []
        self.config['trigger_module_ids'] = []

        self.conf_update_times: dict = {}

        if cache:
            self._from_cache(cache)

    def _from_cache(self, cache: CameraUpdateCache):
        """Run through updates in an existing cache to create a server config."""

        for device in self._camera.monitored_devices:
            for name in cache.get_device_var_names(device):
                update = cache.get_var_update(device, name)
                self._on_update(update, cache)

    def _on_update(self, update: VariableUpdate, cache: CameraUpdateCache):
        """Handle VariableUpdates from the server."""

        UPDATE_TO_CONFIG_ASSOC = {
            'tuning_parameters': {
                'hv_on':                ('hv_on', bool),
                'num_blocks':           ('num_blocks', int),
                'add_bias':             ('add_bias', int)
            },
            'readout_parameters': {
                'thresh':               ('thresh', int),
                'channels_per_packet':  ('channels_per_packet', int),
                'trigger_delay':        ('trigger_delay', int),
                'packet_separation':    ('packet_separation', int),
            }
        }

        if update.device == 'target':
            if update.variable in ('module_ids' or 'trigger_module_ids'):
                conf_key = update.variable
                self.config[conf_key].clear()
                if (update.value is not None):
                    for id_value in update.value:
                        module_id = int(id_value.identifier)
                        self.config[conf_key].append(module_id)
                self.conf_update_times[conf_key] = update.time_sent

            elif update.variable in UPDATE_TO_CONFIG_ASSOC.keys():
                if update.has_multiple_values:
                    for value in update.value:
                        association = UPDATE_TO_CONFIG_ASSOC[update.variable]
                        if (value.identifier not in association):
                            continue
                        conf_key, formatter = association[value.identifier]
                        if (value.value == 'None'):
                            formatted = None
                        else:
                            formatted = formatter(value.value)
                        self.config[conf_key] = formatted
                        self.conf_update_times[conf_key] = update.time_sent

        self.server_config_changed.emit(self.config)

    def request_config_from_server(self):
        """Send commands to get config values.
        
        Send "getter" commands to retrieve all variable updates necessary for
        a complete ServerConfiguration."""

        # TODO: Fill in with all request commands.
        self._camera.send_command('target/get_module_ids')
        self._camera.send_command('target/get_trigger_module_ids')
        self._camera.send_command('target/get_tuning_parameters')
        self._camera.send_command('target/get_readout_parameters')