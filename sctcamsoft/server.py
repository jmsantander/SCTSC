"""Server for control of SCT Camera"""

from abc import ABC, abstractmethod
import argparse
from collections import namedtuple
import selectors
import socket
import sys
import threading
import traceback

import yaml

import run_control  # trunk/data_taking/run_control.py

from sctcamsoft.camera_control_classes import (DeviceCommand,
                                               DeviceController,
                                               Update)
from sctcamsoft.camera_control_classes import (CameraControlError,
                                               CommandArgumentError,
                                               CommandExecutionError,
                                               CommandNameError,
                                               CommandSequenceError,
                                               ConfigurationError,
                                               DeviceNameError,
                                               VariableError)
import sctcamsoft.controllers as ctrl
import sctcamsoft.controllers.mock as mockctrl
import sctcamsoft.camera_control_pb2 as cc

UserCommand = namedtuple('UserCommand', ['command', 'args'])

class ControlManager(ABC):
    """
    Manage a particular aspect of camera control within the server.
    Monitor updates and autonomously issue commands.
    """

    def __init__(self, name):
        self.name = name

    @abstractmethod
    def process_update(self, update):
        """
        Inspect the provided Update.
        Return a UserCommand to execute, or None.
        """
        raise NotImplementedError


class AlertManager(ControlManager):
    """Manages alerts"""

    def __init__(self, name, device, variable, lower_limit, upper_limit):
        super().__init__(name)
        self.device = device
        self.variable = variable
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        self.alerted = False

    def process_update(self, update):
        for value_id, value in update.values:
            if (update.device == self.device
                    and update.variable == self.variable):
                try:
                    alert_value = float(value)
                except ValueError:
                    raise VariableError(update.device, update.variable,
                                        value, "could not convert "
                                        "to float for alert")
                outside_limits = not (self.lower_limit <= alert_value
                                      <= self.upper_limit)
                if outside_limits and not self.alerted:
                    self.alerted = True
                    command_args = {
                        'name': self.name,
                        'value': value,
                        'value_id': value_id,
                        'lower_limit': self.lower_limit,
                        'upper_limit': self.upper_limit,
                        'unit': update.unit,
                        }
                    alert_command = UserCommand('issue_alert', command_args)
                    return alert_command
                if not outside_limits and self.alerted:
                    self.alerted = False
                    command_args = {'name': self.name}
                    clear_command = UserCommand('clear_alert', command_args)
                    return clear_command
        return None


