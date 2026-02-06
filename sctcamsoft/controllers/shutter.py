# WebRelay X-301: two relay output, not sure about which port is used in the pSCT, need to ask Dr. Kieda again.

# controlled or monitored  by sending GET requests  to an XML status page:

# state page: http://192.168.1.2/state.xml
# port: 80

# get info:
           #   GET http://172.17.3.7/state.xml HTTP/1.1

#The following is an html request header without the password:
           #  GET http://172.17.3.7/state.xml?relay1State=1&noReply=1 HTTP/1.1  # turn Output 1 On

# Q1: Dose Control Password is enabled on WebRelay-Dual?

__all__ = ['ShutterController',]

import xml.etree.ElementTree as ET

import requests

from sctcamsoft.camera_control_classes import DeviceController
from sctcamsoft.camera_control_classes import (CommunicationError,
                                               ConfigurationError)

class ShutterController(DeviceController):

    def __init__(self, device, config):
        super().__init__(device, config)
        try:
            self._state_url = "http://{}/state.xml".format(config['address'])
            self._close_sensor_num= config['close_sensor_num']
            self._open_sensor_num = config['open_sensor_num']
        except KeyError as err:
            # Raise the missing config parameter as an error, including
            # the key that generated it (err.args[0])
            raise ConfigurationError(self.device,
                                    err.args[0],
                                    "Missing configuration parameter")
        self._close_sensor = 0
        self._open_sensor = 0

    def _get_chiller_state(self):
        try:
            res = requests.get(self._state_url)
        except requests.exceptions.ConnectionError as err:
            raise CommunicationError(self.device) from err

        if not res:
            raise CommunicationError(self.device)

        root = ET.fromstring(res.text)
        for child in root:

            if child.tag == "input{}state".format(self._close_sensor_num):
                self._close_sensor = child.text
            elif child.tag == "input{}state".format(self._open_sensor_num):
                self._open_sensor = child.text

    def execute_command(self, command):
        cmd = command.command

        update = None

        if cmd == "read_close_sensor":
            self._get_chiller_state()
            update = self.write_update('close_sensor',  self._close_sensor, ' ')
        elif cmd == "read_open_sensor":
            self._get_chiller_state()
            update = self.write_update('open_sensor',  self._open_sensor , ' ')

        return update


