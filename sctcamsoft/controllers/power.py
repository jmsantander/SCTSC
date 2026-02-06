# Control for camera power supply

__all__ = ['PowerController',]

import subprocess

from sctcamsoft.camera_control_classes import DeviceController
from sctcamsoft.camera_control_classes import (CommandExecutionError,
                                               CommandNameError,
                                               CommunicationError,
                                               ConfigurationError,
                                               VariableError)

class PowerController(DeviceController):

    def __init__(self, device, config):
        super().__init__(device, config)
        try:
            self._ip_address = config['ip_address']
        except KeyError:
            raise ConfigurationError(self.device, 'ip_address',
                                     "missing configuration parameter")
        try:
            self._mib_list_path = config['mib_list_path']
        except KeyError:
            raise ConfigurationError(self.device, 'mib_list_path',
                                     "missing configuration parameter")

    def _snmp_cmd(self, snmpcmd, parameters):
        snmp_command = (snmpcmd + ' -v 2c -m ' + self._mib_list_path +
                        ' -c guru ' + self._ip_address + ' ' + parameters)
        return snmp_command.split()

    def _cmd_to_snmp(self, cmd):
        cmd_to_snmp = {
            'turn_on_main_switch': [
                self._snmp_cmd('snmpset', 'sysMainSwitch.0 i 1'),
                ['sleep', '2']],
            'turn_off_main_switch': [
                self._snmp_cmd('snmpset', 'sysMainSwitch.0 i 0'),
                ['sleep', '2']],
            'start_supply': [
                self._snmp_cmd('snmpset', 'outputVoltage.u0 Float: 70.0'),
                self._snmp_cmd('snmpset', 'outputSwitch.u0 i 1')],
            'stop_supply': [
                self._snmp_cmd('snmpset', 'outputSwitch.u0 i 0')],
            'start_HV': [
                self._snmp_cmd('snmpset', 'outputVoltage.u4 Float: 70.0'),
                self._snmp_cmd('snmpset', 'outputSwitch.u4 i 1')],
            'stop_HV': [
                self._snmp_cmd('snmpset', 'outputSwitch.u4 i 0')],
            'read_supply_current': [
                self._snmp_cmd('snmpwalk', 'outputMeasurementCurrent.u0')],
            'read_supply_nominal_voltage': [
                self._snmp_cmd('snmpwalk', 'outputVoltage.u0')],
            'read_supply_measured_voltage': [
                self._snmp_cmd('snmpwalk', 'outputMeasurementSenseVoltage.u0')],
            'read_HV_current': [
                self._snmp_cmd('snmpwalk', 'outputMeasurementCurrent.u4')],
            'read_HV_nominal_voltage': [
                self._snmp_cmd('snmpwalk', 'outputVoltage.u4')],
            'read_HV_measured_voltage': [
                self._snmp_cmd('snmpwalk', 'outputMeasurementSenseVoltage.u4')]
            }
        try:
            snmp_commands = cmd_to_snmp[cmd]
        except KeyError:
            raise CommandNameError(self.device, cmd)
        return snmp_commands

    def execute_command(self, command):
        cmd = command.command
        snmp_commands = self._cmd_to_snmp(cmd)
        command_variable_and_unit = {
            'read_supply_current': ('supply_current', 'A'),
            'read_supply_nominal_voltage': ('supply_nominal_voltage', 'V'),
            'read_supply_measured_voltage': ('supply_measured_voltage', 'V'),
            'read_HV_current': ('HV_current', 'A'),
            'read_HV_nominal_voltage': ('HV_nominal_voltage', 'V'),
            'read_HV_measured_voltage': ('HV_measured_voltage', 'V')
            }
        try:
            if cmd not in command_variable_and_unit:
                for snmp_command in snmp_commands:
                    subprocess.run(snmp_command)
                return None
            variable, unit = command_variable_and_unit[cmd]
            snmp_command = snmp_commands[0]
            completed_process = subprocess.run(snmp_command, check=True,
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.STDOUT,
                                               encoding='ascii')
            # Parse output string to get numerical value only
            try:
                value = completed_process.stdout.split()[-2]
                if value == 'this':
                    # "No Such Instance currently exists at this OID"
                    raise CommandExecutionError(self.device, cmd,
                                                "power unit unavailable")
                value = float(value)
            except IndexError:
                raise CommandExecutionError(self.device, cmd,
                                            "invalid response to command, "
                                            "received: {}".format(
                                                completed_process.stdout))
            except ValueError:
                raise VariableError(self.device, variable, value,
                                    "must be float")
            update = self.write_update(variable, value, unit)
            return update
        except OSError as err:
            raise CommunicationError(self.device) from err
