# Slow control for module temperatures
# Temperatures can only be read during data taking,
# so they are written to a text file
# that this controller reads from

# Two commands are available:
# get_last_run_num: Return run number of most recent temperature file
# read_temperature: Return temperatures of all FEEs by module number

__all__ = ['FEETemperatureController',]

from datetime import datetime
import glob
import os

import numpy as np

from sctcamsoft.camera_control_classes import DeviceController
from sctcamsoft.camera_control_classes import (CommandArgumentError,
                                               CommandExecutionError,
                                               CommandNameError,
                                               ConfigurationError)

class FEETemperatureController(DeviceController):

    def __init__(self, device, config):
        super().__init__(device, config)
        self._file_prefix = '_temperatures.txt'
        try:
            self._dir = config['temperature_dir']
        except KeyError:
            raise ConfigurationError(self.device, 'temperature_dir',
                                     "missing configuration parameter")

    # Load the temperature file from the most recent run
    def _get_most_recent_file(self, cmd):
        path = os.path.join(self._dir, '*'+self._file_prefix)
        try:
            temperature_file = max(glob.glob(path))
        except ValueError:
            raise CommandArgumentError(self.device, cmd, 'run_num',
                                       "no temperature files found")
        return temperature_file

    def execute_command(self, command):
        cmd = command.command
        update = None
        if cmd == "get_last_run_num":
            temperature_file = self._get_most_recent_file(cmd)
            base = os.path.basename(temperature_file) #base=332519_temperatures.txt
            filename = os.path.splitext(base)[0]  #332519_temperatures
            run_num = filename.split("_temperatures", 1)[0]
            update = self.write_update('last_run_num', run_num)
        elif cmd == "read_temperature":
            run_num = command.args.get('run_num')
            if run_num is None:
                temperature_file = self._get_most_recent_file(cmd)
            else:
                try:
                    run_num = int(run_num)
                except ValueError:
                    raise CommandArgumentError(self.device, cmd, 'run_num',
                                               "invalid run number")
                temperature_file = os.path.join(self._dir,
                                                run_num+self._file_prefix)
            #if the temperature file has only one line, then it means that only
            #the header is there
            f = open(temperature_file)
            flines = len(f.readlines())
            f.close()
            if(flines>1):
                try:
                    #there are 2 timestamps in the temperature file
                    #a. timestamp_start
                    #b. timestamp_end
                    #they are typically few seconds apart, so we can take either
                    timestamps_start = np.loadtxt(temperature_file, dtype=np.str, delimiter=',', usecols=0, skiprows=1)
                    timestamps_end = np.loadtxt(temperature_file, dtype=np.str, delimiter=',', usecols=1, skiprows=1)

                    #format of the temp file
                    #timestamp_start,timestamp_end,1_ADC0,1_ADC1,1_ADC2,1_ADC3,...{FEEnum}_ADC0,{FEEnum}_ADC1,...
                    # Skip the first 2 columns with the timestamp strings
                    with open(temperature_file, 'r') as tempfile:
                        num_cols = len(tempfile.readline().strip().split(','))
                    usecols_fee = range(2, num_cols, 4)

                    #format of the temp file
                    #timestamp_start,timestamp_end,1_ADC0,1_ADC1,1_ADC2,1_ADC3,...{FEEnum}_ADC0,{FEEnum}_ADC1,...

                    fee_nums = np.loadtxt(temperature_file, dtype=np.str,
                                          delimiter=',', usecols=usecols_fee,
                                          max_rows=1)

                    #Converts scalars to 1d arrays and preserves higher order inputs
                    fee_nums = np.atleast_1d(fee_nums)
                    fee_nums = np.asarray([int(fee_num.split('_')[0]) for fee_num in fee_nums])
                    #print(fee_nums)
                    usecols = range(2,num_cols) 
                    temps = np.loadtxt(temperature_file, delimiter=',',
                                       usecols=usecols, skiprows=1)

                    temps = np.atleast_1d(temps)
                    #print(temps)
                except Exception as err:  # FIXME: what error is this for?
                    raise CommandExecutionError(self.device, cmd,
                                                "Temperature file is being written"
                                                " by another process") from err
                # Keep only the most recent temperature reading
                timestamps_start = np.atleast_1d(timestamps_start)
                last_timestamp = datetime.fromisoformat(timestamps_start[-1])
                #last_temps = temps[-1].reshape((-1, 4))
                shape_temps = np.shape(temps)
                #print(shape_temps)
                shape_temps_first_row = (len(fee_nums)*4,);
                #print(shape_temps_first_row)
                if(shape_temps == shape_temps_first_row):
                    last_temps = temps
                else:
                    last_temps = temps[-1]
                #last_temps = np.atleast_1d(last_temps)
                #print(last_temps)
                temperatures = {}

                #lower_limit = 4  # degrees C
                #upper_limit = 125  # degrees C

                # For display, ignore broken sensors and average the readings
                # In the future, we may want to display ADC-wise temperatures
                # even with the broken (very low = 4 or very high = 125 readings)

                for i in range(len(fee_nums)):
                    fee_num = fee_nums[i]
                    t = last_temps[4*i:4*(i+1)]
                    #good_temps = t[(t > lower_limit) & (t < upper_limit)]
                    #if good_temps.size > 0:
                    #    temperatures[fee_num] = np.mean(good_temps)
                    #else:
                    #    temperatures[fee_num] = np.nan
                    temperatures[fee_num] = np.mean(t)

                update = self.write_multiple_update('temperature',
                                                    temperatures,
                                                    unit='C',
                                                    timestamp=last_timestamp)
        else:
            raise CommandNameError(self.device, cmd)
        return update
