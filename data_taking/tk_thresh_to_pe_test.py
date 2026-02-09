from psct_toolkit import RateScanner
from run_info import get_run_info, get_rate_scan_results
import numpy as np
import time, os


#moduleIDList = [8]
#moduleIDList = [1, 2, 3, 4, 5, 7, 8, 9, 106, 121, 125, 126]
#moduleIDList = [1, 2, 3, 4, 5, 6, 7, 8, 9] #current INFN
#moduleIDList = [100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] #current US
moduleIDList = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] #current All
#moduleIDList = [1, 2, 4, 5, 6, 7, 8, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] #current All, excluding 3 and 9

#trigger_modules = [8]
trigger_modules = [124]
#trigger_modules = [100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126]  # all US modules except 110 (central module).
#trigger_modules = [100, 103, 106, 107, 108, 111, 112, 114, 119, 121, 123, 124, 125]  # all US modules except 110 (central module) and 126 and 115trigger_modules = [100, 103, 106, 107, 108,  112, 114, 119, 121, 123, 124, 125]  # all US modules except 110 (central module) and 126 and 111 and 115
#trigger_modules = [100, 103, 106, 107, 108, 111, 112, 114, 119, 123, 124, 125]
#trigger_modules = [1, 2, 3, 4, 5, 6, 7, 8, 9]
#trigger_modules = [2, 4]
#trigger_modules = [1, 2, 7, 100, 103, 106, 107, 108, 112, 114, 119, 121, 123, 124, 125]  # all modules except 4, 5, 6, 8, 9, 110 (central module), 111, and 115
#trigger_modules = [1, 2, 7, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125]  # all modules except 3, 4, 5, 6, 8, 9, 110 (central module)
#trigger_modules = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] #current All
#trigger_modules = [2, 4, 5, 7, 8, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] #current All except 1, 3, 6, and 9.
#trigger_modules = [2, 7, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] # all US mods + 2 and 7.
#trigger_modules = [2, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] # all US mods + 2 .
#trigger_modules = [2, 4, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] # all US mods + 2, 4.
#trigger_modules = [2, 3, 4, 9, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] # all US mods + 2, 3, 4, 9
# Get info for current run
run_info = get_run_info()

hv_on = False 
tuning_temp = None # Should no longer be necessary
new_tune = True
pmtref4voltage = 2.0 # Old Voltage = 1.25. New voltage = 2.0

# PE scan starts close to the baseline and moves further away
# values in DAC
#pe_thresholds = range(600, 0, -20)
pe_thresholds = range(4050,-50,-50)

# steps of 100 from 600 to 400 and steps of 10 from 350 to 10.
# ! comment out the * TWO * lines below if needed to use the regular steps of 20 above, for e.g., shutter closed or HV off.
#pe_thresholds =  list(np.concatenate([np.arange(600, 350, -50),  np.arange(350, 30, -10)])) #normal
#pe_thresholds =  list(np.concatenate([np.arange(600, 400, -20), np.arange(400, 300, -5), np.arange(300, 100, -2), np.arange(100,0,-10)])) # dense sampling
#pe_thresholds =  list(np.concatenate([np.arange(600, 400, -40), np.arange(400, 100, -5), np.arange(100,0,-10)])) # dense sampling
#pe_thresholds =  list(np.concatenate([np.arange(600, 300, -20),  np.arange(300, 0, -30)])) # for HV off, REGULAR ONE
#pe_thresholds = list(np.concatenate([np.arange(1000, 400, -100), np.arange(400, 0, -30)])) # Testing new PMTRef4 voltage
#pe_thresholds =  list(np.concatenate([np.arange(600, 300, -100),  np.arange(350, 0, -10)]))
#pe_thresholds =  list(np.concatenate([np.arange(600, 300, -100),  np.arange(360, 0, -20)]))
pe_thresholds = [int(i) for i in pe_thresholds]

expected_duration = len([i for i in pe_thresholds if i > 800])*5 + len([i for i in pe_thresholds if 400 < i <= 800])*10 + len([i for i in pe_thresholds if i <= 400])*20 + 3.*60
print("Will scan {} threshold values.\n Expect roughly {:.0f} min.".format(len(pe_thresholds), expected_duration/60.))
start_time = time.time()

#exit()

# Desired data rate in Hz, EXCLUSIVE of any flasher rate
# Ex. if this is 10 with the flasher running at 10 Hz, the target will be 20 Hz

read_temperatures = True
read_currents = False

add_bias = 0  # mV

if os.path.isfile('/home/ctauser/target5and7data/previousRun.txt'):
    print ("Wisconsin previousRun.txt file mounted")
else:
    print ("Wisconsin previousRun.txt file NOT mounted. Exiting")
    exit()

scanner = RateScanner(moduleIDList, trigger_modules,
                      pe_thresholds=pe_thresholds, HVon=hv_on,
                      addBias=add_bias, read_temperatures=read_temperatures,
                      read_currents=read_currents, run_info=run_info, new_tune=new_tune, tuning_temp=tuning_temp, pmtref4voltage=pmtref4voltage)

# module initialization and tuning
#scanner.prepareModules(write_trim_log=True)
scanner.prepareModules(write_trim_log=False)#, italian_bias=4600)

# Sleep time before start of the thresh scan
scanner.sleep(interval=30, num_intervals=1) #Nominal Equilibriation Time
#scanner.sleep(interval=30, num_intervals=10)

vped_default = 1106
#for Vped in range(vped_default, vped_default+(20+1)*5, 5):
for asic in range(0,4):
    for trpixel in range(0,4):
        for Vped in [1106]: #range(1106, 1206, 5):#5):
            #print(Vped,type(Vped))
            scanner.moduleList[0].WriteSetting("Vped_value", Vped) # scan over vped in some sense, name scan files accordingly
            #scanner.thresh_pe_scan(0, 0, Vped)  # asic, trpixel, Vped (for file name)
            scanner.thresh_pe_scan_reg(asic,trpixel,Vped)
scanner.closeMods()

elapsed_time = time.time() - start_time
print("Guessed duration was {} min.".format(expected_duration))
print("Done. Elapsed time: {} s".format(elapsed_time))
