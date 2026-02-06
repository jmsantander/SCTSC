"""Control for communication with the modules using TargetDriver"""

__all__ = ['TargetController',]

from collections import namedtuple, OrderedDict
import datetime
import itertools
import json
from queue import Empty, Queue
#from multiprocessing import Process, Queue
import threading
import os
import subprocess
import time

import numpy as np
import pandas as pd
import yaml

import target_driver
import target_io

from tuneModule import getTunedWrite

from sctcamsoft.camera_control_classes import DeviceController
from sctcamsoft.camera_control_classes import (CommandArgumentError,
                                               CommandExecutionError,
                                               CommandNameError,
                                               CommandSequenceError,
                                               ConfigurationError)

ModuleCommand = namedtuple('ModuleCommand',
                           ['function', 'parameters', 'variable', 'unit'],
                           defaults=(None, 'state', None))

class TargetController(DeviceController):
    """ DeviceController for control and communication with the TARGET modules

    This class uses the TargetDriver and TargetIO libraries to connect to,
    initialize, and tune the modules, and holds the connection to the modules
    so that the setup needs only to be done once, at the start of the night.

    The class is used to take data, using the start_readout and stop_readout
    methods to begin and end data readout, writing the results to a FITS file.
    Data taking occurs between these calls, without blocking.

    The trigger rate can also be read using the read_trigger_rate method.
    To take a rate scan, repeatedly request a threshold, then read the rate.

    This class also provides access to the monitoring variables read out from
    the MAX1230 ADC units, namely the FEE temperatures and pixel currents,
    using the read_temperature, read_currents, and read_total_current methods.
    It is recommended to close the trigger mask before calling these methods,
    as turning on the ADC units introduces noise.
    """

    def __init__(self, device, config):
        super().__init__(device, config)
        # Load configuration parameters
        try:
            # Dictionary of DACQ subnet: port IP address
            self._dacq_subnet_port_ip = config['dacq_subnet_port_ip']
            # TargetDriver board config file
            self._board_def = config['board_def']
            # TargetDriver ASIC config file
            self._asic_def = config['asic_def']
            # Number of ASICs per module
            try:
                self._num_asic = int(config['num_asic'])
            except ValueError:
                raise ConfigurationError(self.device, 'num_asic',
                                         "must be an integer")
            # Number of ASIC groups per ASIC
            try:
                self._num_groups_per_asic = int(config['num_groups_per_asic'])
            except ValueError:
                raise ConfigurationError(self.device, 'num_groups_per_asic',
                                         "must be an integer")
            # Dictionary of ASIC settings
            self._asic_parameters = {}
            self._initialize_parameters(config, 'asic_parameters',
                                        self._asic_parameters)
            # Dictionary of data taking parameters
            self._readout_parameters = {}
            self._initialize_parameters(config, 'readout_parameters',
                                        self._readout_parameters)
            # Dictionary of module tuning parameters
            self._tuning_parameters = {}
            self._initialize_parameters(config, 'tuning_parameters',
                                        self._tuning_parameters)
            # Dictionary of ADC (temperature/current) reading parameters
            self._adc_parameters = {}
            self._initialize_parameters(config, 'adc_parameters',
                                        self._adc_parameters,
                                        set_parameters=True)
            # Dictionary of rate scan parameters
            self._rate_scan_parameters = {}
            self._initialize_parameters(config, 'rate_scan_parameters',
                                        self._rate_scan_parameters,
                                        set_parameters=True)
            self._rate = self._rate_scan_parameters['default_rate']['set_value']
            # Dictionaries of module ID: list of pixel numbers to mask
            # Provides fine control of the behavior of trigger modules,
            # and ignored for modules not included in that list.
            # Default for trigger modules not specified: trigger on all pixels
            # Need two, as trigger pixels behave differently with HV on and off
            self._trigger_pixel_mask_path = {}
            for hv_on, hv_string in [(True, 'on'), (False, 'off')]:
                param = 'trigger_pixel_mask_hv_' + hv_string
                self._trigger_pixel_mask_path[hv_on] = config[param]
            # FPM configuration
            try:
                fpm_config_file = config['fpm_configuration']
                self._fpm_config = pd.read_csv(fpm_config_file)
            except FileNotFoundError:
                raise ConfigurationError(self.device, 'fpm_configuration',
                                         "file not found")
            # FEE configuration
            try:
                fee_config_file = config['fee_configuration']
                self._fee_config = pd.read_csv(fee_config_file)
            except FileNotFoundError:
                raise ConfigurationError(self.device, 'fee_configuration',
                                         "file not found")
            # Path to copy the trigger mask to on the Raspberry Pi
            self._trigger_mask_path = config['trigger_mask_path']
            # IP address of Raspberry Pi (for copying the trigger mask)
            self._pi_ip_address = config['pi_ip_address']
        except KeyError as err:
            raise ConfigurationError(self.device, err.args[0],
                                     "missing configuration parameter")
        # Ordered dictionary of module ID: module object
        self._modules = OrderedDict()
        # Sets of the requested and set modules for the camera to use
        # Default: request all modules
        self._requested_module_ids = set(self._fpm_config.module_id)
        self._set_module_ids = set()
        # Sets of the requested and set modules for the camera to trigger on
        # Default: request all modules
        self._requested_trigger_module_ids = set(self._fpm_config.module_id)
        self._set_trigger_module_ids = set()

        # Readout objects
        self._listener = None
        self._writer = None
        self._run_id = None
        self._data_file_path = None

    def _initialize_parameters(self, config, name, dictionary,
                               set_parameters=False):
        try:
            for param, value in config[name].items():
                dictionary[param] = {}
                dictionary[param]['requested_value'] = value
                set_value = value if set_parameters else None
                dictionary[param]['set_value'] = set_value
                dictionary[param]['default_value'] = value
                dictionary[param]['type'] = type(value)
        except AttributeError:
            raise ConfigurationError(self.device, name, "must be a dictionary")

    def _connect(self, module_id):

        module = self._modules[module_id]
        module_num = list(self._modules.keys()).index(module_id)

        loc = (self._fee_config.module_id == module_id)
        module_ip = self._fee_config.ip_address.loc[loc].values[0]
        subnet = self._fee_config.dacq_subnet.loc[loc].values[0]
        client_ip = self._dacq_subnet_port_ip[subnet]
        module.SetIPAddresses(client_ip, module_ip) 