class RunManager(ControlManager):
    """Manages runs and rate scans"""

    def __init__(self):
        super().__init__('run_manager')
        self.state = 'IDLE'
        self.run_type = None
        self.run_id = None

        self._prev_thresh = None
        self._prev_rate = None

        self._transitions = {
            ('IDLE', 'define_run'): 'DEFINED',
            ('DEFINED', 'initialize_run'): 'INITIALIZED',
            ('DEFINED', 'end_run'): 'TERMINATED',
            ('INITIALIZED', 'start_run'): 'ACTIVE',
            ('INITIALIZED', 'end_run'): 'TERMINATED',
            ('ACTIVE', 'end_run'): 'COMPLETE',
            ('ACTIVE', 'read_rate'): 'ACTIVE',
            ('COMPLETE', 'clear_run'): 'IDLE',
            ('TERMINATED', 'clear_run'): 'IDLE',
            }
        self._instructions = list({instruction for (state, instruction)
                                  in self._transitions})
        # TODO: replace hardcoded placeholders with methods to set
        # using user-provided values from run control
        # Data run variables
        self.adc_interval = 30  # seconds
        self.run_interval = 1800  # seconds
        # Rate scan variables
        self.start_thresh = 600  # DAC
        self.stop_thresh = 0  # DAC
        self.max_spacing = 50  # DAC
        self.min_spacing = 10 # DAC
        self.alpha = 1.5
        self.read_hitmaps = False
        self.num_hitmaps = 50


    def process_update(self, update):
        if update.device == 'target' and update.variable == 'trigger_rate':
            instruction = 'read_rate'
        elif update.device == 'server':
            instruction = update.variable
            if instruction not in self._instructions:
                return None
        else:
            return None
        trigger = (self.state, instruction)
        if trigger not in self._transitions:
            message = "{} is not a valid instruction in run state {}".format(
                instruction, self.state)
            raise CommandSequenceError('server', instruction, message)
        self.state = self._transitions[trigger]
        command = None
        if instruction == 'define_run':
            self.run_id = self._get_run_id()
            self._prev_thresh = None  # for rate scans
            self._prev_rate = None  # for rate scans
        elif instruction in ['initialize_data_run', 'initialize_rate_scan']:
            self.run_type = instruction[11:]  # remove 'initialize_'
            command = UserCommand("initialize_run", {'run_id': self.run_id})
        elif instruction == 'start_run':
            args = {}
            if self.run_type == 'data_run':
                args['adc_interval'] = self.adc_interval
                args['end_run_interval'] = self.run_interval
            elif self.run_type == 'rate_scan':
                args['thresh'] = self.start_thresh
            command = UserCommand("start_{}".format(self.run_type), args)
        elif instruction == 'read_rate':
            thresh, rate = update.values['thresh'], update.values['rate']
            command = self._read_rate(thresh, rate)
            self._prev_thresh, self._prev_rate = thresh, rate
        elif instruction == 'end_run':
            # Only send command if run is complete, no need if terminated
            if self.state == 'COMPLETE':
                command = UserCommand("end_{}".format(self.run_type), {})
        elif instruction == 'clear_run':
            self.run_id = None
            self.run_type = None
        return command


    @staticmethod
    def _get_run_id():
        """Gets the run number

        Uses the run control script based on reading a text file
        located on the UW cluster. A future implemention should
        define the run number using a local database.
        """
        run_control_dir = "/home/ctauser/target5and7data"
        run_id = run_control.incrementRunNumber(run_control_dir)
        return run_id


    def _calculate_spacing(self, derivative):
        """Calculates the spacing to the next threshold in the rate scan

	Determine the spacing after each threshold based on the derivative
        of the rate between it and the previous threshold.

        When the derivative is close to 0, the spacing should be large,
        and when the absolute value of the derivative is large,
        the spacing should be small. Calculating the derivative locally
        suffices, as the rate varies fairly smoothly. Thus, there is no need
        to manually determine the transition threshold(s).

        Use a sigmoid function to smooth the transition from high/low spacing.
        The alpha parameter controls the sensitivity of the smoothing,
        with a higher alpha producing a steeper transition.
        """
        sigmoid = 1 / (1 + pow(abs(derivative), self.alpha))
        scale = self.max_spacing - self.min_spacing
        offset = self.min_spacing
        spacing = scale*sigmoid + offset
        return round(spacing)


    def _read_rate(self, thresh, rate):
        if None in (self._prev_thresh, self._prev_rate):
            spacing = self.max_spacing
        else:
            derivative = (rate - self._prev_rate) / (thresh - self._prev_thresh)
            spacing = self._calculate_spacing(derivative)
        next_thresh = thresh - spacing
        if next_thresh >= self.stop_thresh:
            command = UserCommand("read_rate", {'thresh': next_thresh})
        else:
            command = UserCommand("end_rate_scan", {})
        return command


