"""Device Manager for web-based slow control.

Manages device states and provides thread-safe access to device data.
"""

import threading
from datetime import datetime, timezone, timedelta
from collections import defaultdict

class DeviceManager:
    """Manages device states and subscriptions for the web interface."""
    
    def __init__(self, camera_comm, config, value_timeout=10):
        """Initialize device manager.
        
        Args:
            camera_comm: CameraComm instance for communication
            config: Configuration dictionary
            value_timeout: Seconds before a value is considered stale
        """
        self.camera_comm = camera_comm
        self.config = config
        self.value_timeout = timedelta(seconds=value_timeout)
        self.lock = threading.Lock()
        
        # Device data storage
        self._device_data = defaultdict(dict)
        self._device_updates = defaultdict(dict)
        
        # Device names corresponding to the PyQt controls
        self.devices = [
            'fan',
            'power',
            'module',
            'fee_temp',
            'network',
            'chiller',
            'backplane',
            'shutter',
            'target'
        ]
        
        # Register update handlers if camera_comm has the signal
        if hasattr(camera_comm, 'on_update'):
            camera_comm.on_update.connect(self._on_device_update)
    
    def _on_device_update(self, device_name, var_name, value):
        """Handle device variable update from camera."""
        with self.lock:
            if device_name not in self._device_data:
                self._device_data[device_name] = {}
            
            self._device_data[device_name][var_name] = value
            self._device_updates[device_name][var_name] = datetime.now(timezone.utc)
    
    def get_device_state(self, device_name):
        """Get current state of a device.
        
        Returns:
            Dictionary with device variables and their states,
            including whether values are expired.
        """
        with self.lock:
            if device_name not in self._device_data:
                return None
            
            now = datetime.now(timezone.utc)
            state = {
                'device_name': device_name,
                'variables': {},
                'timestamp': now.isoformat()
            }
            
            for var_name, value in self._device_data[device_name].items():
                update_time = self._device_updates[device_name].get(var_name)
                is_expired = False
                
                if update_time:
                    is_expired = now >= (update_time + self.value_timeout)
                
                state['variables'][var_name] = {
                    'value': value,
                    'expired': is_expired,
                    'updated': update_time.isoformat() if update_time else None
                }
            
            return state
    
    def get_all_device_states(self):
        """Get states of all devices.
        
        Returns:
            Dictionary mapping device names to their states.
        """
        states = {}
        for device_name in self.devices:
            state = self.get_device_state(device_name)
            if state:
                states[device_name] = state
        return states
    
    def send_command(self, command, **kwargs):
        """Send a command to the camera server.
        
        Args:
            command: Command string
            **kwargs: Command parameters
        """
        self.camera_comm.send_command(command, **kwargs)
