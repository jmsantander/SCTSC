from psct_toolkit import RateScanner
from run_info import get_run_info, get_rate_scan_results
import numpy as np
import time, os


#moduleIDList = [2]
moduleIDList = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] #current All
#moduleIDList = [100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] #current US
#moduleIDList = [1, 2, 3, 4, 5, 6, 7, 8, 9] #current INFN

#trigger_modules = [2]
#trigger_modules = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126] #current All
#trigger_modules = [100, 103, 106, 107, 108, 111, 112, 114, 115, 119, 121, 123, 124, 125, 126]  # all US modules except 110 (central module).
trigger_modules = [1, 2, 3, 4, 5, 6, 7, 8, 9] #current INFN

# Get info for current run
run_info = get_run_info()

#hv_on = False #True
hv_on = True
tuning_temp = None # Should no longer be necessary
new_tune = True
pmtref4voltage = 2.0 # Old Voltage = 1.25. New voltage = 2.0
n_hitmaps = 100
retry = True
n_retry = 3
scan_type = "thresh" #"pe" OR "thresh"

# PE scan starts close to the baseline and moves further away
# values in DAC
#pe_thresholds = range(750, -5, -5) #Use with scan_type "thresh"
pe_thresholds = range(1000, -100, -100) #Use with scan_type "thresh"
#pe_thresholds = range(1000, -100, -100) #Use with scan_type "thresh"
pe_thresholds = [int(i) for i in pe_thresholds] #this is for the fixed threshold
#pe_thresholds = list(np.arange(35, 15, -0.5)) #Use with scan_type "pe"

# steps of 100 from 600 to 400 and steps of 10 from 350 to 10. 
# ! comment out the * TWO * lines below if needed to use the regular steps of 20 above, for e.g., shutter closed or HV off. 
#pe_thresholds =  list(np.concatenate([np.arange(600, 350, -50),  np.arange(350, 30, -10)])) #normal
#pe_thresholds =  list(np.concatenate([np.arange(600, 400, -20), np.arange(400, 300, -5), np.arange(300, 100, -2), np.arange(100,0,-10)])) # dense sampling 
#pe_thresholds =  list(np.concatenate([np.arange(600, 400, -40), np.arange(400, 100, -5), np.arange(100,0,-10)])) # dense sampling 
#pe_thresholds =  list(np.concatenate([np.arange(600, 300, -20),  np.arange(300, 0, -30)])) # for HV off, REGULAR ONE
#pe_thresholds = list(np.concatenate([np.arange(1000, 400, -100), np.arange(400, 0, -30)])) # Testing new PMTRef4 voltage
#pe_thresholds =  list(np.concatenate([np.arange(600, 300, -100),  np.arange(350, 0, -10)])) 
#pe_thresholds =  list(np.concatenate([np.arange(600, 300, -100),  np.arange(360, 0, -20)])) 




expected_duration = (len(pe_thresholds)*(6+n_hitmaps*0.1)+8*60)/60.
print("Will scan {} threshold values and get {} hit maps for each thesh.\n Expect roughly {:.0f} min.".format(len(pe_thresholds), n_hitmaps, (len(pe_thresholds)*(6+n_hitmaps*0.1)+8*60)/60.))
start_time = time.time()

#exit()

# Desired data rate in Hz, EXCLUSIVE of any flasher rate
# Ex. if this is 10 with the flasher running at 10 Hz, the target will be 20 Hz
desired_rate = 0

read_temperatures = True
read_currents = False

add_bias = 0  # mV

if os.path.isfile('/home/ctauser/target5and7data/previousRun.txt'):
    print ("Wisconsin previousRun.txt file mounted")
else:
    print ("Wisconsin previousRun.txt file NOT mounted. Exiting")
    exit()

scanner = RateScanner(moduleIDList, trigger_modules, retry=retry, n_retry=n_retry,
                      pe_thresholds=pe_thresholds, HVon=hv_on,
                      n_hitmaps=n_hitmaps, 
                      addBias=add_bias, read_temperatures=read_temperatures,
                      read_currents=read_currents, run_info=run_info, new_tune=new_tune, 
                      tuning_temp=tuning_temp, pmtref4voltage=pmtref4voltage, scan_type=scan_type)

# module initialization and tuning
#scanner.prepareModules(write_trim_log=True)
scanner.prepareModules(write_trim_log=True)#, italian_bias=4600)

# Sleep time before start of the thresh scan
scanner.sleep(interval=30, num_intervals=10) #Nominal Equilibriation Time
#scanner.sleep(interval=30, num_intervals=2)
scanner.update_tuning()

scanner.peScan()

scanner.closeMods()

# Calculate the threshold that gives the desired rate
flasher_rate = run_info['flasher_rate'] if run_info['flasher_on'] else 0
print(get_rate_scan_results(scanner.run_id, desired_rate=desired_rate,
                            flasher_rate=float(flasher_rate)))
# Also detect the flasher plateau as a sanity check if applicable
if run_info['flasher_on']:
    plateau = get_rate_scan_results(scanner.run_id, desired_rate=flasher_rate)
    print("Flasher: ", plateau)

elapsed_time = time.time() - start_time
print("Guessed duration was {} min.".format(expected_duration))
print("Done. Elapsed time: {} s".format(elapsed_time))

