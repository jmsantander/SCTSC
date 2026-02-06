__all__ = ['ChillerController',]

import requests

from sctcamsoft.camera_control_classes import *
from sctcamsoft.controllers.mock.random_signal import RandomSignal

class ChillerController(DeviceController):

    def __init__(self, device, config):
        self.device = device

        hw_state = config['mock']
        add_noise = hw_state['noisy_signal']
        self._pressure = RandomSignal(hw_state['pressure'], 0.7 if add_noise else 0)
        self._temperature = RandomSignal(hw_state['temperature'], 0.7 if add_noise else 0)

    def execute_command(self, command):
        cmd = command.command
        update = None
        if cmd == "read_pressure":
            update = self.write_update('pressure', self._pressure.read())
        elif cmd == "read_temperature":
            update = self.write_update('temperature', self._temperature.read())
        
        return update
