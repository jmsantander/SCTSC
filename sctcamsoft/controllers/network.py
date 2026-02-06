# Control for camera networking

__all__ = ['NetworkController',]

from getpass import getpass
import os
import subprocess

import pandas as pd

from sctcamsoft.camera_control_classes import DeviceController
from sctcamsoft.camera_control_classes import (
    CommandArgumentError, CommandNameError, ConfigurationError)

class NetworkController(DeviceController):

    def __init__(self, device, config):
        super().__init__(device, config)
        sudo_password = getpass()
        # Reformat for passing to subprocess
        self._password = "{}\n".format(sudo_password).encode()
        try:
            # Load dictionary of DACQ board: dictionary of DACQ config
            self._dacq_boards = config['dacq_boards']
            try:
                for board, network_dict in self._dacq_boards.items():
                    for key in ['ip_address', 'base_mac_address']:
                        if key not in network_dict:
                            raise ConfigurationError(self.device, 'dacq_boards',
                                "{} not specified for board {}".format(key,
                                                                       board))
            except AttributeError:
                raise ConfigurationError(self.device, 'dacq_boards',
                    "must be a dictionary of DACQ board: DACQ config")
            except TypeError:
                raise ConfigurationError(self.device, 'dacq_boards',
                    "DACQ config must be a dictionary")
            # Load FEE configuration
            try:
                fee_config_file = config['fee_configuration']
                self._fee_config = pd.read_csv(fee_config_file)
            except FileNotFoundError as err:
                raise ConfigurationError(self.device, 'fee_configuration',
                                         "file not found") from err
            # Load FPM configuration
            try:
                fpm_config_file = config['fpm_configuration']
                self._fpm_config = pd.read_csv(fpm_config_file)
            except FileNotFoundError as err:
                raise ConfigurationError(self.device, 'fpm_configuration',
                                         "file not found") from err
            # Load path to authorized keys file
            self._authorized_keys = config['authorized_keys_file']
            if not os.path.isfile(self._authorized_keys):
                raise ConfigurationError(self.device, 'authorized_keys_file',
                                         "file not found")
            # Load timeout parameter for checking interfaces
            try:
                self._timeout = int(config['timeout'])
            except ValueError:
                raise ConfigurationError(self.device, 'timeout',
                                         "must be an integer")
        except KeyError as err:
            raise ConfigurationError(self.device, err.args[0],
                                     "missing configuration parameter")

    def _check_interface_activity(self, interface):
        tcpdump_command = ("sudo -S timeout {}".format(self._timeout)
                           + " tcpdump -i {}".format(interface)
                           + " 2>&1 | tail -2 | head -1 | awk '{print $1}'")
        # Return number of packets send over interface within timeout
        proc = subprocess.run(tcpdump_command, input=self._password,
                              shell=True, capture_output=True)
        try:
            num_packets = int(proc.stdout.decode().strip())
        except ValueError:
            # tcpdump returned an error -> interface not connected
            num_packets = -1
        update = self.write_update(interface, num_packets)
        return update

    def _add_arp_entry(self, ip_address, mac_address):
        arp_command = "sudo -S arp -s {} {}".format(ip_address, mac_address)
        proc = subprocess.run(arp_command, input=self._password, shell=True)
        return proc.returncode

    def _set_ip_addresses(self):
        return_codes = []
        for ip_address, mac_address in zip(self._fee_config.ip_address,
                                           self._fee_config.mac_address):
            return_codes.append(self._add_arp_entry(ip_address, mac_address))
        status = 'failure' if any(return_codes) else 'success'
        update = self.write_update('camera_server_module_addresses', status)
        return update

    def _write_dacq_script(self, dacq_board, base_mac_address):
        script = 'set_target_module_addresses.sh'
        mac_start, mac_end_base = base_mac_address.rsplit(':', 1)
        mac_end_base = int(mac_end_base, 16)  # Convert hex string to number
        with open(script, 'w') as scriptfile:
            for module_id, mac_address, module_dacq_board in zip(
                    self._fee_config.module_id, self._fee_config.mac_address,
                    self._fee_config.dacq_board):
                if module_dacq_board != dacq_board:
                    continue
                # Associate the MAC address of each module with its slot
                # so that the computer disregards the switch
                # and communicates directly with the module
                loc = (self._fpm_config.module_id == module_id)
                wr_slot = self._fpm_config.white_rabbit_position.loc[loc].values[0]
                scriptfile.write("/wr/bin/rtu_stat add {} {} 0 0\n".format(
                    mac_address, wr_slot))
                # Construct MAC address for white rabbit slot in DACQ board
                wr_mac_end = mac_end_base + wr_slot
                wr_mac_end = "{:02x}".format(wr_mac_end)  # Convert to hex
                wr_mac_address = ':'.join([mac_start, wr_mac_end])
                # Assign MAC address for white rabbit slot in DACQ board
                scriptfile.write("/wr/bin/rtu_stat add {} {} 0 0\n".format(
                    wr_mac_address, wr_slot))
            # The DACQ boards remove ports from the rtu tables
            # if they are idle for 5 minutes. During data taking,
            # the module connections look idle to the DACQ boards.
            # Those lines kill the rtu process and start it back up
            # with the option to set the timeout to 2 hours (the maximum).
            # Data transfer will stop 2 hours after running DataPortPing().
            scriptfile.write("sleep 1\n")
            scriptfile.write("killall wrsw_rtud\n")
            scriptfile.write("sleep 1\n")
            scriptfile.write("/wr/bin/wrsw_rtud -t 7200 &")
        return script

    def _execute_dacq_script(self, ip_address, script):
        commands = ['sshpass -p "" scp -o StrictHostKeyChecking=no {} '
                    'root@{}:.ssh/'.format(self._authorized_keys, ip_address),
                    'sshpass -p "" scp -o StrictHostKeyChecking=no {} '
                    'root@{}:'.format(script, ip_address),
                    'sshpass -p "" ssh -o StrictHostKeyChecking=no root@{} '
                    '"/bin/bash /root/{}"'.format(ip_address, script)]
        for command in commands:
            proc = subprocess.run(command, shell=True)
            if proc.returncode:
                return 'failure'
        return 'success'

    def _set_dacq_module_addresses(self):
        for dacq_board, dacq_config in self._dacq_boards.items():
            script = self._write_dacq_script(dacq_board,
                                             dacq_config['base_mac_address'])
            res = self._execute_dacq_script(dacq_config['ip_address'], script)
            os.remove(script)
        update = self.write_update('dacq_module_addresses', res)
        return update

    def execute_command(self, command):
        cmd = command.command
        update = None
        if cmd == "check_interface_activity":
            try:
                interface = command.args['interface']
            except KeyError:
                raise CommandArgumentError(self.device, cmd, 'interface',
                                           "missing argument")
            if interface is None:
                raise CommandArgumentError(self.device, cmd, 'interface',
                                           "argument not specified")
            update = self._check_interface_activity(interface)
        elif cmd == "set_camera_server_module_addresses":
            update = self._set_ip_addresses()
        elif cmd == "set_dacq_module_addresses":
            update = self._set_dacq_module_addresses()
        else:
            raise CommandNameError(self.device, cmd)
        return update
