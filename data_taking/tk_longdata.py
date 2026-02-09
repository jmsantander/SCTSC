#! /usr/bin/env python

from psct_toolkit import DataTaker
from run_info import get_run_info, get_livetime
import os


#moduleIDList = [115]
#moduleIDList = [1, 2, 3, 4, 5, 7, 8, 9, 106, 121, 125, 126]
#moduleIDList = [1, 2, 3, 4, 5, 6, 7, 8, 9] #current INFN
#moduleIDList = [100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] #current US
moduleIDList = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] #current All
#moduleIDList = [6]

#trigger_modules = [115]
#trigger_modules = [1, 2, 3, 4, 5, 7, 8, 9, 106, 121, 125, 126]
#trigger_modules = [100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125]  # all US modules except 110 (central module) and 126
#trigger_modules = [100, 103, 106, 107, 108, 112, 114, 119, 121, 123, 124, 125]  # all US modules except 110 (central module) and 126, 111, 115
#trigger_modules = [1, 2, 3, 4, 7, 9, 100, 103, 106, 107, 108, 112, 114, 119, 121, 123, 124, 125, 126]  # all modules except 5, 6, 8, 110 (central module), 111, and 115
#trigger_modules = [1, 2, 7, 100, 103, 106, 107, 108, 112, 114, 119, 121, 123, 124, 125]  # all modules except 4, 5, 6, 8, 9, 110 (central module), 111, and 115 
#trigger_modules = [1, 2, 7, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125]  # all modules except 4, 5, 6, 8, 9, 110 (central module), 126
#trigger_modules = [2, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126]  # all modules except 1, 4, 5, 6, 7, 8, 9, 110 (central module)
#trigger_modules = [2, 4, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126]  # all modules except 1, 5, 6, 7, 8, 9, 110 (central module)
trigger_modules  = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] #current All
#trigger_modules = [6]

#run_duration = 300
#run_duration = 3600#300  # seconds; 1 hr, 29 + 2 +29
run_duration = 900  # seconds; 40 min, 19 + 2 + 19
#run_duration = 1800 
static_threshold_us = [550]*16 #[0,0,0,0]+[0,0,0,0]+[0,0,0,0]+[0,400,400,400] #[600]*16
static_threshold_infn = [250]*16 #[0,0,0,0]+[0,0,0,0]+[0,0,0,0]+[0,400,400,400] #[600]*16
pe_threshold_us = [37] * 16  # threshold value in photoelectrons
pe_threshold_infn = [21] * 16  # threshold value in photoelectrons
thresh_type = "static_thresh" #pe_thresh
num_blocks = 4
hv_on = True
#hv_on = False
tuning_temp = None # 11.0 # Use the average temperature from a warmup run to pick the tuning temperature SHOULD NO LONGER BE NECESSARY
new_tune = True
pmtref4voltage = 2.0 # Old value = 1.25. New value = 2.0

read_adc_period = 300  # seconds
read_temperatures = True #True
read_currents = True #True
retry = True
n_retry = 1

channels_per_packet = 32
psocket_buffer_size = 999424
packet_separation = 4000
packet_delay = 0
trigger_delay = 668
add_bias = 0 # mV

# Check if wisconsin disk is mounted
if os.path.isfile('/home/ctauser/target5and7data/previousRun.txt'):
    print ("Wisconsin previousRun.txt file mounted")
else:
    print ("Wisconsin previousRun.txt file NOT mounted. Exiting")
    exit()

# Get info for current run
run_info = get_run_info()

data = DataTaker(moduleIDList, trigger_modules, run_duration=run_duration,
                 HVon=hv_on, static_threshold_us=static_threshold_us, static_threshold_infn=static_threshold_infn,
                 pe_threshold_us=pe_threshold_us,pe_threshold_infn=pe_threshold_infn,
                 numBlock=num_blocks, chPerPacket=channels_per_packet,
                 triggerDly=trigger_delay, addBias=add_bias,
                 packetSeparation=packet_separation, packetDelay=packet_delay,
                 read_adc_period=read_adc_period,
                 read_temperatures=read_temperatures,
                 read_currents=read_currents,
                 tuning_temp=tuning_temp,
                 new_tune=new_tune,
                 pmtref4voltage=pmtref4voltage,
                 pSocketBufferSize=psocket_buffer_size, run_info=run_info, retry=retry, n_retry=n_retry, thresh_type=thresh_type) 

try:
    # preserve the order of this procedure or things may go wrong!

    # module initialization and tuning
    #data.prepareModules()
    data.prepareModules(write_trim_log=True, italian_bias=0)

    # correct location to set trim voltages to something different
    """
    asicDict = {0: 0b0001, 1: 0b0010, 2: 0b0100, 3: 0b1000}
    for module, moduleID in zip(data.moduleList, data.moduleIDList):
        module.WriteSetting("HV_Enable", 0b1)
        for asic in range(4):
            module.WriteSetting("HVDACControl", asicDict[asic])
            module.WriteSetting("LowSideVoltage", 0x30000)
            module.WriteSetting("LowSideVoltage", 0x31000)
            module.WriteSetting("LowSideVoltage", 0x32000)
            module.WriteSetting("LowSideVoltage", 0x33000)
    """
    # required if taking data
    # sets chPerPacket, triggerDly, packetSeparation, staticThresh
    data.prepareModules4Readout()
    #data.setStaticThresh(moduleID, staticThresh=list) #To set static thresh module by module
    #data.setStaticThresh(4, [0, 0, 0, 0] + [0, 0, 0, 0] + [0, 0, 400, 0] + [0, 0, 0, 0])
    #data.setStaticThresh(5, [400, 0, 0, 0] + [0, 0, 0, 0] + [0, 0, 0, 0] + [0, 0, 0, 0])
    #data.setStaticThresh(103, [0, 400, 0, 0] + [0, 0, 0, 0] + [0, 0, 0, 0] + [0, 0, 0, 0])

    # Sets 5 minute sleep time
    data.sleep(interval=30, num_intervals=10) #Nominal Equilibriation Time - it'll sleep for 5mins to make sure the modules have hit their nominal Temp
                                              #before taking data. Want to have this enabled in general
                                              
    #data.sleep(interval=30, num_intervals=2)                                        
    #data.sleep(interval=30, num_intervals=4)
    data.update_tuning()
    #data.update_tuning(flat_trims=flat_trims)
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
