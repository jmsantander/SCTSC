import time
import numpy as np
import powerCycle
import runInit
import IO
import tuneModule
import triggerThresh
import Agilent33600A
import sys
import run_control
import itertools
import datetime
import os

trigger_thresh=100
read_temperatures=True
read_currents=True

datadir = "/Users/ltaylor/test_suite/output/"
testDir = datadir

moduleID = 110
FPM = [4, 12]

bps = powerCycle.powerCycle()
module, tester = runInit.Init()
for asic in range(4):
    for group in range(4):
    	tester.EnableTrigger(asic, group, False)

Vped = 1106
num_blocks = 4
tuneModule.getTunedWrite(moduleID, FPM, module, Vped, numBlock=num_blocks)

run_duration = 5 # s
std_my_ip = "192.168.10.1"
buffer_depth = 50000
deadtime = 15000
trigger_delay = 634 #666 #Increase in trigger delay moves waveforms to the right
std_n_packets_per_event = 64
thresh = [trigger_thresh]*16

'''
# PMTref4 Setting
for asic in range(4):
    for group in range(4):
        module.WriteASICSetting("PMTref4_{}".format(group), asic, 2400, True)
'''

run_num = run_control.incrementRunNumber("/Users/ltaylor/test_suite/")
outfile = "{}/run{}.fits".format(datadir,run_num)


packet_size = 22 + num_blocks * 64
packet_size = int(2 * (10 + (num_blocks * 32 + 1)))
time.sleep(1)
#tester.SetTriggerModeAndType(0b00, 0b00)
tester.SetTriggerDeadTime(deadtime)
#module.WriteSetting("TACK_EnableTrigger",0x0)
#module.WriteSetting("TriggerDelay", trigger_delay)
#module.WriteSetting("TACK_TriggerDead", 100)
time.sleep(1)
    #filename = "test_a{}_g{}.txt".format(asic, group)
    #threshScan(module, asic,group, datadir, 2, filename, pmtref4_start=1300, pmtref4_stop=2100, stepsize=20 )


for asic in range(4):
    for group in range(4):
        module.WriteASICSetting("Thresh_{}".format(group), asic, 0, True)






#tester.SetTriggerModeAndType(0b00, 0b00) #makes sure the internal trigger is used
#tester.SetTriggerDeadTime(deadtime) #deadtime is the time the trigger is disabled after it has sent out data


#fg = Agilent33600A.Agilent33600A()
#real_ampl = 0.01
#ampl = real_ampl
#print("the set amplitude is:", ampl)
#fg.apply_pulse(1.0E3, ampl, 0,80,10,100)

#for asic in range(1,2):
#    for group in range(2,3):
#    	outRunList, outFileList,trigThreshDone = triggerThresh.trigThreshScan(module, tester, moduleID, asic, group, dataset, testDir, numBlock=num_blocks, HV=0, Vped=1106, deadtime=15000, inputf=100, enableReadout=1)





#module.WriteSetting("TACK_EnableTrigger", 0x0) # trigger on pixel 0
#module.WriteSetting("ExtTriggerDirection", 0x0)
#module.WriteSetting("TACK_EnableTrigger",0xffff)

    		
    
module.WriteSetting("Vped_value", Vped)
module.WriteSetting("EnableChannelsASIC0", 0xffff)
module.WriteSetting("EnableChannelsASIC1", 0xffff)
module.WriteSetting("EnableChannelsASIC2", 0xffff)
module.WriteSetting("EnableChannelsASIC3", 0xffff)
module.WriteSetting("Zero_Enable", 0x1)
module.WriteSetting("NumberOfBlocks", num_blocks-1)
module.WriteSetting("TriggerDelay",trigger_delay) #to tell the FPGA how far to look back in time in order to see the actual trigger (acounting for the time it took everything to communicate)


tester.SetTriggerModeAndType(0b00, 0b00) #makes sure the internal trigger is used
tester.SetTriggerDeadTime(deadtime) #deadtime is the time the trigger is disabled after it has sent out data

print("Enable Pulser!")
time.sleep(2)


buf, writer, listener = IO.setUp(std_my_ip, buffer_depth, std_n_packets_per_event,packet_size, outfile)

#tester.EnableTrigger(0, 0, True)
tester.EnableTrigger(1, 2, True)


for asic in range(4):
    for group in range(4):
        module.WriteASICSetting("Thresh_{}".format(group), asic, int(thresh[asic*4+group]), True)


#@staticmethod
def _read_adc_value(module, register, start_bit, num_tries=2, wait_time=0.01):
    """
    Read the value from a register with ADC values, reading part 0 or 1.
    Check that the data are valid,
    and if not try a total of num_tries times,
    waiting wait_time seconds in between each try.
    """
    for __ in range(num_tries):
        ret, value = module.ReadRegister(register)
        bitstring = '{0:032b}'.format(value)[::-1]
        bitstring = bitstring[start_bit:start_bit + 16]
        validation_bit = int(bitstring[15], 2)
        if not ret and validation_bit:
            value = int(bitstring[12::-1], 2)
            return value
        time.sleep(wait_time)
    # Loop exited - no valid value found after all tries completed
    return 0

