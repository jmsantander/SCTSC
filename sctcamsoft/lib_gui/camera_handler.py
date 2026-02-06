from datetime import datetime, timezone
from collections import namedtuple
from typing import NamedTuple, Any

from PyQt5.QtCore import QObject, pyqtSignal

import logging


class VariableUpdate(NamedTuple):
    """A high-level container for variable update information."""

    device: str
    variable: str
    value: Any
    units: str
    time_sent: datetime  # aware, UTC
    time_recieved: datetime  # aware, UTC
    has_multiple_values: bool


class IdentifiedValue(NamedTuple):
    """A high-level container for a 2-tuple-like structure."""

    identifier: str
    value: str

    def __repr__(self):
        return f'{self.identifier}:{self.value}'


class AlertUpdate(NamedTuple):
    """A high-level container for alert message information."""

    name: str
    value: str
    value_id: str
    lower_limit: str
    upper_limit: str
    units: str
    time_sent: datetime  # aware, UTC
    time_recieved: datetime  # aware, UTC


class ErrorUpdate(NamedTuple):
    """A high-level container for error message information."""

    device: str
    error: str
    time_sent: datetime  # aware, UTC
    time_recieved: datetime  # aware, UTC


class CameraUpdateCache():
    """A container to store updates from the camera.

    Instances of CameraUpdateCache can be compared for equality,
    and can be shared between objects; entitites in the private
    dictionaries are kept private - only views, copies, and immutable 
    values are returned from public methods.
    """

    def __init__(self):
        super().__init__()

        self._cached_vars = {}
        self._cached_alerts = {}

    def save_var_update(self, update):
        """Saves a VariableUpdate to the cache.

        Extracts 'device' and 'variable' from the update 
        tuple to use as keys for later recall.
        
        Args:
            update: The VarUpdate tuple to save."""

        # _cached_vars is a nested dict. Ensure the inner dict is created.
        if (update.device not in self._cached_vars):
            self._cached_vars[update.device] = {}

        self._cached_vars[update.device][update.variable] = update

    def get_device_var_names(self, device):
        """Get a list of a device's variable names in the cache."""

        if (device not in self._cached_vars):
            return []
        return list(self._cached_vars[device].keys())

    def get_var_update(self, device, var_name):
        """Provides access to a 'VariableUpdate' tuple.
        
        Args:
            device: A string identifier for a specific Camera server subsystem.
            var_name: A string identifier for a specific variable produced
                by the subsystem.

        Returns:
            The latest VarUpdate received that is associated with this 
            device and variable name.
        """

        if (device in self._cached_vars
                and var_name in self._cached_vars[device]):
            return self._cached_vars[device][var_name]
        else:
            return None

    def get_val(self, device, var_name):
        """Convience method that extracts an VariableUpdate's value."""

        update = self.get_var_update(device, var_name)
        if update is not None:
            return update.value
        else:
            return None

    def save_new_alert(self, alert_update):
        """Saves a "new alert" update to the cache"""

        self._cached_alerts[alert_update.name] = alert_update

    def get_current_alerts(self, filter_func=lambda x: True):
        """Retrieves currently asserted alerts from the cache.

        Retrieves a list of AlertUpdate tuples corresponding to all "new alert"
        messages recieved from the camera server. Optionally, filter the
        list before returning it.

        Args:
            filter_func: Optional. Accepts a filter function that must return
                true if its parameter (an AlertUpdate) should be included in 
                the retrieved list.

        Returns:
            A list of optionally-filtered AlertUpdate tuples.
        """
        
        return [alert for alert
                in self._cached_alerts.values()
                if filter_func(alert)]

    def get_alert(self, alert_name):
        """Retrieves a specific alert from the cache.

        Args:
            alert_name: The string name of an alert.

        Returns:
            The alert with matching name, or None if that alert is not
            currently in the list of asserted alerts.
        """

        try: 
            return self._cached_alerts[alert_name]
        except KeyError:
            return None

    def clear_alert(self, alert_name):
        """Remove an alert from the cache

        This updates the cache that an alert has been cleared.

        Args:
            alert_name: The string name of the alert to clear.
        """

        del self._cached_alerts[alert_name]

    def __eq__(self, other):
        if not isinstance(other, CameraUpdateCache):
            raise NotImplementedError

        return (self._cached_vars == other._cached_vars and
                self._cached_alerts == other._cached_alerts)


