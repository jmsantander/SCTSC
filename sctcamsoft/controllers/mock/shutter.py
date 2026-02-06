__all__ = ['ShutterController', ]

import requests

from sctcamsoft.camera_control_classes import *
import random


class ShutterController(DeviceController):

    def __init__(self, device, config):
        self.device = device


    def execute_command(self, command):
        self._close_sensor = random.randint(0, 1)
        self._open_sensor = random.randint(0, 1)
        cmd = command.command
        update = None
        if cmd == "read_close_sensor":
            update = self.write_update('close_sensor', self._close_sensor)
        elif cmd == "read_open_sensor":
            update = self.write_update('open_sensor', self._open_sensor)
        return update