#        fail = module.EstablishSlowControlLink(client_ip, module_ip)
#        if fail:
#            print("Module: {}, Failed to establish slow control connection, with: {}".format(module_id,fail))
#        else:
#            port = np.uint16(0)
#            dataPort = np.uint16(0)
#            regVal = 0
#            time.sleep(0.2)
#            regVal = module.ReadRegister(0x80)
#            port = (regVal[1] >> 16) & 0xFFFF
#            dataPort = (regVal[1]) & 0xFFFF
#            print("Module: {}, Slow control connection established with slow control port: {} and data port: {}".format(module_id,port, dataPort))
#            # Write integer values to identify modules
#            module.WriteSetting("DetectorID", module_num)
#            module.WriteSetting("CTAID", module_id)
        module.Connect()
        time.sleep(1)
        state = self._get_state(module_id)
        print("Module id: {}, State after connect: {}".format(module_id, state))
#        time.sleep(1)
#        module.WriteSetting("DetectorID", module_num)
#        module.WriteSetting("CTAID", module_id)
#        time.sleep(1)
        TC_OK=module.GoToPreSync()
#        print("Module into PreSync with return: {}".format(TC_OK))
#        time.sleep(0.2)
        state = self._get_state(module_id)
#        time.sleep(0.2)
#        print("Module id: {}, State after presync: {}".format(module_id, state))
#        time.sleep(0.2)
#        self._set_asic_parameters(module_id)
#        time.sleep(3)
#        self._ready(module_id)
#        print("Module id: {}, State after ready: {}".format(module_id, state))
        
        
        
        
#        print("Module id:{},  State after 60 s:{}".format(module_id, self._get_state(module_id)))
        #print("Writing WR_ADDR_Incr1LE_Delay: 3, to asic 0")
        #ret_writeasicsetting = module.WriteASICSetting('WR_ADDR_Incr1LE_Delay', 0, 3)
        #print("Writing WR_ADDR_Incr1LE_Delay: 3, to asic 0 returned with value: ", ret_writeasicsetting)
        #print("Calling set_asic_parameters")
        ##self._set_asic_parameters(module_id)
        
        

    def _close(self, module_id):
        self._modules[module_id].CloseSockets()

    def _set_asic_parameters(self, module_id):
        for asic in range(self._num_asic):
            for setting, setting_info in self._asic_parameters.items():
                value = setting_info['requested_value']
                #self._modules[module_id].WriteASICSetting(setting, asic, value)
                ret_writeasicsetting = self._modules[module_id].WriteASICSetting(setting, asic, value)
                print("Module {}, Writing {}: {}, to asic {} returned with value: {}".format(module_id,setting,value,asic,ret_writeasicsetting))
                self._asic_parameters[setting]['set_value'] = value

    def _ready(self, module_id):
        self._modules[module_id].GoToReady()
        print("Module id: {}, State after ready: {}".format(module_id,self._get_state(module_id)))

    def _ping(self, module_id):
        # Make sure dataport connection is not lost
        self._modules[module_id].DataPortPing()

    def _read_adc_value(self, module_id, register, start_bit):
        """
        Read the value from a register with ADC values, reading part 0 or 1.
        Check that the data are valid,
        and if not try a total of num_tries times,
        waiting wait_time seconds in between each try.
        """
        for __ in range(self._adc_parameters['num_tries']['set_value']):
            ret, value = self._modules[module_id].ReadRegister(register)
            bitstring = '{0:032b}'.format(value)[::-1]
            bitstring = bitstring[start_bit:start_bit + 16]
            validation_bit = int(bitstring[15], 2)
            if not ret and validation_bit:
                value = int(bitstring[12::-1], 2)
                return value
            time.sleep(self._adc_parameters['wait_time']['set_value'])
        # Loop exited - no valid value found after all tries completed
        return 0

    def _activate_adc(self, module_id):
        """Activate the MAX1230 ADC"""
        self._modules[module_id].WriteSetting('ADCEnableSelect', 0b1111)
        self._modules[module_id].WriteSetting('ADCStart', 1)
        time.sleep(0.1)

    def _deactivate_adc(self, module_id):
        """
        Deactivate the MAX1230 ADC
        It's important to deactivate this element when not in use,
        because it introduces noise into the trigger path
        """
        self._modules[module_id].WriteSetting('ADCEnableSelect', 0)
        self._modules[module_id].WriteSetting('ADCStart', 1)
        time.sleep(0.1)

    def _read_temperature(self, module_id):
        """Read out the temperature on the auxiliary board"""
        temperature = np.zeros(4)
        for i, (register, start_bit) in enumerate([(0x34, 0), (0x45, 0),
                                                   (0x34, 16), (0x45, 16)]):
            temperature[i] = self._read_adc_value(module_id, register,
                                                  start_bit)
        temperature *= 0.125  # Convert raw values to degrees C
        temperature_string = json.dumps(temperature.tolist())
        return temperature_string

    def _read_currents(self, module_id):
        """Read out the currents on the auxiliary board"""
        currents = np.zeros((self._num_asic, self._num_groups_per_asic))
        # Read individual pixel currents
        for asic, channel in itertools.product(range(self._num_asic),
                                               range(self._num_groups_per_asic)):
            register = 0x35 + (asic % 2)*17 + channel
            start_bit = 0 if asic in [0, 1] else 16
            value = self._read_adc_value(module_id, register, start_bit)
            currents[asic, channel] = value
        currents *= 0.5  # Convert raw values to uA
        currents_string = json.dumps(currents.tolist())
        return currents_string

    def _read_total_current(self, module_id):
        """Read out the total current on the auxiliary board"""
        return self._read_adc_value(module_id, 0x2a, 0)

    def _set_tuning_parameters(self, module_id):
        """
        Set offset voltages on trigger path, numBlock, and HV values for FPMs
        """

        def value(param):
            return self._tuning_parameters[param]['requested_value']

        # TODO: clean up and integrate tuneModule.py
        getTunedWrite(module_id, self._modules[module_id], value('vped_value'),
                      HV=value('hv_on'), numBlock=value('num_blocks'),
                      addBias=value('add_bias'))


    def _set_readout_parameters(self, module_id):

        def value(param):
            return self._readout_parameters[param]['requested_value']

        module = self._modules[module_id]
        module.WriteSetting("MaxChannelsInPacket", value('channels_per_packet'))
        time.sleep(0.5)
        module.WriteSetting("TriggerDelay", value('trigger_delay'))
        time.sleep(0.5)
        module.WriteRegister(0x71, value('packet_separation'))
        time.sleep(0.5)
        self._set_thresh(module_id)
        time.sleep(0.5)


    def _set_thresh(self, module_id):
        thresh = self._readout_parameters['thresh']['requested_value']
        module = self._modules[module_id]
        for i in range(self._num_asic):
            for j in range(self._num_groups_per_asic):
                module.WriteASICSetting("Thresh_{}".format(j), i, thresh, True)


    def _get_state(self, module_id):
        # Defined in https://forge.in2p3.fr/projects/cta/repository/entry/COM/CCC/TargetDriver/trunk/include/TargetDriver/TargetModule.h
        # States are Not Present, Not Powered, Not Responding,
        # Not yet contacted, Safe, Pre-sync, and Ready
        #return self._modules[module_id].GetStateString()
        return self._modules[module_id].GetState()


    def _execute_parallel(self, module_fn, module_ids=None):

        def target(module_id, q):
            module_data = module_fn(module_id)
            # If the module_fn doesn't return data, return the state instead
            if module_data is None:
                module_data = self._get_state(module_id)
            q.put((module_id, module_data))

        # Default: execute command on all modules
        if module_ids is None:
            module_ids = self._set_module_ids

        # Execute module_fn on each TargetModule in its own thread
        q = Queue()
        procs = []
        time1 = datetime.datetime.utcnow()
        for module_id in module_ids:
            proc = threading.Thread(target=target, args=(module_id, q)) # Process(target=target, args=(module_id, q))
            procs.append(proc)
            proc.start()
        for proc in procs:
            proc.join()

        # Create the return data from the results pushed onto q from each process
        data = {}
        while True:
            try:
                module_id, module_data = q.get(False)
                data[module_id] = module_data
            except Empty:
                break
       # q.close()

        time2 = datetime.datetime.utcnow()
        # Approximate the timestamp by averaging the times before and after
        timestamp = time1 + (time2 - time1) / 2

        return data, timestamp

    def _read_register(self, register):
        values = {}
        for module_id, module in self._modules.items():
            __, value = module.ReadRegister(register)
            hex_value = "0x{:08x}".format(value)
            values[module_id] = hex_value
        return values

    def _write_trigger_mask(self, cmd='write_trigger_mask'):

        # Determine trigger mask positions
        # The first seven (32 - 25) trigger mask positions are never used
        trigger_mask_position = [None, None, None, None, None, None, None]
        trigger_mask_position.extend([module_id for pos, module_id
                                      in sorted(zip(
                                          self._fpm_config.trigger_mask_position,
                                          self._fpm_config.module_id))])

        # Mask pixels appropriately for the HV setting (on/off)
        hv_on = self._tuning_parameters.get('hv_on')
        mask_path = self._trigger_pixel_mask_path[hv_on]
        try:
            with open(mask_path, 'r') as pixel_mask:
                trigger_pixel_mask = yaml.safe_load(pixel_mask)
        except FileNotFoundError:
            raise CommandExecutionError(self.device, cmd,
                                        "trigger pixel mask file {} "
                                        "not found".format(mask_path))

        # Write the trigger mask file
        with open("trigger_mask", 'w') as maskfile:
            for module_id in trigger_mask_position:
                if (module_id is not None
                        and module_id in self._requested_trigger_module_ids):
                    bits = ['0'] * 16
                    masked_pixels = trigger_pixel_mask.get(module_id, [])
                    for pixel in masked_pixels:
                        bits[pixel] = '1'
                    bits.reverse()
                    bitmask = ''.join(bits)
                    # Convert to hexadecimal string (with no leading '0x')
                    maskfile.write('{:0>4x}\n'.format(int(bitmask, 2)))
                else:
                    maskfile.write('ffff\n')

        # Copy the trigger mask file to the Pi and delete the local copy
        proc = subprocess.run("scp trigger_mask pi@{}:{}".format(
            self._pi_ip_address, self._trigger_mask_path),
                              shell=True, check=False)
        os.remove("trigger_mask")
        if proc.returncode:
            raise CommandExecutionError(self.device, cmd,
                                        "scp of trigger mask failed with "
                                        "status {}".format(proc.returncode))
        self._set_trigger_module_ids = self._requested_trigger_module_ids


    def _read_tacks(self):
        # Reading the TACK count from the first module is arbitrary,
        # since all modules have the same value
        try:
            first_module = next(iter(self._modules))
        except StopIteration:
            raise IndexError
        num_tacks = np.uint16(first_module.ReadRegister(0xf)[1] & 0xffff)
        return num_tacks


    def _count_triggers(self, duration):
        num_tacks_before = self._read_tacks()
        time.sleep(duration)
        num_tacks_after = self._read_tacks()
        num_triggers = num_tacks_after - num_tacks_before
        if num_triggers < 0:
            num_triggers += 65535
        return num_triggers


    def _read_trigger_rate(self, cmd):
        """ Read the trigger rate

        Estimate the time needed to collect enough counts to reach the
        required precision, where
        precision = rate_error / rate, and
        rate = counts / duration, rate_error = sqrt(counts) / duration
        -> counts = 1 / precision**2
        -> duration = 1 / (rate * precision**2)

        Estimate the rate using the rate measured on the previous threshold
        Since the rate decreases close to monotonically,
        this should generally be an over-estimate
        """

        total_counts = 0
        precision = self._rate_scan_parameters['precision']['set_value']
        remaining_counts = round(pow(precision, -2))

        total_duration = 0
        remaining_duration = self._rate_scan_parameters['timeout']['set_value']

        while remaining_counts > 0 and remaining_duration > 0:
            duration = min(remaining_counts / self._rate, remaining_duration)
            try:
                counts = self._count_triggers(duration)
            except IndexError:
                raise CommandExecutionError(self.device, cmd,
                                            "no modules available")
            total_counts += counts
            remaining_counts -= counts
            total_duration += duration
            remaining_duration -= duration
            self._rate = total_counts / total_duration
        return self._rate


    def _start_readout(self, cmd):
        """Prepare for data taking and start taking data"""

        for param in ['buffer_depth', 'num_packets_per_event',
                      'channels_per_packet']:
            if self._readout_parameters[param]['set_value'] is None:
                raise CommandSequenceError(self.device, cmd,
                                           "must set readout parameters"
                                           " before starting readout")

        buffer_depth = self._readout_parameters['buffer_depth']['set_value']

        num_packets_per_event =\
                self._readout_parameters['num_packets_per_event']['set_value']
        total_num_packets_per_event = num_packets_per_event * len(self._modules)

        channels_per_packet =\
                self._readout_parameters['channels_per_packet']['set_value']
        num_blocks = self._tuning_parameters['num_blocks']['set_value']
        if num_blocks is None:
            raise CommandSequenceError(self.device, cmd,
                                       "must set tuning parameters"
                                       " before starting readout")
        packet_size = 2*(10 + channels_per_packet*(num_blocks*32 + 1))

        self._listener = target_io.DataListener(buffer_depth,
                                               total_num_packets_per_event,
                                               packet_size)
        for server_ip in self._dacq_subnet_port_ip.values():
            self._listener.AddDAQListener(server_ip)
        self._listener.StartListening()
        event_buffer = self._listener.GetEventBuffer()

        self._writer = target_io.EventFileWriter(self._data_file_path,
                                                total_num_packets_per_event,
                                                packet_size)
        self._writer.StartWatchingBuffer(event_buffer)


    def _stop_readout(self, cmd):
        """Stop taking data and clean up after data taking"""

        del cmd  # unused
        self._writer.StopWatchingBuffer()
        self._listener.StopListening()
        self._writer.Close()

        for module_id, module in self._modules.items():
            module.DeleteDAQListeners()


    def _get_run_results(self, cmd):
        if self._data_file_path is None:
            raise CommandSequenceError(self.device, cmd,
                                       "must define a run before"
                                       " getting run results")
        reader = target_io.EventFileReader(self._data_file_path)
        num_events = reader.GetNEvents()
        reader.Close()

        if self._writer is None:
            num_packets_written = 0
        else:
            num_packets_written = self._writer.GetPacketsWritten()

        num_packets_per_event =\
            self._readout_parameters['num_packets_per_event']['set_value']
        if num_packets_per_event is None:
            raise CommandSequenceError(self.device, cmd,
                                       "must set readout parameters"
                                       " before getting run results")
        total_num_packets_per_event = num_packets_per_event * len(self._modules)
        num_packets_expected = total_num_packets_per_event * num_events

        run_results = {
            'run_id': self._run_id,
            'data_file_path': self._data_file_path,
            'num_events': num_events,
            'num_packets_written': num_packets_written,
            'num_packets_expected': num_packets_expected,
            }

        return run_results

    def execute_command(self, command):
        cmd = command.command
        update = None
        module_commands = {
            'connect': ModuleCommand(self._connect),
            'close': ModuleCommand(self._close),
            'ready': ModuleCommand(self._ready),
            'ping': ModuleCommand(self._ping),
            'activate_adc': ModuleCommand(self._activate_adc),
            'deactivate_adc': ModuleCommand(self._deactivate_adc),
            'set_thresh': ModuleCommand(self._set_thresh),
            'set_asic_parameters': ModuleCommand(
                self._set_asic_parameters, parameters=self._asic_parameters),
            'set_tuning_parameters': ModuleCommand(
                self._set_tuning_parameters, parameters=self._tuning_parameters),
            'set_readout_parameters': ModuleCommand(
                self._set_readout_parameters,
                parameters=self._readout_parameters),
            #'read_state': ModuleCommand(lambda module_id: None), # does nothing
            'read_state': ModuleCommand(lambda module_id: self._get_state(module_id)), 
            'read_temperature': ModuleCommand(self._read_temperature,
                                              variable='temperature', unit='C'),
            'read_currents': ModuleCommand(self._read_currents,
                                           variable='currents', unit='uA'),
            'read_total_current': ModuleCommand(self._read_total_current,
                                                variable='total_current',
                                                unit='uA'),
            }
        request_parameter_commands = {
            'request_asic_parameter': self._asic_parameters,
            'request_readout_parameter': self._readout_parameters,
            'request_tuning_parameter': self._tuning_parameters,
            'request_adc_parameter': self._adc_parameters,
            'request_rate_scan_parameter': self._rate_scan_parameters,
            }
        get_parameter_commands = {
            'get_asic_parameters': self._asic_parameters,
            'get_readout_parameters': self._readout_parameters,
            'get_tuning_parameters': self._tuning_parameters,
            'get_adc_parameters': self._adc_parameters,
            'get_rate_scan_parameters': self._rate_scan_parameters,
            }
        enable_disable_commands = {
            'enable_module': (self._requested_module_ids, set.add),
            'disable_module': (self._requested_module_ids, set.remove),
            'enable_trigger_module': (self._requested_trigger_module_ids,
                                      set.add),
            'disable_trigger_module': (self._requested_trigger_module_ids,
                                       set.remove),
            }
        get_module_ids_commands = {
            'get_module_ids': self._set_module_ids,
            'get_trigger_module_ids': self._set_trigger_module_ids,
            }
        readout_commands = {
            'start_readout': self._start_readout,
            'stop_readout': self._stop_readout,
            }
        if cmd == "initialize":
            self._modules.clear()
            self._set_module_ids.clear()
            state = {}
            # Initialize modules in a standard, reproducible order
            ordered_module_ids = sorted(self._requested_module_ids,
                                        key=list(
                                            self._fee_config.module_id).index)
            print("ordered_module_ids: ", ordered_module_ids)
            for module_num, module_id in enumerate(ordered_module_ids):
                print("module_num: {}, module_id: {}".format(module_num, module_id))
                self._modules[module_id] = target_driver.TargetModule(
                    self._board_def, self._asic_def, module_num)
                print("self._modules[{}]: {}".format(module_id,self._modules[module_id]))
                state[module_id] = self._get_state(module_id)
                print("state[{}]: {}".format(module_id,state[module_id]))
                print("in-loop self._modules: ", self._modules)
            print("after-loop self._modules: ", self._modules)            
            self._set_module_ids = self._requested_module_ids.copy()
            print("after set_module_ids self._modules: ", self._modules)
            update = self.write_multiple_update('state', state)
            print("after write_multiple_updates self._modules: ", self._modules)
        elif cmd in module_commands:
            if not self._modules:
                raise CommandSequenceError(self.device, cmd,
                                           "no modules initialized")
            try:
                module_id = command.args['module_id']
                module_id = None if module_id == 'all' else [int(module_id)]
            except KeyError as err:
                raise CommandArgumentError(self.device, cmd, err.args[0],
                                           "missing argument")
            except (TypeError, ValueError):
                raise CommandArgumentError(self.device, cmd, 'module_id',
                                           "must be an integer")
            function = module_commands[cmd].function
            data, timestamp = self._execute_parallel(function, module_id)
            if module_commands[cmd].parameters is not None:
                for param_info in module_commands[cmd].parameters.values():
                    param_info['set_value'] = param_info['requested_value']
            # Write an update containing the module state (default),
            # or data if the command returns it
            variable = module_commands[cmd].variable
            try:
                unit = module_commands[cmd][1].unit
            except AttributeError:
                unit = ''
            update = self.write_multiple_update(variable, data, unit=unit,
                                                timestamp=timestamp)
        elif cmd in request_parameter_commands:
            parameters = request_parameter_commands[cmd]
            try:
                param = command.args['parameter']
                requested_value = command.args['value']
                requested_value = parameters[param]['type'](requested_value)
            except KeyError as err:
                raise CommandArgumentError(self.device, cmd, err.args[0],
                                           "missing argument")
            except ValueError:
                valtype = parameters[param]['type'].__name__
                raise CommandArgumentError(self.device, cmd, 'value',
                                           "must be {}".format(valtype))
            parameters[param]['requested_value'] = requested_value
            if cmd in ["request_adc_parameter", "request_rate_scan_parameter"]:
                # These are just variables, no need for further setting
                parameters[param]['set_value'] = requested_value
        elif cmd in get_parameter_commands:
            parameters = get_parameter_commands[cmd]
            variable = cmd[4:]  # Remove "get_"
            values = {param: param_info['set_value'] for param, param_info
                      in parameters.items()}
            update = self.write_multiple_update(variable, values)
        elif cmd in enable_disable_commands:
            try:
                module_id = int(command.args['module_id'])
            except KeyError as err:
                raise CommandArgumentError(self.device, cmd, err.args[0],
                                           "missing argument")
            except (TypeError, ValueError):
                raise CommandArgumentError(self.device, cmd, 'module_id',
                                           "must be an integer")
            module_ids, func = enable_disable_commands[cmd]
            func(module_ids, module_id)
        elif cmd in get_module_ids_commands:
            module_ids = get_module_ids_commands[cmd]
            variable = cmd[4:]  # Remove "get_"
            values = {module_id: '' for module_id in module_ids}
            update = self.write_multiple_update(variable, values)
        elif cmd in readout_commands:
            readout_commands[cmd](cmd)
        elif cmd == "initialize_run":
            try:
                run_id = int(command.args['run_id'])
            except KeyError:
                raise CommandArgumentError(self.device, cmd, 'run_id',
                                           "missing argument")
            except ValueError:
                raise CommandArgumentError(self.device, cmd, 'run_id',
                                           "must be integer")
            self._run_id = run_id

            # Data run variables
            self._listener = None
            self._writer = None
            outdir = self._readout_parameters['data_outdir']['set_value']
            if outdir is None:
                raise CommandSequenceError(self.device, cmd,
                                           "must set readout parameters"
                                           " before defining a run")
            self._data_file_path = os.path.join(outdir,
                                                "run{}.fits".format(run_id))
            # Rate scan variables
            self._rate = self._rate_scan_parameters['default_rate']['set_value']

            update = self.write_update('run_id', self._run_id)
        elif cmd == "get_run_results":
            run_results = self._get_run_results(cmd)
            update = self.write_multiple_update('run_results', run_results)
        elif cmd == "read_register":
            try:
                register = int(command.args['register'])
            except KeyError:
                raise CommandArgumentError(self.device, cmd, 'register',
                                           "missing argument")
            except ValueError:
                raise CommandArgumentError(self.device, cmd, 'register',
                                           "must be integer")
            if not 0 <= register <= 128:
                raise CommandArgumentError(self.device, cmd, 'register',
                                           "must be between 0 and 128 "
                                           "inclusive")
            values = self._read_register(register)
            update = self.write_multiple_update('register_{}'.format(register),
                                                values)
        elif cmd == "write_trigger_mask":
            self._write_trigger_mask(cmd)
        elif cmd == "read_trigger_rate":
            rate = self._read_trigger_rate(cmd)
            update = self.write_update('trigger_rate', rate)
        else:
            raise CommandNameError(self.device, cmd)
        return update