def read_adc(module):
    """
    Read out the temperature and/or SiPM currents on the auxiliary board
    """
    # Initialize variables
    temperature = np.zeros(4)
    currents = np.zeros((4, 16))
    total_current = 0

    # Activate the MAX1230 ADC
    module.WriteSetting('ADCEnableSelect', 0b1111)
    module.WriteSetting('ADCStart', 1)
    time.sleep(0.1)

    # Read variables
    if read_temperatures:
        for i, (register, start_bit) in enumerate([(0x34, 0), (0x45, 0), (0x34, 16), (0x45, 16)]):
            temperature[i] = _read_adc_value(module, register, start_bit)
        temperature *= 0.125  # Convert raw values to degrees C
    
    if read_currents:
        # Read individual pixel currents
        for asic, channel in itertools.product(range(4), range(16)):
            register = 0x35 + (asic % 2)*17 + channel
            start_bit = 0 if asic in [0, 1] else 16
            value = _read_adc_value(module, register, start_bit)
            currents[asic, channel] = value
        currents *= 0.5  # Convert raw values to uA
        # Read total current
        total_current = _read_adc_value(module, 0x2a, 0)
    
    # Deactivate the MAX1230 ADC
    # It's important to deactivate this element when not in use,
    # because it introduces noise into the trigger path
    module.WriteSetting('ADCEnableSelect', 0)
    module.WriteSetting('ADCStart', 1)
    time.sleep(0.1)

    return temperature, currents, total_current


def read_all_adcs():
    """
    Read temperatures and/or SiPM currents from all modules
    """
    temperatures = []
    sipm_currents = []
    reopen_mask = False
    timestamp_start = datetime.datetime.utcnow().isoformat()
    #if close_trigger_mask and self._trigger_mask_is_open:
    #    self.close_trigger_mask()
    #    reopen_mask = True
    #for module_id, module in zip(self.moduleIDList, self.moduleList):
    
    temperature, currents, total_current = read_adc(module)
    if read_temperatures:
        # Log all four ADC temperature readings to file
        temperatures.extend(temperature)
        # For display, ignore broken sensors and average the readings
        lower_limit = 4  # degrees C
        upper_limit = 125  # degrees C
        good_temperatures = temperature[(temperature > lower_limit) & (temperature < upper_limit)]
        if good_temperatures.size > 0:
            print("\nTemperature in module {} is {:.2f} C".format(moduleID, np.mean(good_temperatures)))
        else:
            print("\nNo good temperatures in module {}".format(moduleID))
    if read_currents:
        # Log all current readings to file
        sipm_currents.append(total_current)
        sipm_currents.extend(currents.flatten())
        # For display, ignore broken sensors
        lower_limit = 0  # uA
        upper_limit = 2000  # uA
        good_currents = currents[(currents > lower_limit) & (currents < upper_limit)]
        print("Total current in module {}: {} uA".format(moduleID, total_current))
        if good_currents.size > 0:
            print("\nPixel currents in module {} (uA): {}".format(moduleID, currents))
        else:
            print("\nNo good pixel currents in module {}".format(moduleID))
    #if close_trigger_mask and reopen_mask:
    #    self.open_trigger_mask()
    timestamp_end = datetime.datetime.utcnow().isoformat()
    

    # Log the values to files
    if read_temperatures:
        temperature_filename = "{}_temperatures.txt".format(run_num)
        temperature_file = os.path.join(datadir, temperature_filename)
        with open(temperature_file, 'w') as f:
            sensor_names = ["{}_ADC{}".format(moduleID, i) for i in range(4)]
            f.write("timestamp_start,timestamp_end,{}\n".format(','.join(sensor_names)))
        with open(temperature_file, 'a') as f:
            temps_string = ','.join([str(temp) for temp in temperatures])
            f.write("{},{},{}\n".format(timestamp_start, timestamp_end, temps_string))
    if read_currents:
        currents_filename = "{}_currents.txt".format(run_num)
        currents_file = os.path.join(datadir, currents_filename)
        with open(currents_file, "w") as f:
            pixels = ['global'] + list(range(64))
            pixel_names = ["{}_pixel{}".format(moduleID, pixel) for pixel in pixels]
            f.write("timestamp_start,timestamp_end,{}\n".format(','.join(pixel_names))) 
        with open(currents_file, 'a') as f:
            currs_string = ','.join([str(curr) for curr in sipm_currents])
            f.write("{},{},{}\n".format(timestamp_start, timestamp_end, currs_string))
    return temperatures, sipm_currents

temps, currents = read_all_adcs()
#print(temps)
#print(currents)

writer.StartWatchingBuffer(buf)
time.sleep(run_duration)
writer.StopWatchingBuffer()
#tester.EnableTrigger(0, 0, False)
tester.EnableTrigger(0, 2, False)


#fg.send_cmd("OUTPut1 OFF")
#fg.close

for asic in range(4):
    for group in range(4):
        module.WriteASICSetting("Thresh_{}".format(group), asic, 0, True)

IO.stopData(listener, writer)

powerCycle.powerOff(bps)

print('********************')
print('**** Run {} ****'.format(run_num))
print('********************')
