# Control for communication with the Backplane through the Raspberry Pi

__all__ = ['BackplaneController',]

import os
import time

import pandas as pd
import pexpect

from sctcamsoft.camera_control_classes import DeviceController
from sctcamsoft.camera_control_classes import (CommandArgumentError,
                                               CommandNameError,
                                               ConfigurationError)

class BackplaneController(DeviceController):

    def __init__(self, device, config):
        super().__init__(device, config)
        try:
            # Load IP address of Raspberry Pi
            ip_address = config['ip_address']
            # Load timeout parameter for pexpect
            try:
                timeout = int(config['timeout'])
            except ValueError:
                raise ConfigurationError(self.device, 'timeout',
                                         "must be an integer")
            # Load path to control program on the Pi
            try:
                pi_path, pi_program = os.path.split(config['pi_program_path'])
            except TypeError:
                raise ConfigurationError(self.device, 'pi_program_path',
                                         "must be a path string")
            # Load FPM configuration
            try:
                fpm_config_file = config['fpm_configuration']
                self._fpm_config = pd.read_csv(fpm_config_file)
            except FileNotFoundError:
                raise ConfigurationError(self.device, 'fpm_configuration',
                                         "file not found")
            # Load number of slots in backplane
            try:
                self._num_slots = int(config['num_slots'])
            except ValueError:
                raise ConfigurationError(self.device, 'num_slots',
                                         "must be an integer")
            # Load hold off time to wait between triggering
            try:
                holdoff = int(config['hold_off_time'])
                # Convert to hexadecimal with leading '0x' removed
                self._holdoff = hex(holdoff)[2:]
            except ValueError:
                raise ConfigurationError(self.device, 'hold_off_time',
                                         "must be an integer")
        except KeyError as err:
            raise ConfigurationError(self.device, err.args[0],
                                     "missing configuration parameter")

        # Initialize record of which module slots are powered on
        self._slots_powered_on = set()

        # Start ssh application
        self._ssh = pexpect.spawn("ssh pi@{}".format(ip_address),
                                 timeout=timeout,encoding='utf-8')
        self._ssh.logfile = open("pi_log", "w")
        self._ssh.expect('$')
        # Navigate to directory
        self._ssh.sendline("cd {}".format(pi_path))
        self._ssh.expect('$')
        # Execute program
        self._ssh.sendline("sudo ./{}".format(pi_program))
        self._ssh.expect("exit")  # last line of program prompt

    # Power on a module slot, or if no slot is given, power all off.
    # Since only one additional slot can be powered on at a time,
    # but a list of all slots to be powered is required,
    # store a set of the modules already powered and power those too.
    # Use a hexadecimal number with on bits to specify the slots turned on.
    def _power_fee(self, slot=None):
        if slot is not None:
            self._slots_powered_on.add(slot)
            # The available slots are 0-31
            bits = [1 if s in self._slots_powered_on else 0
                    for s in range(self._num_slots)]
            # Convert list of bits to big-endian hexadecimal representation
            bitstring = ''.join(reversed([str(bit) for bit in bits]))
            hexstring = hex(int(bitstring, 2))
        else:
            self._slots_powered_on = set()
            hexstring = hex(0)
        self._ssh.sendline("n")
        self._ssh.expect("FFFF:")
        self._ssh.sendline(hexstring)
        time.sleep(0.5)

    def _read_modules(self, delimiter=''):
        # Loop over the 5 rows of 5 modules each in the display
        # The FPM positions are numbered left to right, bottom to top,
        # so assemble the list of values in the same order
        # Keep values as strings since they'll be stored that way later anyway
        values = []
        for __ in range(5):
            self._ssh.expect("\r\n")
            # row_values = self._ssh.before.decode().strip().split(delimiter)
            row_values = self._ssh.before.strip().split()
            row_values.reverse()
            values.extend(row_values)
        values.reverse()
        module_values = {}
        for fpm_position, module_id in zip(self._fpm_config.fpm_position,
                                           self._fpm_config.module_id):
            module_values[module_id] = values[fpm_position]
        return module_values

    def _read_tfpga(self, expect):
        self._ssh.sendline('c')
        self._ssh.expect(expect)
        value = self._ssh.before.decode().strip().split()[-1]
        value = int(value.strip())
        return value

    def _read_hit_pattern(self, display=False):
        # Standard trigger pixel numbering:
        # Bottom left, bottom right, top left, top right
        # for each quadrant and for each trigger pixel within each quadrant
        standard_order = [0, 4, 1, 5,
                          8, 12, 9, 13,
                          2, 6, 3, 7,
                          10, 14, 11, 15]
        # Trigger pixel numbering formatted for display
        # as a matrix with the origin at the top left
        display_order = [3, 7, 11, 15,
                         2, 6, 10, 14,
                         1, 5, 9, 13,
                         0, 4, 8, 12]
        trigger_pixel_order = display_order if display else standard_order
        self._ssh.sendline("7")
        self._ssh.expect("read:\r\n")
        slot_hits = []
        for __ in range(self._num_slots):
            self._ssh.expect(",\r\n")
            hits = self._ssh.before.decode().strip()
            # Convert to list of 16 hit bits for the ASIC groups
            # ordered by column from bottom to top
            hits = '{0:016b}'.format(hits)
            hits = list(hits)[::-1]
            # Reformat as a string with the correct order for trigger pixels
            hits = [hits[i] for i in trigger_pixel_order]
            hits = ''.join(hits)
            slot_hits.append(hits)
        hit_pattern = {}
        for module_id, slot in zip(self._fpm_config.module_id,
                                   self._fpm_config.slow_control_slot):
            hit_pattern[module_id] = slot_hits[slot]
        return hit_pattern

    def _set_tack(self, tack):
        self._ssh.sendline('g')
        self._ssh.expect("16-31")
        self._ssh.sendline(tack)
        time.sleep(1)

    def _set_trigger_mask(self, trigger_mask):
        self._ssh.sendline('j')
        self._ssh.expect("read!")
        self._ssh.sendline(trigger_mask)

    def execute_command(self, command):
        cmd = command.command
        update = None
        if cmd == "enable_tack":
            self._set_tack('6f')
        elif cmd == "disable_tack":
            self._set_tack('0')
        elif cmd == "power_fee":
            try:
                slot = command.args['slot']
            except KeyError:
                raise CommandArgumentError(self.device, cmd, 'slot',
                                           "missing argument")
            if slot not in range(self._num_slots):
                raise CommandArgumentError(self.device, cmd, 'slot',
                                           "invalid slot number")
            self._power_fee(slot)
        elif cmd == "power_off_all_fees":
            self._power_fee()
            time.sleep(5)
        elif cmd == "power_on_all_fees":
            for slot in self._fpm_config.slow_control_slot:
                self._power_fee(slot)
            time.sleep(25)
        elif cmd == "reboot_dacq_1":
            self._ssh.sendline('1')
        elif cmd == "reboot_dacq_2":
            self._ssh.sendline('2')
        elif cmd == "read_current":
            self._ssh.sendline('i')
            self._ssh.expect("\(A\)\r\n\r\n")
            current = self._read_modules()
            # print ("current:",current)
            update = self.write_multiple_update('current', current)
        elif cmd == "read_presence":
            self._ssh.sendline('p')
            self._ssh.expect('p\r\n')
            presence = self._read_modules()
            # print("presence:", presence)
            update = self.write_multiple_update('presence', presence)
        elif cmd == "read_voltage":
            self._ssh.sendline('v')
            self._ssh.expect("\~12V\r\n\r\n")
            voltage = self._read_modules()
            # print("voltage:", voltage)
            update = self.write_multiple_update('voltage', voltage)
        elif cmd == "read_hit_pattern":
            display = command.args.get('display', False)
            hit_pattern = self._read_hit_pattern(display=display)
            update = self.write_multiple_update('hit_pattern', hit_pattern)
        elif cmd == "read_tack_count":
            tack_count = self._read_tfpga(expect="TACK Rate")
            update = self.write_update('tack_count', tack_count)
        elif cmd == "read_timer":
            timer = self._read_tfpga(expect="ns")
            update = self.write_update('timer', timer)
        elif cmd == "reset_triggers_and_timer":
            self._ssh.sendline('l')
        elif cmd == "send_sync":
            self._ssh.sendline('s')
            time.sleep(5)
        elif cmd == "set_hold_off_time":
            self._ssh.sendline("o")
            self._ssh.expect("hex :")
            self._ssh.sendline(self._holdoff)
            time.sleep(0.5)
        elif cmd == "set_trigger_mask":
            self._set_trigger_mask("trigger_mask")
        elif cmd == "set_trigger_mask_closed":
            self._set_trigger_mask("trigger_mask_null")
        else:
            raise CommandNameError(self.device, cmd)
        self._ssh.expect("exit \r\n")  # Clear prompt after each command
        return update
