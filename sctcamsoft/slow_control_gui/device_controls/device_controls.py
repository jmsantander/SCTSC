from abc import ABC, abstractmethod

import time
import copy
from collections import namedtuple

from datetime import datetime, timezone, timedelta

from sctcamsoft.lib_gui.camera_handler import CameraHandler

class DeviceControls(ABC):
    """Abstract class representing a camera subsystem and associated GUI controls.

    This ABC should be extended by each camera subsystem (that is, each server 
    "device" with its own `device_name`). This class hides device-specific 
    communication and provides access methods to update information about that
    device. It permits a child implementation to author one method, `draw`,
    which uses all device information to update a set of GUI widgets. The `draw`
    method is called when the device's variables are changed, or when a
    variable has newly expired.

    DeviceControls maintains an "expired" flag for each variable produced by
    the device. If the variable's value has not been updated by the server 
    within a configurable number of seconds, the flag is asserted. If it has, 
    it is deasserted.  tracks the time of the most recent update for each 
    variable and maintains an "expired" state. If a variable changes from
    unexpired to expired, the `draw` method is called again so the child 
    implementation can use the new expiration state.
    """

    def __init__(self, device_name, monitored_alerts, 
                 widgets, value_timeout, update_signal, 
                 timer_signal, send_command_slot):

        self.device_name = device_name
        self.widgets = widgets

        self.camera = CameraHandler(
            [device_name], monitored_alerts,
            update_signal, send_command_slot)
        self.camera.on_update.connect(self._on_draw)
        self.camera.on_new_alert.connect(self._on_draw)
        self.camera.on_alert_clear.connect(self._on_draw)
        
        self.value_timeout = timedelta(seconds=value_timeout)
        timer_signal.connect(self._on_timer)
    
        self._on_draw()

    def _on_timer(self):
        if (self._needs_redraw()):
            self._on_draw()

    def _needs_redraw(self, now = None):
        """Check to see if the cache has changed or vars have expired since last check"""

        if (now == None):
            now = datetime.now(timezone.utc)

        current_cache = self.camera.get_cache()

        if (self._last_cache != current_cache):
            return True

        # Check to see if any values have expired since the last drawing -
        # that is, if they were not expired at last drawing but are now
        device_vars = current_cache.get_device_var_names(self.device_name)
        for var_name in device_vars:
            # Extract the current value of this device var, and compute
            # whether or not it has expired based on the current time
            var_update = current_cache.get_var_update(self.device_name, var_name)
            var_is_expired = now >= (var_update.time_recieved + self.value_timeout)
            
            # Extract the value of the device var when the controls were
            # last drawn. Compute whether or not the value was expired then.
            var_update_last = self._last_cache.get_var_update(self.device_name, var_name)
            var_was_expired = self._last_draw_time >= (var_update_last.time_recieved + self.value_timeout)

            # If the value has changed since last drawing, or if the
            # value's expiry status has changed, we need to redraw
            if (var_update != var_update_last or var_is_expired != var_was_expired): 
                return True

        return False

    def _on_draw(self):
        # Store the update cache so current values can be used 
        # to determine if redrawings are needed later
        self._last_cache = copy.copy(self.camera.get_cache())
        self._last_draw_time  = datetime.now(timezone.utc)

        self.draw()

    def is_expired(self, var_name):
        """Check is a device variable's value is expired.
        
        Returns "true" if a variable update has not been recieved within the 
        last `value_timeout` seconds.
        """

        update = self.camera.get_cache().get_var_update(self.device_name, var_name)
        if (update is not None):
            return (datetime.now(timezone.utc) >= 
                    update.time_recieved + self.value_timeout)
        else:
            return None
        
    def get_var(self, var_name):
        """Access a VariableUpdate by name.
        
        Returns:
            The most recent VariableUpdate tuple associated with this device
            and with a matching name, or None if no matching tuples are found.
        """

        cache = self.camera.get_cache()
        return cache.get_update(self.device_name, var_name)

    def get_val(self, var_name):
        """Convienence method for accessing `value` field of a VariableUpdate.
        
        Returns:
            The `value` field of the most recent VariableUpdate tuple associated
            with this device and with the matching name, or None if a matching
            tuple is not found.
        """
        cache = self.camera.get_cache()
        return cache.get_val(self.device_name, var_name)

    def get_asserted_alerts(self):
        """Get a list of monitored AlertUpdates that are currently asserted."""

        return self.camera.get_cache().get_current_alerts()

    def get_alert_if_asserted(self, alert_name):
        """Get an AlertUpdate by name, if it is currently asserted. Else None."""

        return self.camera.get_cache().get_alert(alert_name)

    def send_command(self, cmd):
        """Send a command to the server."""

        self.camera.send_command(cmd)

    @abstractmethod
    def draw(self):
        """Update GUI widgets according to current device state.
        
        This method must be implemented by the child implementation. It will be
        called whenever a variable or variable expiry status has changed and
        should update all applicable widgets according to the device's current
        state. That state is accessible from the draw method through 
        `is_expired()`, `get_var()`, `get_asserted_alerts()`, etc.
        """
        
        raise NotImplementedError()
