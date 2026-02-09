#! /usr/bin/env python

from psct_toolkit import DataTaker
from run_info import get_run_info, get_livetime

#moduleIDList = [115]
#moduleIDList = [1, 2, 3, 4, 5, 6, 7, 8, 9] #current INFN
#moduleIDList = [100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] #current US
moduleIDList = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] #current All

#trigger_modules = [100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125]  # all US modules except 110 (central module) and 126
trigger_modules = [2, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126]  # all US modules except 1, 4, 5, 6, 7, 8, 9, 110 (central module), 126
#trigger_modules = [100, 103, 106, 107, 108, 111, 112, 114, 119, 123, 124, 125]
#trigger_modules = [115]
#trigger_modules = [1, 2, 7, 100, 103, 106, 107, 108, 112, 114, 119, 121, 123, 124, 125]  # all US modules except 4, 5, 6, 8, 9, 110 (central module), 111, and 115                                    
run_duration = 180  # seconds
static_threshold = [400]*16
pe_threshold = [27.] * 16
num_blocks = 4
hv_on = False

tuning_temp = 16.
new_tune = True

retry = True
n_retry = 3

read_adc_period = 180  # seconds
read_temperatures = False
read_currents = False

channels_per_packet = 32
psocket_buffer_size = 999424
packet_separation = 4000
packet_delay = 0
trigger_delay = 868 #668
add_bias = 0  # mV

# Get info for current run
run_info = get_run_info()

data = DataTaker(moduleIDList, trigger_modules, run_duration=run_duration,
                 HVon=hv_on, static_threshold=static_threshold,
                 numBlock=num_blocks, chPerPacket=channels_per_packet,
                 triggerDly=trigger_delay, addBias=add_bias,
                 packetSeparation=packet_separation, packetDelay=packet_delay,
                 read_adc_period=read_adc_period,
                 read_temperatures=read_temperatures,
                 read_currents=read_currents,
                 pSocketBufferSize=psocket_buffer_size, run_info=run_info, retry=retry, n_retry=n_retry,
		 new_tune=new_tune, tuning_temp=tuning_temp, pmtref4voltage=2.0, pe_threshold=pe_threshold)

try:
    # preserve the order of this procedure or things may go wrong!

    # module initialization and tuning
    data.prepareModules()

    # required if taking data
    # sets chPerPacket, triggerDly, packetSeparation, staticThresh
    data.prepareModules4Readout()

    data.sleep(interval=30, num_intervals=10)

    # sets up writer / listener / buffer
    data.prepareReadout()

    # call to take data
    data.takeInternalTrigData()

    # closes writer / listener / buffer
    data.closeReadout()

    # power off mods at the end of a run
    data.closeMods()

# power off mods if something goes wrong
except:
    data.closeMods()
    raise

livetime = get_livetime(data.actual_duration, data.run_id)
print("Approximate livetime: {} s".format(int(livetime)))
print("Approximate rate: {0:.1f}".format(data.nEvents / livetime))