class UserHandler():
    """Handles communication with the user clients"""

    def __init__(self, config):
        self.host = config['host']
        self.input_port = config['input_port']
        self.output_port = config['output_port']
        self.header_length = config['header_length']
        self._header_template = "{{:0{}d}}".format(self.header_length)
        self._selector = selectors.DefaultSelector()
        self._user_command = None
        self._user_update = None

        def add_socket(port, accept_fn):
            sock = socket.socket()
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, port))
            sock.listen()
            sock.setblocking(False)
            self._selector.register(sock, selectors.EVENT_READ, accept_fn)

        add_socket(self.input_port, self._accept_input)
        add_socket(self.output_port, self._accept_output)

    def _accept_input(self, sock, mask):
        del mask  # unused
        conn, __ = sock.accept()
        conn.setblocking(False)
        self._selector.register(conn, selectors.EVENT_READ, self._read)

    def _accept_output(self, sock, mask):
        del mask  # unused
        conn, __ = sock.accept()
        conn.setblocking(False)
        self._selector.register(conn, selectors.EVENT_WRITE, self._write)

    def _read(self, conn, mask):
        del mask  # unused
        # Get length of the message from the header
        header = conn.recv(self.header_length)
        if header:
            serialized_message = conn.recv(int(header))

        if header and serialized_message:
            user_command = cc.UserCommand()
            user_command.ParseFromString(serialized_message)
            self._user_command = UserCommand(user_command.command,
                                            dict(user_command.args))
        else:
            self._selector.unregister(conn)
            conn.close()

    def _write(self, conn, mask):
        del mask  # unused
        if self._user_update:
            user_update = cc.UserUpdate()
            for update in self._user_update:
                update_pb = user_update.updates.add()
                update.fill_protobuf(update_pb)
            message = user_update.SerializeToString()
            header = self._header_template.format(len(message)).encode()
            conn.sendall(header + message)

    def communicate_user(self, updates):
        """Read in user commands and write out updates"""
        self._user_command = None
        self._user_update = updates
        for key, mask in self._selector.select(timeout=-1):
            callback = key.data
            conn = key.fileobj
            try:
                callback(conn, mask)
            except ConnectionError:
                self._selector.unregister(conn)
                conn.close()
        self._user_update = None
        return self._user_command

