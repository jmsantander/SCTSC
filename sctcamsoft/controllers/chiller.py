__all__ = ['ChillerController',]

import xml.etree.ElementTree as ET

import requests

from sctcamsoft.camera_control_classes import DeviceController
from sctcamsoft.camera_control_classes import (CommunicationError,
                                               ConfigurationError)

class ChillerController(DeviceController):

    def __init__(self, device, config):
        super().__init__(device, config)
        try:
            self._state_url = "http://{}/state.xml".format(config['address'])
            self._pressure_analog_sensor_num = config['pressure_analog_sensor_num']
            self._temp_sensor_num = config['temp_sensor_num']
        except KeyError as err:
            # Raise the missing config parameter as an error, including
            # the key that generated it (err.args[0])
            raise ConfigurationError(self.device,
                                    err.args[0],
                                    "Missing configuration parameter")
        self._pressure = 0
        self._temperature = 0

    def _get_chiller_state(self):
        try:
            res = requests.get(self._state_url)
        except requests.exceptions.ConnectionError as err:
            raise CommunicationError(self.device) from err

        if not res:
            raise CommunicationError(self.device)

        root = ET.fromstring(res.text)
        for child in root:
            # TODO: Does any math need to be done do get the proper units?
            if child.tag == "an{}state".format(self._pressure_analog_sensor_num):
                self._pressure = child.text
                self._pressure=str(float(self._pressure)*25.0)    # convert voltage (0-5V to  pressure 0-100 PSI in the manual, but the actual factor is to be determind )
            elif child.tag == "sensor{}temp".format(self._temp_sensor_num):
                self._temperature = child.text    # measuring the west cabinet temperature

    def execute_command(self, command):
        cmd = command.command

        update = None
        # TODO: Again, are these units correct?
        if cmd == "read_pressure":
            self._get_chiller_state()
            update = self.write_update('pressure', self._pressure, 'kPa')
            update=update
        elif cmd == "read_temperature":
            self._get_chiller_state()
            update = self.write_update('temperature', self._temperature, 'C')

        return update
