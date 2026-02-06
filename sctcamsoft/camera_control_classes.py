# Shared camera control classes and definitions

from abc import ABC, abstractmethod
from collections import namedtuple
from datetime import datetime

# args are values given by the user as input and are strings. The
# DeviceController shall cast them to another type if needed.
DeviceCommand = namedtuple('DeviceCommand', ['device', 'command', 'args'])

class CameraControlError(Exception):
    """Base class for custom exceptions in the camera control software"""

    def __init__(self, device, message):
        self.device = device
        self.message = message


class CommandArgumentError(CameraControlError):
    """Exception raised for invalid or missing command arguments"""

    def __init__(self, device, command, argument, message):
        super().__init__(device,
                         "{}: {}: {}".format(command, argument, message))
        self.command = command
        self.argument = argument


class CommandExecutionError(CameraControlError):
    """Exception raised for errors encountered during command execution"""

    def __init__(self, device, command, message):
        super().__init__(device, "{}: {}".format(command, message))
        self.command = command


class CommandNameError(CameraControlError):
    """Exception raised for invalid command names."""

    def __init__(self, device, command):
        super().__init__(device, "{}: invalid command name".format(command))
        self.command = command


class CommandSequenceError(CameraControlError):
    """Exception raised for calling a command in an unsupported order.
    For example, opening a connection when it is already open."""

    def __init__(self, device, command, message):
        super().__init__(device, "{}: {}".format(command, message))
        self.command = command


class CommunicationError(CameraControlError):
    """Exception raised for errors communicating with a device"""

    def __init__(self, device):
        super().__init__(device, "not connected")


class ConfigurationError(CameraControlError):
    """Exception raised for missing or invalid configuration parameters.
    Raise only during initialization."""

    def __init__(self, device, parameter, message):
        super().__init__(device, "{}: {}".format(parameter, message))
        self.parameter = parameter


class DeviceNameError(CameraControlError):
    """Exception raised for invalid device names."""

    def __init__(self, device):
        super().__init__(device, "invalid device")


class VariableError(CameraControlError):
    """Exception raised for invalid variables or values."""

    def __init__(self, device, variable, value, message):
        super().__init__(device, "{}: {}: {}".format(variable, value, message))
        self.variable = variable
        self.value = value


class Update():
    """User update internal representation, to be converted to protobuf"""

    def __init__(self, device, variable, unit=None, timestamp=None):

        self.device = device
        self.variable = variable
        self.unit = unit if unit is not None else ''
        if timestamp is None:
            timestamp = datetime.utcnow()
        self.timestamp = timestamp
        self.values = []

    def add_value(self, value, value_id=None):
        value_id = '' if value_id is None else str(value_id)
        self.values.append((value_id, value))

    def fill_protobuf(self, update_pb):
        update_pb.device = str(self.device)
        update_pb.variable = str(self.variable)
        update_pb.unit = str(self.unit)
        update_pb.timestamp.FromDatetime(self.timestamp)
        for value in self.values:
            value_pb = update_pb.values.add()
            value_pb.id = str(value[0])
            value_pb.value = str(value[1])


class DeviceController(ABC):
    """
    Execute commands and write updates for a particular device.

    A DeviceController must raise a CameraControlError for
    any exception encountered.
    """

    def __init__(self, device, config):
        """
        Device is a string representing the device name
        and config is a dictionary of configuration parameters.
        """
        self.device = device
        self.config = config

    @abstractmethod
    def execute_command(self, command):
        """
        Execute the specified command (of type DeviceCommand),
        returning either a dict containing update values or None.
        """
        raise NotImplementedError

    def write_update(self, variable, value=None, unit=None, timestamp=None):
        update = Update(self.device, variable, unit, timestamp)
        if value is not None:
            update.add_value(value)
        return update

    def write_multiple_update(self, variable, values, unit=None,
                              timestamp=None):
        update = Update(self.device, variable, unit, timestamp)
        for value_id, value in values.items():
            update.add_value(value, value_id)
        return update