class ServerController(DeviceController):
    """DeviceController for the server

    Implements the main loop of reading in high-level user commands,
    parsing them into low-level device commands,
    sending them to the relevant devices for execution,
    and returning updates of the output.

    The ServerController is a DeviceController itself,
    so in addition to its server functionality
    it acts as a device itself, implementing commands such as
    setting alerts and sending messages.
    """

    def __init__(self, device, config, user_commands, devices):
        print("Slow Control Server")
        print("Initializing server...")
        super().__init__(device, config)
        self._managers = {'_run_manager': RunManager()}
        self._timers = {}
        self._user_handler = UserHandler(config['user_interface'])
        self._updates = []
        self._user_commands = user_commands
        try:
            self._validate_commands(self._user_commands)
            print("Configuring devices:")
            self._device_controllers = {self.device: self}
            for controlled_device, controller in devices.items():
                print("Configuring {}...".format(controlled_device))
                self._device_controllers[controlled_device] = controller(
                    controlled_device, config.get(controlled_device, {}))
        except ConfigurationError as err:
            print('Fatal configuration error in device:', err.device)
            print(err.message)
            print("Shutting down.")
            sys.exit()
        print("Configuration complete.")

    def _validate_commands(self, user_commands):
        for command_name, command_params in user_commands.items():
            # Low level or special commands
            if 'device' in command_params and 'command' in command_params:
                # Validate special commands
                if (command_params['device'] is None
                        and command_params['command'] == 'enter_repeat_mode'):
                    for key in ['interval', 'num_executions',
                                'execute_immediately']:
                        if not key in command_params['args']:
                            raise ConfigurationError(
                                self.device,
                                "enter_repeat_mode: args: " + key,
                                "missing configuration parameter")
                continue
            # High level commands
            if 'command_list' in command_params:
                for arg, arg_keys in command_params.get('args', {}).items():
                    for key in ['index', 'arg']:
                        if not key in arg_keys:
                            raise ConfigurationError(
                                self.device,
                                "{}: args: {}: {}".format(command_name,
                                                          arg, key),
                                "missing configuration parameter")
                continue
            raise ConfigurationError(
                self.device, command_name,
                "command definition must have device and command, "
                "or command list")

    # Break down user command into an unprocessed list of device commands
    # Recursively process nested high-level commands
    def _parse_user_command(self, user_command):

        # Combine command arguments from user input and prespecified values
        def get_command_args(args, user_input, device, command):
            cmd_args = {**args, **user_input} # User input overrides values
            # Check for missing args
            missing_args = [a for a in cmd_args if a is None]
            for arg in missing_args:
                raise CommandArgumentError(device, command, arg,
                                           "missing argument")
            # Check for extra args
            extra_args = list(set(cmd_args) - set(args))

            for arg in extra_args:
                raise CommandArgumentError(device, command, arg,
                                           "extra argument")
            return cmd_args

        cmd_def = self._user_commands[user_command.command]
        args = cmd_def.get('args', {})
        user_input = user_command.args
        # Base case: one command for a particular device ("low level")
        if 'device' in cmd_def and 'command' in cmd_def:
            cmd_args = get_command_args(args, user_input, cmd_def['device'],
                                        cmd_def['command'])
            device_command = DeviceCommand(cmd_def['device'],
                                           cmd_def['command'], cmd_args)
            return [device_command]
        # Recursive case: list of commands ("high level")
        device_commands = []
        for index, command in enumerate(cmd_def['command_list']):
            sub_arg_names = {a: args[a]['arg'] for a in args
                             if args[a]['index'] == index}
            sub_args = {sub_arg_names[a]: args[a]['val']
                                          if 'val' in args[a] else None
                        for a in sub_arg_names}
            sub_user_input = {sub_arg_names[a]: user_input[a]
                              for a in sub_arg_names if a in user_input}
            cmd_args = get_command_args(sub_args, sub_user_input,
                                        self.device, user_command.command)
            user_subcommand = UserCommand(command, cmd_args)
            device_subcommands = self._parse_user_command(user_subcommand)
            device_commands.extend(device_subcommands)
        return device_commands

    def _execute_device_command_list(self, device_command_list):

        repeat_depth = 0
        repeat_cmds = []
        RepeatParams = namedtuple('RepeatParams',
                                  ['name', 'interval', 'num_executions',
                                   'execute_immediately'])
        for dc in device_command_list:
            # Begin mode to list commands to repeatedly execute later
            if dc.device is None and dc.command == 'enter_repeat_mode':
                if repeat_depth == 0: # This is the first nested repeat
                    try:
                        name = dc.args['name']
                    except KeyError:
                        raise CommandArgumentError(self.device, dc.command,
                                                   'name', "missing argument")
                    try:
                        interval = dc.args['interval']
                        if interval is None:
                            raise KeyError
                        interval = float(interval)
                    except KeyError:
                        raise CommandArgumentError(self.device, dc.command,
                                                   'interval',
                                                   "missing argument")
                    except ValueError:
                        raise CommandArgumentError(self.device, dc.command,
                                                   'interval', "must be float")
                    try:
                        num_executions = dc.args.get('num_executions')
                        num_executions = int(num_executions)
                        if num_executions == 0:
                            num_executions = None  # repeat forever
                        elif num_executions < 0:
                            raise CommandArgumentError(self.device, dc.command,
                                                       'num_executions',
                                                       "must be >= 0")
                    except ValueError:
                        raise CommandArgumentError(self.device, dc.command,
                                                   'num_executions',
                                                   "must be integer")
                    try:
                        execute_immediately = dc.args.get('execute_immediately')
                        execute_immediately = bool(execute_immediately)
                    except ValueError:
                        raise CommandArgumentError(self.device, dc.command,
                                                   'execute_immediately',
                                                   "must be Boolean")
                    repeat_params = RepeatParams(
                        name=name,
                        interval=interval,
                        num_executions=num_executions,
                        execute_immediately=execute_immediately)
                else:
                    repeat_cmds.append(dc)
                repeat_depth += 1
            # Exit this mode unless the exit is in a nested repeat mode
            elif dc.device is None and dc.command == 'exit_repeat_mode':
                repeat_depth -= 1
                # Set the commands for repeated execution
                if repeat_depth == 0:
                    timer = {'interval': repeat_params.interval,
                             'num_executions': repeat_params.num_executions,
                             'execute_immediately': repeat_params.execute_immediately,
                             'command_list': repeat_cmds}
                    timer['passed'] = timer['execute_immediately']
                    self._timers[repeat_params.name] = timer

                    def timer_fn(timer):
                        def start_timer():
                            timer['passed'] = True
                            num_executions = timer['num_executions']
                            if num_executions is None or num_executions > 1:
                                threading.Timer(timer['interval'],
                                                start_timer).start()
                        return start_timer

                    start_timer = timer_fn(timer)
                    threading.Timer(timer['interval'], start_timer).start()
                    repeat_cmds = []
                else: repeat_cmds.append(dc)
            # Add the command to the list for repeated execution
            elif repeat_depth > 0:
                repeat_cmds.append(dc)
            # Execute the command
            else:
                try:
                    device_controller = self._device_controllers[dc.device]
                except KeyError:
                    raise DeviceNameError(dc.device)
                device_update = device_controller.execute_command(dc)
                # Add device update to rest of the updates
                if device_update is not None:
                    self._updates.append(device_update)

    def execute_command(self, command):
        cmd = command.command
        update = None
        if cmd == 'write_update':
            for arg in ['variable', 'value']:
                try:
                    value = command.args[arg]
                    if value is None:
                        raise KeyError
                except KeyError:
                    raise CommandArgumentError(self.device, cmd, arg,
                                               "missing argument")
            update = self.write_update(cmd.args['variable'], cmd.args['value'])
        elif cmd == 'set_alert':
            # Confirm that exactly the required arguments are present
            all_args = ['name', 'device', 'variable', 'lower_limit',
                        'upper_limit']
            for arg in all_args:
                if arg not in command.args:
                    raise CommandArgumentError(self.device, cmd, arg,
                                               "missing argument")
                if command.args[arg] is None:
                    raise CommandArgumentError(self.device, cmd, arg,
                                               "unspecified argument")
            invalid_args = set(list(command.args)) - set(all_args)
            for arg in invalid_args:
                raise CommandArgumentError(self.device, cmd, arg,
                                           "invalid argument")
            # Confirm limits have the correct type
            if arg in ['lower_limit', 'upper_limit']:
                try:
                    command.args[arg] = float(command.args[arg])
                except ValueError:
                    raise CommandArgumentError(self.device, cmd, arg,
                                               "argument must be float")
            self._managers[command.args['name']] = AlertManager(**command.args)
            update = self.write_update('alert_set', command.args['name'])
        elif cmd in ['unset_alert']:
            try:
                name = command.args['name']
            except KeyError:
                raise CommandArgumentError(self.device, cmd, 'name',
                                           "missing argument")
            if name is None:
                raise CommandArgumentError(self.device, cmd, 'name',
                                           "unspecified argument")
            try:
                del self._managers[name]
            except KeyError:
                raise CommandExecutionError(self.device, cmd,
                                            "no manager named {}".format(name))
            update = self.write_update('manager_unset', name)
        elif cmd == 'issue_alert':
            update_args = ['name', 'value', 'value_id', 'lower_limit',
                           'upper_limit']
            for arg in update_args + ['unit']:
                if arg not in command.args:
                    raise CommandArgumentError(self.device, cmd, arg,
                                               "missing argument")
                if command.args[arg] is None:
                    raise CommandArgumentError(self.device, cmd, arg,
                                               "unspecified argument")
            values = {arg: command.args[arg] for arg in update_args}
            update = self.write_multiple_update('alert', values,
                                                command.args['unit'])
        elif cmd == 'clear_alert':
            if 'name' not in command.args:
                raise CommandArgumentError(self.device, cmd, 'name',
                                           "missing argument")
            if command.args['name'] is None:
                raise CommandArgumentError(self.device, cmd, 'name',
                                           "unspecified argument")
            update = self.write_update('alert_clear', command.args['name'])
        elif cmd == 'modify_repeating_command':
            for arg in ['name', 'arg', 'value']:
                if arg not in command.args:
                    raise CommandArgumentError(self.device, cmd, arg,
                                               "missing argument")
            try:
                timer = self._timers[command.args['name']]
            except KeyError:
                raise CommandArgumentError(self.device, cmd, 'name',
                                           "no repeating command: {}".format(
                                               command.args['name']))
            try:
                timer[command.args['arg']] = command.args['value']
            except KeyError:
                raise CommandArgumentError(self.device, cmd, 'arg',
                                           "no repeating command "
                                           "argument: {}".format(
                                               command.args['arg']))
        elif cmd == 'stop_repeating_command':
            for arg in ['name', 'no_command_is_error']:
                if arg not in command.args:
                    raise CommandArgumentError(self.device, cmd, arg,
                                               "missing argument")
            try:
                del self._timers[command.args['name']]
            except KeyError:
                if command.args['no_command_is_error']:
                    raise CommandArgumentError(self.device, cmd, arg,
                                               "no repeating command: "
                                               "{}".format(
                                                   command.args['name']))
        else:
            raise CommandNameError(self.device, cmd)

        return update


    def _execute_timed_commands(self):
        for timer in self._timers.values():
            if (timer['num_executions'] is not None
                    and timer['num_executions'] <= 0):
                continue
            if timer['passed']:
                timer['passed'] = False
                if timer['num_executions'] is not None:
                    timer['num_executions'] -= 1
                self._execute_device_command_list(timer['command_list'])


    def _execute_user_command(self, user_command):
        if user_command is not None:
            device_command_list = self._parse_user_command(user_command)
            self._execute_device_command_list(device_command_list)


    def run_server(self):
        """Runs the server main loop"""

        while True:
            try:
                # Send an update to the user and receive a command (if any)
                user_command = self._user_handler.communicate_user(self._updates)
                self._updates = []
                self._execute_user_command(user_command)
                # Process any commands on an automatic timer
                self._execute_timed_commands()
                # Inspect updates by managers (e.g. check alerts)
                for manager in self._managers.values():
                    for update in self._updates:
                        manager_command = manager.process_update(update)
                        self._execute_user_command(manager_command)
            except CameraControlError as err:
                update = Update(err.device, 'ERROR')
                update.add_value(err.message)
                self._updates.append(update)
                print('---')
                traceback.print_exc()
                print('---')

def main():
    """Start the server when run from the command line"""

    parser = argparse.ArgumentParser()
    parser.add_argument('config_file', help='Path to slow control config file')
    parser.add_argument('commands_file',
                        help='Path to slow control commands file')
    parser.add_argument('--mock', action='store_true',
                        help='Run server with mock devices for testing')
    args = parser.parse_args()

    with open(args.config_file, 'r') as config_file:
        config = yaml.safe_load(config_file)

    with open(args.commands_file, 'r') as commands_file:
        user_commands = yaml.safe_load(commands_file)

    ctrlmod = mockctrl if args.mock else ctrl

    devices = {
#       'server': ServerController --> automatically included as self
        'fan': ctrlmod.FanController,
        'fee_temperature': ctrlmod.FEETemperatureController,
        'network': ctrlmod.NetworkController,
        'power': ctrlmod.PowerController,
        'chiller': ctrlmod.ChillerController,
        'shutter': ctrlmod.ShutterController,
        'target': ctrlmod.TargetController,
        'backplane': ctrlmod.BackplaneController,
        }
    server = ServerController('server', config, user_commands, devices)

    server.run_server()

if __name__ == "__main__":
    main()
