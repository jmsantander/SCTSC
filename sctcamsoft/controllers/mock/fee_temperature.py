# Slow control for module temperatures
# Temperatures can only be read during data taking,
# so they are written to a text file
# that this controller reads from

# Two commands are available:
# get_last_run_num: Return run number of most recent temperature file
# read_temperature: Return temperatures of all FEEs by module number

__all__ = ['FEETemperatureController',]

import glob
import os

import numpy as np

from sctcamsoft.camera_control_classes import *
from sctcamsoft.controllers.mock.random_signal import RandomSignal

class FEETemperatureController(DeviceController):

    def __init__(self, device, config):
        self.device = device
        self.file_prefix = 'temperatureFile_run'
        try:
            self.dir = config['temperature_dir']
        except KeyError:
            raise ConfigurationError(self.device, 'temperature_dir',
                    "missing configuration parameter")
        self.run_num = config['mock']['run_num']
        self._temperature_sig = RandomSignal(config['mock']['temperature_mean'],
                                             config['mock']['temperature_std'])
        self._module_ids = config['mock']['module_ids']

    def execute_command(self, command):
        cmd = command.command
        update = None
        if cmd == "get_last_run_num":
            update = self.write_update('last_run_num', self.run_num)
        elif cmd == "read_temperature":
            run_num = command.args.get('run_num')
            if run_num is not None:
                try:
                    run_num = int(run_num)
                except ValueError:
                    raise CommandArgumentError(self.device, cmd, 'run_num',
                                               "invalid run number")
            temperatures = {}
            for fee_num in self._module_ids:
                temperatures[fee_num] = self._temperature_sig.read()
            update = self.write_multiple_update('temperature', temperatures,
                                                unit='C')
        else:
            raise CommandNameError(self.device, cmd)
        return update