class CameraHandler(QObject):
    """A high-level interface to the data sent to and recieved from the server.

    CameraHandler is a worker object that accepts protobuf Update objects via 
    the `update_signal` passed to the constructor. Each protobuf Update is then 
    categorized as a VariableUpdate, AlertUpdate, or ErrorUpdate, and the 
    protobuf object's fields are used to populate an instance of whichever 
    namedtuple is applicable.

    Any number or value measured or tracked by the server (i.e. fan voltage, 
    the ID of the last run, or the current state of each camera module) is
    converted to a VariableUpdate object. Each measured value is uniquely 
    identified by its `device` and `variable` fields, where `device` is the 
    camera subsystem that produced the value, and `variable` is the name of the 
    value. That is, if the server wanted to send a new version of the same value
    at a later time, it will broadcast a new Update with the same `device` and
    `variable` fields, but a new `value` field.

    Thus, all information available about the camera can be thought of as a 
    simple list of values indexed by their `device` and `variable` fields. Each
    value is captured in a ValueUpdate object, and the collection of values is
    stored in a CameraUpdateCache object. When a new value is recieved, an 
    `on_update` signal is emitted with the new VarUpdate and the updated
    CameraUpdateCache.

    The CameraUpdateCache also catalogs alerts broadcast from the server. When 
    CameraHandler recieves an alert update, it creates an AlertUpdate tuple
    and adds it to the cache. If it subsequently receives an alert_clear 
    update, it removes the alert from the cache. When an alert's state is 
    updated, an `on_new_alert` or `on_alert_clear` signal is emitted with the
    new tuple and the updated cache.

    Finally, when CameraHandler receives error updates from the server, it 
    creates an ErrorUpdate tuple and immeadiately emits an `on_error` 
    signal with the new tuple. It does not store errors in the cache.

    The CameraHandler object also has a send_command function that allows 
    clients to transmit commands to the server.


    A brief note on the datetime objects throughout this module; this class 
    assumes that the server sends UTC timestamps. This timezone information 
    is lost by the protobuf library, and thus "naive" datetimes are recieved 
    from the server. The assumed UTC timezone is added (with the .replace 
    method) to all timestamps from the server.
    """

    on_update = pyqtSignal(VariableUpdate, CameraUpdateCache)
    on_new_alert = pyqtSignal(AlertUpdate, CameraUpdateCache)
    on_alert_clear = pyqtSignal(object, CameraUpdateCache)
    on_error = pyqtSignal(object)

    _send_command = pyqtSignal(str)


    def __init__(self, monitored_devices, monitored_alerts,
                 update_signal, send_command_slot):
        """Create the CameraHandler object.

        Args:
            monitored_devices: A list of strings each holding the identifier
                of a Camera subsystem that this CameraHandler should react to.
                An empty list will force monitoring of all subystems.
            monitored_alerts: A list of strings each holding the identifier of
                an alert the server may generate that this CameraHandler should
                react to. An empty list will force monitoring of all alerts.
            update_signal: A pyqtSignal that will be emitted when the server
                sends a new update. The signal should be emitted with the 
                recieved protobuf Update object.
            send_command_slot: A slot (or other simple function) that accepts
                a command as a text string and sends the string command
                to the server when called. The CameraHandler will use this
                function whenever the CameraHandler's user calls send_command.
        """
        super().__init__()
        self.monitored_devices = monitored_devices
        self.all_devices = len(self.monitored_devices) == 0
        self.monitored_alerts = monitored_alerts
        self.all_alerts = len(self.monitored_alerts) == 0
        update_signal.connect(self._on_update)

        self._send_command.connect(send_command_slot)

        self._cam_update_cache = CameraUpdateCache()

    def _on_update(self, up):
        # Interpret an issued alert
        if (up.device == 'server' and up.variable == 'alert'):
            # Convert to a map for access-by-key
            values = {x.id: x.value for x in up.values}

            # Filter based on the alerts we're monitoring
            if (self.all_alerts or (values['name'] in self.monitored_alerts)):

                # Create the alert update tuple
                alert_up = AlertUpdate(
                    values['name'],
                    values['value'],
                    values['value_id'],
                    values['lower_limit'],
                    values['upper_limit'],
                    up.unit,
                    self._pb3_timestamp_to_utc_datetime(up.timestamp),
                    datetime.now(timezone.utc)
                )

                # Save it to the cache and notify listeners
                self._cam_update_cache.save_new_alert(alert_up)
                self.on_new_alert.emit(alert_up, self._cam_update_cache)

        # Interpret an alert clear
        elif (up.device == 'server' and up.variable == 'alert_clear'):
            alert_name = up.values[0].value
            if (self.all_alerts or alert_name in self.monitored_alerts):
                # Grab the alert tuple from the cache
                alert_up = self._cam_update_cache.get_alert(alert_name)
                if (alert_up != None):
                    # Remove the alert from the cache
                    self._cam_update_cache.clear_alert(alert_name)
                # Notify listeners of the cleared alert
                self.on_alert_clear.emit(alert_up, self._cam_update_cache)

        elif (up.variable == 'ERROR' and 
                (self.all_devices or up.device in self.monitored_devices)):
            # Create the error object and call the listener
            error_up = ErrorUpdate(
                up.device,
                up.values[0].value,
                self._pb3_timestamp_to_utc_datetime(up.timestamp),  # Time sent
                datetime.now(timezone.utc),  # Time recieved
            )
            self.on_error.emit(error_up)

        elif (self.all_devices or (up.device in self.monitored_devices)):
            # If this update contains many values, parse
            # them all before creating the VariableUpdate tuple.
            if not up.values:
                value = None
                has_multiple_values = False
            else:
                value = up.values[0]
                has_multiple_values = False
                if value.id:
                    value = [IdentifiedValue(x.id, x.value)
                             for x in up.values]
                    has_multiple_values = True
                else:
                    value = up.values[0].value
                    has_multiple_values = False

            # Create the VariableUpdate, cache it, and emit an "updated" signal
            var_update = VariableUpdate(
                up.device,
                up.variable,
                value,
                up.unit,
                self._pb3_timestamp_to_utc_datetime(up.timestamp),  # Time sent
                datetime.now(timezone.utc),  # Time recieved
                has_multiple_values
            )
            self._cam_update_cache.save_var_update(var_update)
            self.on_update.emit(var_update, self._cam_update_cache)

    def get_cache(self):
        """Access the CameraUpdateCache maintained by this CameraHandler."""
        return self._cam_update_cache

    def send_command(self, command_string):
        """Send a command to the server.
        
        Args:
            command_string: The command to send."""

        self._send_command.emit(command_string)

    def _pb3_timestamp_to_utc_datetime(self, timestamp):
        """Adds timezone-awareness to naive protobuff timestamps."""

        naive_datetime = timestamp.ToDatetime()
        utc_datetime = naive_datetime.replace(tzinfo=timezone.utc)
        return utc_datetime
