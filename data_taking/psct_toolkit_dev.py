import datetime
import itertools
import os
import pickle
import subprocess
import sys
import time

import pandas as pd
import numpy as np
import yaml
from shutil import copyfile

import target_driver
import target_io
import h5py
import piCom
import run_control
from tuneModule import doTunedWrite, getTunedWrite

class PsctTool():
    """
    An object possessing the basic attributes for any test setup. It contains the subclasses:
        DataTaker: perform readout on camera
        TriggerTester: perform scans measuing only triggers with no readout
    """

    # DACQ subnet IP addresses
    subnet_port_ip = {10: "192.168.10.1", 12: "192.168.12.1",
                      14: "192.168.14.1", 16: "192.168.16.1"}

    board_def = "/data/software/CCC/TargetDriver/branches/issue37423/config/T7_M_FPGA_Firmware0xB0000107.def"
    asic_def = "/data/archive/TargetDriver_new/config/T7_ASIC.def"

    num_asic = 4
    num_groups_per_asic = 4
    num_channels_per_asic = 16
    groupsPerMod = num_asic * num_groups_per_asic

    # ASIC settings (Leslie)
    asic_settings = {'WR_ADDR_Incr1LE_Delay': 3,
                     'WR_ADDR_Incr1TE_Delay': 18,
                     'WR_STRB1LE_Delay': 37,
                     'WR_STRB1TE_Delay': 44,
                     'WR_ADDR_Incr2LE_Delay': 35,
                     'WR_ADDR_Incr2TE_Delay': 50,
                     'WR_STRB2LE_Delay': 0,
                     'WR_STRB2TE_Delay': 7,
                     'SSPinLE_Delay': 55,
                     'SSPinTE_Delay': 63}

    outdir = "/data/local_outputDir"
    run_control_dir = "/home/ctauser/target5and7data"

    logfile = "/home/ctauser/run_log.pkl"  # Temporary logging solution until we have a database

    def __init__(self, moduleIDList, trigger_modules, HVon, numBlock=2,
                 addBias=0, static_threshold_us=None, static_threshold_infn=None, 
                 pe_threshold_us=None, pe_threshold_infn=None, read_temperatures=False,
                 read_currents=False, retry=False, n_retry=1, tuning_temp=None, new_tune=False,
                 pmtref4voltage=1.25):
        # Load module configuration
        fpm_config = pd.read_csv("FPM_config.csv")
        fee_config = pd.read_csv("FEE_config.csv")
        self.moduleIDList = moduleIDList
        print("Loading tuning temps from file tuning_temps.yml")
        if os.path.exists("tuning_temps.yml"):
            with open("tuning_temps.yml", "r") as inf_:
                self.tuning_temps = yaml.safe_load(inf_)
            if self.tuning_temps is None:
                self.tuning_temps = {}
        else:
            self.tuning_temps = {}

        if HVon:
            masked_tr_pix_file = "masked_trigger_pixels_HVon.yml"
        else:
            masked_tr_pix_file = "masked_trigger_pixels_HVoff.yml"
        print("Loading masked trigger pixels from file {}...".format(masked_tr_pix_file))
        with open(masked_tr_pix_file, 'r') as pixels_file:
            self.masked_trigger_pixels = yaml.safe_load(pixels_file)
        #self.masked_trigger_pixels = None #FIXME
        if self.masked_trigger_pixels is None:
            self.masked_trigger_pixels = {}
        # Determine module network settings
        self.board_IPs = {}
        self.subnets = {}
        for mod_id in self.moduleIDList:
            loc = (fee_config.module_id == mod_id)
            self.board_IPs[mod_id] = fee_config.ip_address.loc[loc].values[0]
            self.subnets[mod_id] = fee_config.dacq_subnet.loc[loc].values[0]
        # Determine trigger mask positions
        # The first seven (32 - 25) trigger mask positions are never used
        self.trigger_mask_position = [None, None, None, None, None, None, None]
        self.trigger_mask_position.extend([mod_id for pos, mod_id in sorted(zip(
            fpm_config.trigger_mask_position, fpm_config.module_id))])
        # Determine slots for powering modules
        self.power_slots = {mod_id: slot for slot, mod_id
                            in zip(fpm_config.slow_control_slot,
                                   fpm_config.module_id)}
        self.moduleList = []
        self.trigger_modules = trigger_modules
        #self.VpedList = [1106]*len(self.moduleIDList) #MAX
        #try to assign different vped in case of italian and us modules #MAX
        VpedList = []
        for module in self.moduleIDList:
            if module in range(10):
                VpedList.append(1106)
            else:
                VpedList.append(1106)
        self.VpedList = VpedList
        self.HVon = HVon
        self.numBlock = numBlock
        self.addBias = addBias
        self.holdOff = "c350"

        if static_threshold_us is None:
            static_threshold_us = [750] * self.groupsPerMod #roughly around 100Hz trigger
        self.staticThresh_us = static_threshold_us
        
        if static_threshold_infn is None:
            static_threshold_infn = [250] * self.groupsPerMod #roughly around 10Hz trigger
        self.staticThresh_infn = static_threshold_infn

        if pe_threshold_us is None:
            pe_threshold_us = [30.] * 16
        self.peThresh_us = pe_threshold_us
        
        if pe_threshold_infn is None:
            pe_threshold_infn = [21.] * 16
        self.peThresh_infn = pe_threshold_infn

        self.pi = piCom.executeConnection()
        self.failed_modules = []
        self._trigger_mask_is_open = False

        self.run_id = None
        self.read_temperatures = read_temperatures
        self.read_currents = read_currents
        self.write_temperatures = read_temperatures
        self.write_currents = read_currents
        self.temperature_file = None
        self.currents_file = None
        self.registers_file = None

        self.origin_timestamp = None
        self.run_timestamp = None

        self.retry = retry
        self.n_retry = n_retry
        self.pmtref4voltage = pmtref4voltage


    def initModules(self):
        """
        Initialize modules
        """

        # Power on all modules
        # by powering an additional module with each iteration
        # Do not power all modules on at once,
        # the backplane can't deliver that much power!
        slots = []
        
        for module_id in self.moduleIDList:
            slots.append(self.power_slots[module_id])
            piCom.powerFEE(self.pi, slots)
            time.sleep(0.5)

        time.sleep(25)

        self.establishConnections(self.moduleIDList)

        if(self.retry is True):
            if(self.failed_modules!=[]):
                for i in range(self.n_retry):
                    print("Retry attempt: {}".format(i+1))
                    slots=[]
                    for module_id in self.moduleIDList:
                        slots.append(self.power_slots[module_id])
                        piCom.powerFEE(self.pi, slots)
                        time.sleep(0.5)
    
                    time.sleep(25)
                        
                    self.establishConnections(self.moduleIDList)
                        
                    if(self.failed_modules==[]):
                        break
        """
        if(self.retry is True):
            if(self.failed_modules!=[]):
                for i in range(self.n_retry):
                    print("Retry attempt ", i)
                    slots_connected = []
                    for modID in self.connected_modules:
                        slots_connected.append(self.power_slots[modID])
                    
                    slots = slots_connected
                    piCom.powerFEE(self.pi, slots)
                    time.sleep(3)
                    
                    for module_id in self.failed_modules:
                        slots.append(self.power_slots[module_id])
                        piCom.powerFEE(self.pi, slots)
                        time.sleep(0.5)
                    
                    time.sleep(25)
        
                    self.establishConnections(self.failed_modules)
                    
                    if(self.failed_modules==[]):
                        break
                

           """        
        
        print("\n***** Setting ASIC params")
        time.sleep(1)

        self.setASICParams()
        time.sleep(3)

        # Match up the system time as closely as possible to
        # the origin of the backplane time
        # This is approximate, mostly due to network latency
        time1 = datetime.datetime.utcnow()
        piCom.sendClockReset(self.pi)
        time2 = datetime.datetime.utcnow()
        self.origin_timestamp = time1 + (time2 - time1) / 2
        print("SYNCING NOW")
        #piCom.sendClockReset(self.pi)
        time.sleep(1)
        piCom.sendSync(self.pi)
        time.sleep(5)

        self.modsToReady()


        # Require that at least one module connected
        # This is a good setting for testing
        # but a little liberal for observing
        if len(self.failed_modules) >= len(self.moduleList):
            print("Connection not established!")
            print("Exit data taking!")
            sys.exit()

    # Read registers 0x2 and 0x3 for 2 hex strings - used to identify FEE ID
    @staticmethod
    def queryBoard(module, address):
        hexAddress = "0x%02x" % address
        ret, value = module.ReadRegister(address)
        hexValue = "0x%08x" % value

        return hexValue

    def establishConnections(self, IDList):
        self.failed_modules = []
        self.connected_modules = []
        for i, moduleID in enumerate(IDList):
            #First check if moduleID is already in moduleIDList. If so, pop that index out of moduleList

            if len(self.moduleList) > i:
                idx = self.moduleIDList.index(moduleID)
                self.moduleList.pop(idx)
                self.moduleList.insert(idx,
                    target_driver.TargetModule(PsctTool.board_def,
                                           PsctTool.asic_def, idx))

            else:
                idx = i

                self.moduleList.append(
                    target_driver.TargetModule(PsctTool.board_def,
                                           PsctTool.asic_def, idx))
            subnet_ip = self.subnet_port_ip[self.subnets[moduleID]]
            board_ip = self.board_IPs[moduleID]

            print("My IP is: {} for module: {}, with board IP {}".format(
                subnet_ip, moduleID, board_ip))

            fail = self.moduleList[idx].EstablishSlowControlLink(subnet_ip,
                                                               board_ip)
            if fail:
                print("Failed to establish slow control connection, with: {}".format(fail))
                self.failed_modules.append(moduleID)
            else:
                self.connected_modules.append(moduleID)
                port = np.uint16(0)
                dataPort = np.uint16(0)
                regVal = 0
                time.sleep(0.2)
                regVal = self.moduleList[idx].ReadRegister(0x80)
                port = (regVal[1] >> 16) & 0xFFFF
                dataPort = (regVal[1]) & 0xFFFF
                print("Slow control connection established with slow control port: {} and data port: {}".format(port, dataPort))

                address = 0x02  # LSW of serial code
                hexLSW = self.queryBoard(self.moduleList[idx], address)
                address = 0x03  # MSW of serial code
                hexMSW = self.queryBoard(self.moduleList[idx], address)
                serialCode = "{}{}".format(hexMSW, hexLSW[2:10])
                print("The module serial number is: {}".format(serialCode))

                # integer values to identify modules
                self.moduleList[i].WriteSetting("DetectorID", idx)
                self.moduleList[i].WriteSetting("CTAID", moduleID)
                time.sleep(1)

        time.sleep(3)

        for ID in IDList:
            idx = self.moduleIDList.index(ID)


            module = self.moduleList[idx]
        #for module in self.moduleList:
            state = module.GetState()
            print("Module state: {}".format(state))
            time.sleep(0.2)

            TC_OK = module.GoToPreSync()
            print("Module into PreSync with return: {}".format(TC_OK))

            time.sleep(0.2)
            state = module.GetState()
            time.sleep(0.2)
            print("Module state: {}".format(state))

    def modsToReady(self):
        for module in self.moduleList:
            fail = module.GoToReady()
            print("Failed:? {}".format(fail))
            if fail:
                print("MODULE FAILED \"GO TO READY\"")

        for module in self.moduleList:
            state = module.GetState()
            print("Module state: {}".format(state))

    def closeMods(self):
        """
        Closes connection to all modules and powers them off
        """
        for module in self.moduleList:
            module.CloseSockets()
        piCom.powerFEE(self.pi, None)

    def open_trigger_mask(self):
        piCom.setTriggerMask(self.pi)
        self._trigger_mask_is_open = True

    def close_trigger_mask(self):
        piCom.setTriggerMaskClosed(self.pi)
        self._trigger_mask_is_open = False

    def setASICParams(self):
        for module in self.moduleList:
            time.sleep(0.1)
            for asic in range(PsctTool.num_asic):
                for setting, value in self.asic_settings.items():
                    module.WriteASICSetting(setting, asic, value)

    def peddac_to_pedmV(self,peddac,a_ped,b_ped):
        """
        Conversion from DAC to mV for Vped
        """
        return a_ped*peddac + b_ped

    def pe_to_adc(self,pe, gain_INFN, gain_US, module_type="INFN"):
        """
        gain in ADC/pe
        """
        if module_type=="INFN":
            gain = gain_INFN
        if module_type=="US":
            gain = gain_US
        #print(type(pe))
        #print(type(gain))
        return pe*gain #integration window=16ns
    
    def adc_to_mV(self,pe_adc, mv_per_adc=0.5):
        return pe_adc*mv_per_adc
    
    def pe_to_mV(self,pe, gain_INFN, gain_US, module_type="INFN", conversion="photostat"):
        """
        conversion==photostat --> gain in ADC/pe. WARNING: check that gain is not in ADC*ns/pe
        conversion==nominal --> gain in mV/pe
        """
        if conversion=="nominal":
            if module_type=="INFN":
                return pe*gain_INFN
            if module_type=="US":
                return pe*gain_US
        if conversion=="photostat":
            return self.adc_to_mV(self.pe_to_adc(pe,gain_INFN,gain_US,module_type))
    
    def mV_to_threshdac(self,mV, a, b):
        """
        mV to thresh DAC conversion
        """
        return a*mV + b
    
    def pe_to_threshdac(self,pe,vped_dac,a_ped,b_ped,gain_INFN,gain_US,a,b,module_type="INFN",conversion="photostat"):
        
        vped_mV = self.peddac_to_pedmV(vped_dac,a_ped,b_ped)
    
        if module_type=="INFN":
            gain = gain_INFN
        if module_type=="US":
            gain = gain_US
        
        pe_mV = self.pe_to_mV(pe,gain_INFN,gain_US,module_type,conversion)
        mV = vped_mV + pe_mV/4 #single p.e. per trigger pixel
    
        pe_threshdac = self.mV_to_threshdac(mV,a,b) 
        
        return np.round(pe_threshdac)
    
    def setStaticThresh(self, moduleID, staticThresh=None):
        """
        Sets a static threshold value for all groups and asics of any module
        using a list.
        """

        if staticThresh is None:
            staticThresh = self.staticThresh
            
        #print("staticThresh",staticThresh)

        # if all Thresh vals are the same, suppress output for individual groups
        same_thresh = len(set(staticThresh)) <= 1

        module = self.moduleList[self.moduleIDList.index(moduleID)]
        for i in range(PsctTool.num_asic):
            for j in range(PsctTool.num_groups_per_asic):
                #print(j,i,int(staticThresh[i*4 + j]))
                module.WriteASICSetting("Thresh_{}".format(j), i,
                                        int(staticThresh[i*4 + j]), True)
                if not same_thresh:
                    print("ModID: {}, ASIC: {}, Group: {}, Thresh: {}".format(
                        moduleID, i, j, int(staticThresh[i*4 + j])))
        if same_thresh:
            print("ModID: {}, Thresh: {}".format(moduleID, int(staticThresh[0])))
            
    def setPeThresh(self, moduleID, peThresh=None, vped_dac=1106, a_ped=0.609, 
                    b_ped=26.25, gain_INFN=300./16, gain_US=190./16, a=-46.1957, 
                    b=35140.4259, conversion="photostat"):
        """
        Calculates a static threshold value for all groups and asics of any module
        from a pe threshold.
        """

        if peThresh is None:
            peThresh = self.peThresh
        #print(type(peThresh))
        if (peThresh[0]<0):
            print("Warning: p.e. value < 0!!! Setting to 0")
            peThresh = [0]*16
        INFN = range(1, 9 + 1)
        if moduleID in INFN:
            module_type="INFN"
            pe_thresh = self.pe_to_threshdac(np.asarray(peThresh,dtype=float),vped_dac,a_ped,b_ped,gain_INFN,gain_US,a,b,
                                        module_type=module_type,conversion=conversion) 
        else:
            module_type="US"
            pe_thresh = self.pe_to_threshdac(np.asarray(peThresh,dtype=float),vped_dac,a_ped,b_ped,gain_INFN,gain_US,a,b,
                                        module_type=module_type,conversion=conversion)
        
        #note: for as it is called in peScan(), thresh list is a list containing 16 equal thresh values for each trigger pixel
        #of an entire module. Hence, it is sufficient to check the 1st element
        if pe_thresh[0] > 4095:
            print("Warning: p.e. thresh value > 4095!!! Setting to 4095")
            pe_thresh = [4095]*16
        if pe_thresh[0] < 0:
            print("Warning: p.e. thresh value < 0!!! Setting to 0")
            pe_thresh = [0]*16
        print("ModID: {}, Thresh (p.e.): {}".format(moduleID, peThresh[0]))
        self.setStaticThresh(moduleID, list(pe_thresh))

    def setAllThreshHigh(self, modID):
        """
        Sets the effective threshold of a module very high (far from the baseline)
        """
        modInd = self.moduleIDList.index(modID)
        print("\nSetting threshold HI for module {}\n".format(modID))
        for i in range(PsctTool.num_asic):
            for j in range(PsctTool.num_groups_per_asic):
                self.moduleList[modInd].WriteASICSetting("Thresh_{}".format(j), i, 0, True)

    def setTuning(self, write_log=None, italian_bias=0, flat_trims=-1):
        """
        Set offset voltages on trigger path, numBlock, and HV values for FPMs
        If italian_bias is not 0, bias the italians
        """
        for module_id, module, Vped in zip(self.moduleIDList, self.moduleList,
                                           self.VpedList):
            if italian_bias > 0 and module_id < 10:
                add_italian_bias = italian_bias
                print("Adding additional bias {} mV to italian module {}".format(italian_bias, module_id))
            else:
                add_italian_bias = 0
            if self.new_tune is True:
                #doTunedWrite(module_id, module, Vped, self.HVon, self.tuning_temp,
                if module_id in self.tuning_temps:
                    this_temp = self.tuning_temps[module_id]
                else:
                    this_temp = self.tuning_temp
                    self.tuning_temps[module_id] = this_temp #for logging
                print("tuning temp for module {} set to {} deg C".format(module_id, this_temp))
                doTunedWrite(module_id, module, Vped, self.HVon, this_temp,
                            numBlock=self.numBlock, addBias=(self.addBias+add_italian_bias), write_log=write_log,
                            pmtref_4_voltage=self.pmtref4voltage, flat_trims=flat_trims)
            else:
                getTunedWrite(module_id, module, Vped, HV=self.HVon,
                              numBlock=self.numBlock, addBias=(self.addBias+add_italian_bias), write_log=write_log)

    def prepareModules(self, write_trim_log=False, italian_bias=0, flat_trims=-1):
        """
        Performs basic setup for any test:
            1. Power the modules off
            2. Write the trigger mask file
            3. Prepare the Pi for slow control connection
            4. Initialize the modules
            5. Ping the data ports to keep the connection alive
            6. Set the voltage values for the trigger tuning and trim voltages
        """
        print("\n***** Power off all modules")
        time.sleep(1)
        piCom.powerFEE(self.pi, None)
        time.sleep(5)

        print("\n**** Writing the trigger mask file")
        self.write_trigger_mask()

        print("\n***** Preparing Pi for slow control communication")
        time.sleep(1)
        piCom.setHoldOff(self.pi, "{}".format(self.holdOff))
        time.sleep(0.5)
        piCom.enableTACK(self.pi)
        time.sleep(1)

        print("\n***** Powering modules on and initializing")
        time.sleep(1)
        self.initModules()
        time.sleep(1)

        # Make sure dataport connection is not lost.
        # Added by Thomas, 05-27-2018
        print("\n**** Pinging the data ports")
        for module in self.moduleList:
            module.DataPortPing()

        print("\n***** Setting the trigger tuning and trim voltage values for modules")
        time.sleep(1)

        self.tmp_trim_voltage_file = None

        if write_trim_log and self.HVon:
            #this is done before the run_id gets assigned...
            #trim_voltage_filename = "{}_trim_voltages.txt".format(self.run_id)
            #self.trim_voltage_file = os.path.join(self.outdir,
            #                                     trim_voltage_filename)
            tmp_trim_voltage_filename = "tmp_trim_voltages.txt"
            self.tmp_trim_voltage_file = os.path.join(self.outdir,
                                                 tmp_trim_voltage_filename)
            self.setTuning(write_log=self.tmp_trim_voltage_file, italian_bias=italian_bias, flat_trims=flat_trims)
        else:
            self.setTuning()
        time.sleep(1)

    def initialize_run(self):
        """
        Define a run number and set up files for the current run
        """
        self.run_id = run_control.incrementRunNumber(self.run_control_dir)

        print("Writing to directory: {}".format(self.outdir))
        os.makedirs(self.outdir, exist_ok=True)

        if self.tmp_trim_voltage_file is not None and self.HVon:
            trim_voltage_filename = "{}_trim_voltages.txt".format(self.run_id)
            self.trim_voltage_file = os.path.join(self.outdir,
                                              trim_voltage_filename)
            copyfile(self.tmp_trim_voltage_file, self.trim_voltage_file)
            os.remove(self.tmp_trim_voltage_file)


        if self.read_temperatures:
            temperature_filename = "{}_temperatures.txt".format(self.run_id)
            self.temperature_file = os.path.join(self.outdir,
                                                 temperature_filename)
            with open(self.temperature_file, 'w') as f:
                sensor_names = ["{}_ADC{}".format(module_id, i)
                                for module_id in self.moduleIDList
                                for i in range(4)]
                f.write("timestamp_start,timestamp_end,{}\n".format(
                    ','.join(sensor_names)))

        if self.read_currents:
            currents_filename = "{}_currents.txt".format(self.run_id)
            self.currents_file = os.path.join(self.outdir, currents_filename)
            with open(self.currents_file, 'w') as f:
                pixels = ['global'] + list(range(64))
                pixel_names = ["{}_pixel{}".format(module_id, pixel)
                               for module_id in self.moduleIDList
                               for pixel in pixels]
                f.write("timestamp_start,timestamp_end,{}\n".format(
                    ','.join(pixel_names)))

        registers_filename = "{}_registers.txt".format(self.run_id)
        self.registers_file = os.path.join(self.outdir, registers_filename)
        self.log_registers()

        self.run_timestamp = datetime.datetime.utcnow()

    @staticmethod
    def _read_adc_value(module, register, start_bit, num_tries=2,
                        wait_time=0.01):
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

    def read_adc(self, module):
        """
        Read out the temperature and/or SiPM currents on the auxiliary board
                print(self.__dict__.keys())
        """
        # Initialize variables
        temperature = np.zeros(4)
        currents = np.zeros((self.num_asic, self.num_channels_per_asic))
        total_current = 0

        # Activate the MAX1230 ADC
        module.WriteSetting('ADCEnableSelect', 0b1111)
        module.WriteSetting('ADCStart', 1)
        time.sleep(0.1)

        # Read variables
        if self.read_temperatures:
            for i, (register, start_bit) in enumerate([(0x34, 0), (0x45, 0),
                                                       (0x34, 16), (0x45, 16)]):
                temperature[i] = self._read_adc_value(module, register,
                                                      start_bit)
            temperature *= 0.125  # Convert raw values to degrees C
        if self.read_currents:
            # Read individual pixel currents
            for asic, channel in itertools.product(
                    range(self.num_asic), range(self.num_channels_per_asic)):
                register = 0x35 + (asic % 2)*17 + channel
                start_bit = 0 if asic in [0, 1] else 16
                value = self._read_adc_value(module, register, start_bit)
                currents[asic, channel] = value
            currents *= 0.5  # Convert raw values to uA
            # Read total current
            total_current = self._read_adc_value(module, 0x2a, 0)

        # Deactivate the MAX1230 ADC
        # It's important to deactivate this element when not in use,
        # because it introduces noise into the trigger path
        module.WriteSetting('ADCEnableSelect', 0)
        module.WriteSetting('ADCStart', 1)
        time.sleep(0.1)

        return temperature, currents, total_current

    def read_all_adcs(self, close_trigger_mask):
        """
        Read temperatures and/or SiPM currents from all modules
        """
        temperatures = []
        sipm_currents = []
        reopen_mask = False
        timestamp_start = datetime.datetime.utcnow().isoformat()
        if close_trigger_mask and self._trigger_mask_is_open:
            self.close_trigger_mask()
            reopen_mask = True
        for module_id, module in zip(self.moduleIDList, self.moduleList):
            temperature, currents, total_current = self.read_adc(module)
            if self.read_temperatures:
                # Log all four ADC temperature readings to file
                temperatures.extend(temperature)
                # For display, ignore broken sensors and average the readings
                lower_limit = 4  # degrees C
                upper_limit = 125  # degrees C
                good_temperatures = temperature[(temperature > lower_limit) &
                                                (temperature < upper_limit)]
                if good_temperatures.size > 0:
                    print("\nTemperature in module {} is {:.2f} C".format(
                        module_id, np.mean(good_temperatures)))
                else:
                    print("\nNo good temperatures in module {}".format(
                        module_id))
            if self.read_currents:
                # Log all current readings to file
                sipm_currents.append(total_current)
                sipm_currents.extend(currents.flatten())
                # For display, ignore broken sensors
                lower_limit = 0  # uA
                upper_limit = 2000  # uA
                good_currents = currents[(currents > lower_limit) &
                                         (currents < upper_limit)]
                print("Total current in module {}: {} uA".format(module_id,
                                                                 total_current))
                if good_currents.size > 0:
                    print("\nPixel currents in module {} (uA): {}".format(
                        module_id, currents))
                else:
                    print("\nNo good pixel currents in module {}".format(
                        module_id))
        if close_trigger_mask and reopen_mask:
            self.open_trigger_mask()
        timestamp_end = datetime.datetime.utcnow().isoformat()
        # Log the values to files
        if self.write_temperatures:
            with open(self.temperature_file, 'a') as f:
                temps_string = ','.join([str(temp) for temp in temperatures])
                f.write("{},{},{}\n".format(timestamp_start, timestamp_end,
                                            temps_string))
        if self.write_currents:
            with open(self.currents_file, 'a') as f:
                currs_string = ','.join([str(curr) for curr in sipm_currents])
                f.write("{},{},{}\n".format(timestamp_start, timestamp_end,
                                            currs_string))
        return temperatures, sipm_currents

    def _read_tacks(self):
        # Read TACKs from an arbitrary module, since it's the same for all
        tack_module = self.moduleList[0]
        num_tacks = np.uint16(tack_module.ReadRegister(0xf)[1] & 0xffff)
        return num_tacks

    def write_trigger_mask(self):
        # Write the trigger mask file
        with open("trigger_mask", 'w') as maskfile:
            for module in self.trigger_mask_position:
                if module is not None and module in self.trigger_modules:
                    bits = ['0'] * 16
                    masked_pixels = self.masked_trigger_pixels.get(module, [])
                    for pixel in masked_pixels:
                        bits[pixel] = '1'
                    bits.reverse()
                    bitmask = ''.join(bits)
                    # Convert to hexadecimal string (with no leading '0x')
                    maskfile.write('{:0>4x}\n'.format(int(bitmask, 2)))
                else:
                    maskfile.write('ffff\n')
        # Copy the trigger mask file to the Pi and delete the local copy
        filepath = "/home/pi/Desktop/BP_SPI_interface/trigger_mask"
        subprocess.run("scp trigger_mask pi@172.17.2.6:{}".format(filepath),
                       shell=True)
        os.remove("trigger_mask")

    def log_registers(self):
        with open(self.registers_file, 'w') as logger:
            for module_id, module in zip(self.moduleIDList, self.moduleList):
                logger.write("******** Module {}\n".format(module_id))
                logger.write("**** FPGA Register addresses\n")
                for addr in range(129):
                    ret, val = module.ReadRegister(addr)
                    hexVal = "0x%08x" % val
                    hexAddr = "0x%02x" % addr
                    currentTime = datetime.datetime.utcnow()
                    line = "{}\t{}\t{}\n".format(currentTime, hexAddr, hexVal)
                    logger.write(line)
                logger.write("\n")

    def sleep(self, interval=30, num_intervals=10):
        for ping in range(num_intervals):
            print("Sleeping for {} seconds ({}/{})".format(interval,
                                                           ping + 1,
                                                           num_intervals))
            time.sleep(interval)
            for module in self.moduleList:
                module.DataPortPing()

    def update_tuning(self, flat_trims=-1):
        temp_temp_bool = self.write_temperatures
        self.write_temperatures = False
        temp_current_bool = self.write_currents
        self.write_currents = False
        temp_temp_temp_bool = self.read_temperatures  # Someone made me play a stupid game, congrats, here's a stupid prize - BM
        self.read_temperatures = True
        temps, _ = self.read_all_adcs(True)
        temps = np.asarray(temps)
        print(temps)
        avg_temps = [np.mean(temps[i*4:i*4+4][temps[i*4:i*4+4] > 0])
                     for i in range(len(temps) // 4)]
        self.write_temperatures = temp_temp_bool
        self.write_currents = temp_current_bool
        self.read_temperatures = temp_temp_temp_bool
        skipped_modules = []
        print(avg_temps)
        print(self.moduleIDList)
        for i, module_id in enumerate(self.moduleIDList):
            if 0. < avg_temps[i] <= 90.:
                self.tuning_temps[module_id] = avg_temps[i]
            else:
                skipped_modules.append(module_id)
        good_avg_temp = np.mean([i for i in avg_temps if i > 0. and i <= 90.])
        for module_id in skipped_modules:
            self.tuning_temps[module_id] = good_avg_temp
        self.setTuning(write_log=self.tmp_trim_voltage_file, italian_bias=0, flat_trims=flat_trims)



class DataTaker(PsctTool):
    """
    A subclass of PsctTool possessing the ability to perform various data taking (readout) tasks. Those include:
        forceTrigger: Trigger module readout directly from the raspberry pi

    Attributes:
        HVon: boolean - Determines if high voltage will be delivered to modules.
    """

    #can add class attributes here (ones that aren't specific to a certain run)
    #ideas: output dirs, static parameters (leslie's asic params,
    TM_DAQ_PORT = 8107

    # should be only in DataTaker
    # needs to be incremented after every run and also initialized to run_control value right at the start
    def __init__(self, moduleIDList, trigger_modules,
                 run_duration=120, subrun_duration=None, static_threshold_us=None, static_threshold_infn=None, 
                 pe_threshold_us=None, pe_threshold_infn=None,
                 HVon=0, numBlock=2, chPerPacket=32,
                 kNPacketsPerEvent=64, kBufferDepth=10000,
                 triggerDly=648, addBias=0, packetSeparation=1000,
                 packetDelay=0, read_adc_period=30, read_temperatures=False,
                 read_currents=False, pSocketBufferSize=999424, run_info=None,
                 retry=False, n_retry=1, tuning_temp=None, new_tune=False, pmtref4voltage=1.25, thresh_type="static_thresh"):
        super().__init__(moduleIDList, trigger_modules, HVon=HVon,
                         numBlock=numBlock, static_threshold_us=static_threshold_us, static_threshold_infn = static_threshold_infn, 
                         pe_threshold_us=pe_threshold_us, pe_threshold_infn=pe_threshold_infn,
                         addBias=addBias, read_temperatures=read_temperatures,
                         read_currents=read_currents, retry=retry, n_retry=n_retry, tuning_temp=tuning_temp,
                         new_tune=new_tune, pmtref4voltage=pmtref4voltage)

        self.chPerPacket = chPerPacket
        self.kNPacketsPerEvent = kNPacketsPerEvent
        self.kBufferDepth = int(kBufferDepth)
        self.triggerDly = triggerDly
        self.packetSeparation = packetSeparation
        self.packetDelay = packetDelay

        self.data_file = ""

        self.read_adc_period = read_adc_period

        self.packetsPerEvent = int((self.kNPacketsPerEvent*len(self.moduleIDList))/self.chPerPacket)
        self.kPacketSize = int(2*(10 + self.chPerPacket*(self.numBlock*32 + 1)))

        self.pSocketBufferSize = pSocketBufferSize

        self.forceFrequency = 100
        self.calFrequency = 100
        self.runDuration = run_duration
        self.subrunDuration = subrun_duration
        self.subrun_counter = 0
        self.actual_duration = 0
        self.pi_hitpattern = piCom.executeConnectionForHitpattern()

        self.run_info = run_info
        if self.run_info is None:
            self.run_info = {}

        self.tuning_temp = tuning_temp
        self.new_tune = new_tune
        # contains results of the last completed run
        self.nPacketsWritten = None
        self.nEvents = None
        self.num_packets_lost = None
        self.nPacketsWritten_subruns = None
        self.nEvents_subruns = None
        self.num_packets_lost_subruns = None

        #TODO add in writer, listener, buf into constructor
        self.listener = None
        self.buf = None
        self.writer = None
        
        #thresh_type
        self.thresh_type = thresh_type

    def prepareModules4Readout(self):
        """
        Write the channels per packet, trigger delay,
        and packet separation to all modules.
        """
        print("\nSetting chPerPacket for all modules to {}".format(self.chPerPacket))
        self.setChPerPacket()
        time.sleep(0.5)

        print("\nSetting triggerDly for all modules to {}".format(self.triggerDly))
        self.setDelay()
        time.sleep(0.5)

        print("\nSetting packetSeparation for all modules to {}".format(self.packetSeparation))
        self.setPacketSeparation()
        time.sleep(0.)

        print("\nSetting {} values on all modules: {}".format(self.thresh_type,self.moduleIDList))
        for moduleID in self.moduleIDList:
            if(self.thresh_type=="static_thresh"):
                if moduleID in range(10):
                    self.setStaticThresh(moduleID, self.staticThresh_infn)
                else:
                    self.setStaticThresh(moduleID, self.staticThresh_us)
            if(self.thresh_type=="pe_thresh"):
                if moduleID in range(10):
                    self.setPeThresh(moduleID, self.peThresh_infn)
                else:
                    self.setPeThresh(moduleID, self.peThresh_us)
            
        time.sleep(0.5)

    def setChPerPacket(self):
        for module in self.moduleList:
            module.WriteSetting("MaxChannelsInPacket", self.chPerPacket)

    def setDelay(self):
        for module in self.moduleList:
            module.WriteSetting("TriggerDelay", self.triggerDly)

    def setPacketSeparation(self):
        for module in self.moduleList:
            module.WriteRegister(0x71, self.packetSeparation)

    def setPacketDelay(self, modID, packetDelay):
        self.moduleList[self.moduleIDList.index(modID)].WriteSetting("DataSendingDelay", packetDelay)

    #def prepareReadout(self):
    #    self.listener = target_io.DataListener(self.kBufferDepth, self.packetsPerEvent, self.kPacketSize)
    #    piCom.recordHitpatternFile(self.pi_hitpattern, 10, self.runDuration-1)
    #    #piCom.recordHitpatternFile(self.pi, 100, self.runDuration-1)
    #    for module in self.moduleList:
    #        module.DataPortPing()

    #    for server_ip in self.subnet_port_ip.values():
    #        self.listener.AddDAQListener(server_ip)
    #    self.buf = self.listener.GetEventBuffer()

    def prepareReadout(self):
        piCom.recordHitpatternFile(self.pi_hitpattern, 10, self.runDuration-1)
        #piCom.recordHitpatternFile(self.pi, 100, self.runDuration-1)
        if self.subrunDuration is None:
            self.listener = target_io.DataListener(self.kBufferDepth, self.packetsPerEvent, self.kPacketSize)

            for module in self.moduleList:
                module.DataPortPing()

            for server_ip in self.subnet_port_ip.values():
                self.listener.AddDAQListener(server_ip)
            self.buf = self.listener.GetEventBuffer()

    def closeReadout(self):
        if self.subrunDuration is None:
            for module in self.moduleList:
                module.DeleteDAQListeners()

            self.buf = None

    def startRun(self, subruns=False):
        """
        Sets up run and then starts watching the buffer
        """
        self.initialize_run()
        self.data_file = os.path.join(self.outdir,
                                      "run{}.fits".format(self.run_id))
        if not subruns:
            self.writer = target_io.EventFileWriter(self.data_file,
                                                    self.packetsPerEvent,
                                                    self.kPacketSize)
            self.listener.StartListening()
            self.writer.StartWatchingBuffer(self.buf)

    def startSubrun(self):
        """
        Sets up a subrun and then starts watching the buffer 
        add logging 
        file name: avoid knowing subrun, add offset to event ID from previous subrun.
        check temperature at the beginning of subrun
        run33XXX.000.fits
        """
        data_file_subrun = self.data_file.replace(".fits","")+".{0:03}.fits".format(self.subrun_counter)
        self.subrun_counter += 1

        self.listener = target_io.DataListener(self.kBufferDepth, self.packetsPerEvent, self.kPacketSize)
        #piCom.recordHitpatternFile(self.pi_hitpattern, 10, self.runDuration-1)
        #piCom.recordHitpatternFile(self.pi, 100, self.runDuration-1)
        for module in self.moduleList:
            module.DataPortPing()

        for server_ip in self.subnet_port_ip.values():
            self.listener.AddDAQListener(server_ip)
        self.buf = self.listener.GetEventBuffer()

        self.writer = target_io.EventFileWriter(data_file_subrun,
                                                self.packetsPerEvent,
                                                self.kPacketSize)
        self.listener.StartListening()
        self.writer.StartWatchingBuffer(self.buf)

    def endSubrun(self):
        self.writer.StopWatchingBuffer()
        self.listener.StopListening()
        self.writer.Close()

        if self.nPacketsWritten is None:
            self.nPacketsWritten = 0
        if self.nPacketsWritten_subruns is None:
            self.nPacketsWritten_subruns = []
            
        npkts = self.writer.GetPacketsWritten()
        self.nPacketsWritten += npkts
        self.nPacketsWritten_subruns.append(npkts)

        #print("number of packets: {}".format(self.nPacketsWritten))
        print("number of packets: {}".format(npkts))
        
        del self.writer
        self.writer = None
        for module in self.moduleList:
            module.DeleteDAQListeners()
        del self.buf
        self.buf = None
        del self.listener
        self.listener = None
        
    def endRun(self):
        if self.subrunDuration is None:
            self.writer.StopWatchingBuffer()
            self.listener.StopListening()
            self.writer.Close()
            self.nPacketsWritten = self.writer.GetPacketsWritten()
            print("number of packets: {}".format(self.nPacketsWritten))
        
            reader = target_io.EventFileReader(self.data_file)
            self.nEvents = reader.GetNEvents()
            print("number of events: {}".format(self.nEvents))
            self.num_packets_lost = (self.nPacketsWritten -
                                     self.nEvents * self.packetsPerEvent)
            print("number of packets lost: {}".format(self.num_packets_lost))
            reader.Close()
            self.writer = None
        else: 
            self.nEvents = 0
            self.num_packets_lost = 0
            self.nEvents_subruns = []
            self.num_packets_lost_subruns = []
            for irun in range(self.subrun_counter):
                data_file_subrun = self.data_file.replace(".fits","")+".{0:03}.fits".format(irun)
                reader = target_io.EventFileReader(data_file_subrun)
                nev = reader.GetNEvents()
                self.nEvents_subruns.append(nev)
                self.nEvents += nev
                print("number of events in subrun {}: {}".format(irun,nev))
                npkt_lost = (self.nPacketsWritten_subruns[irun] -
                             nev * self.packetsPerEvent)
                self.num_packets_lost += npkt_lost
                self.num_packets_lost_subruns.append(npkt_lost)
                print("number of packets lost: {}".format(npkt_lost))
                reader.Close()

        self.log_run()



        print("#####################################")
        print("######## FINISHED RUN {} ########".format(self.run_id))
        print("#####################################")

        piCom.moveHitpatternFile(self.pi_hitpattern, self.run_id)
        #piCom.moveHitpatternFile(self.pi, self.run_id)
        os.system(f"scp pi@172.17.2.6:~/Desktop/pi_hpread/hitpattern{self.run_id}.txt /data/local_outputDir/.")

    def log_run(self):
        """
        Log critical information about the run to a text file
        so it can be formatted for putting on Confluence.
        TODO: Log to a database instead.
        """

        runlog = {**self.run_info}
        runlog['origin_timestamp'] = self.origin_timestamp
        runlog['run_timestamp'] = self.run_timestamp
        runlog['run_type'] = 'data_run'
        runlog['run_id'] = self.run_id
        runlog['modules'] = self.moduleIDList
        runlog['trigger_modules'] = self.trigger_modules
        runlog['failed_modules'] = self.failed_modules
        runlog['masked_trigger_pixels'] = self.masked_trigger_pixels
        runlog['loaded_tuning_temps'] = self.tuning_temps
        runlog['HV_on'] = self.HVon
        runlog['set_duration'] = self.runDuration
        runlog['actual_duration'] = self.actual_duration
        if(self.thresh_type=="static_thresh"):         
            runlog['threshold_us'] = self.staticThresh_us
            runlog['threshold_infn'] = self.staticThresh_infn
        if(self.thresh_type=="pe_thresh"):         
            runlog['threshold_us'] = self.peThresh_us
            runlog['threshold_infn'] = self.peThresh_infn
        
        runlog['num_blocks'] = self.numBlock
        runlog['trigger_delay'] = self.triggerDly
        runlog['num_packets_received'] = self.nPacketsWritten
        runlog['num_packets_expected'] = self.nEvents * self.packetsPerEvent
        runlog['num_events'] = self.nEvents
        runlog['num_packets_received'] = self.nPacketsWritten
        runlog['num_packets_expected'] = self.nEvents * self.packetsPerEvent
        runlog['num_events_subruns'] = self.nEvents_subruns
        runlog['num_packets_received_subruns'] = self.nPacketsWritten_subruns
        
        # Append to log of all runs
        with open(self.logfile, 'ab') as logfile:
            pickle.dump(runlog, logfile)

        # Also save a human-readable version to the run directory
        run_log_file = os.path.join(self.outdir,
                                    "{}_log.txt".format(self.run_id))
        with open(run_log_file, 'w') as logfile:
            yaml.dump(runlog, logfile, default_flow_style=False)

    def special_sleep(self, run_duration=None):
        """
        Waits for the runDuration, but has the ability to read out temperatures during
        """
        # Guarantee at least one temperature reading,
        # but don't run for longer than the runDuration
        if run_duration is None:
            run_duration = self.runDuration
        elapsed_time = 0.0
        start_time = time.time()
        while elapsed_time <= run_duration:
            self.read_all_adcs(close_trigger_mask=True)
            elapsed_time = time.time() - start_time
            print("############# Time Elapsed : {} seconds".format(elapsed_time))
            safe_elapsed_time = elapsed_time % self.read_adc_period
            safe_remaining_time = max(run_duration - elapsed_time, 0)
            sleep_time = min(self.read_adc_period - safe_elapsed_time,
                             safe_remaining_time)
            time.sleep(sleep_time)

    def special_sleep_subruns(self, run_duration=None, subrun_duration=None):
        """ Special sleep for subrun
        """
        if run_duration is None:
            run_duration = self.runDuration
        if subrun_duration is None:
            subrun_duration = self.subrunDuration
        elapsed_time = 0.0
        starttime = time.time()
        while elapsed_time <= run_duration:
            t0=time.time()
            self.startSubrun()
            print(f"##### startsubrun dead time: {time.time()-t0} s")
            elapsed_time = time.time() - starttime
            print("############# Time Elapsed in subrun loop : {} seconds".format(elapsed_time))
            safe_elapsed_time = elapsed_time % subrun_duration
            safe_remaining_time = max(run_duration - elapsed_time, 0)
            sleep_time = min(subrun_duration - safe_elapsed_time,
                             safe_remaining_time)
            self.read_all_adcs(close_trigger_mask=True)
            self.open_trigger_mask()
            time.sleep(sleep_time)
            #self.special_sleep(run_duration=sleep_time)
            self.close_trigger_mask()
            self.endSubrun()
            elapsed_time = time.time() - starttime

        endtime = time.time()


    def takeForceTrigData(self):
        """
        Takes data with the force trigger setup (trigger sent from bp to modules)
        """
        self.startRun()

        self.open_trigger_mask()
        starttime = time.time()

        print("Sending global FORCE trigger")
        piCom.sendModTrig(self.pi, self.runDuration, self.forceFrequency)
        time.sleep(1)
        time.sleep(self.runDuration)
        self.close_trigger_mask()
        endtime = time.time()
        self.actual_duration = endtime - starttime
        print("Stop taking data after {} seconds".format(self.actual_duration))

        self.endRun()

    def takeCalTrigData(self):
        """
        Takes data with the cal trigger setup (trigger sent from raspberry pi to an external device, such as an LED flasher)
        """
        self.startRun()

        print("**************** Starting run {} *****************".format(self.run_id))

        self.open_trigger_mask()
        starttime = time.time()

        print("Sending global CAL trigger")
        piCom.sendCalTrig(self.pi, self.runDuration, self.calFrequency)
        time.sleep(1)
        self.special_sleep()
        #time.sleep(self.runDuration)
        self.close_trigger_mask()
        endtime = time.time()
        print("Stop taking data after {} seconds".format(endtime-starttime))

        self.endRun()

    def takeInternalTrigData(self):
        """
        Takes data with the internal trigger setup (triggered by module ASICs)
        """
        if self.subrunDuration is not None:
            subruns = True
        else:
            subruns = False
        self.startRun(subruns=subruns)



        numTACKsReceived1 = self._read_tacks()
        if not subruns:
            self.open_trigger_mask()
            starttime = time.time()
            self.special_sleep()

            self.close_trigger_mask()
            endtime = time.time()
        else:
            starttime = time.time()
            self.special_sleep_subruns(run_duration=None, subrun_duration=None)
            #elapsed_time = 0.0
            #while elapsed_time <= self.runDuration:
            #    self.startSubrun()
            #    elapsed_time = time.time() - starttime
            #    print("############# Time Elapsed in subrun loop : {} seconds".format(elapsed_time))
            #    safe_elapsed_time = elapsed_time % self.subrunDuration
            #    safe_remaining_time = max(self.runDuration - elapsed_time, 0)
            #    sleep_time = min(self.subrunDuration - safe_elapsed_time,
            #                     safe_remaining_time)
            #    self.open_trigger_mask()
            #    self.special_sleep(run_duration=sleep_time)
            #    self.close_trigger_mask()
            #    self.endSubrun()
            endtime = time.time()


        numTACKsReceived2 = self._read_tacks()

        print("Stop taking data after {} seconds".format(endtime - starttime))

        print("\n\n************** {} TACK messages received *************\n\n".format(numTACKsReceived2 - numTACKsReceived1))

        self.endRun()

class RateScanner(PsctTool):

    def __init__(self, moduleIDList, trigger_modules, pe_thresholds=None,
                 HVon=0, addBias=0, read_temperatures=False,
                 n_hitmaps=50,retry=False,n_retry=1,
                 read_currents=False, run_info=None, new_tune=False, tuning_temp = None,
                 pmtref4voltage=1.25, scan_type="thresh"):
        super().__init__(moduleIDList, trigger_modules, HVon=HVon, retry=retry, n_retry=n_retry,
                         addBias=addBias, read_temperatures=read_temperatures,
                         read_currents=read_currents, new_tune=new_tune, 
                         tuning_temp=tuning_temp, pmtref4voltage=pmtref4voltage)

        self.run_info = run_info
        if self.run_info is None:
            self.run_info = {}

        self.scan_file = None
        self.hitmaps_file = None
        self.new_tune = new_tune
        self.tuning_temp = tuning_temp

        self.pe_thresholds = pe_thresholds
        if self.pe_thresholds is None:
            if self.scan_type=="thresh":
                self.pe_thresholds = range(850, -25, -25)
            if self.scan_type=="pe":
                self.pe_thresholds = range(30, 9.5, -0.5)
        self.n_hitmaps = n_hitmaps
        self.scan_type = scan_type

    def peScan(self):

        self.initialize_run()
        self.scan_file = os.path.join(self.outdir,
                                      "{}_scan.txt".format(self.run_id))
        self.hitmaps_file = os.path.join(self.outdir,
                                         "{}_hitmaps.txt".format(self.run_id))

        with open(self.scan_file, 'w') as scanfile, \
                open(self.hitmaps_file, 'w') as hitfile:
            for thresh_level in self.pe_thresholds:
                print("Reading module temperatures:")
                self.read_all_adcs(close_trigger_mask=False)

                thresh_list = [thresh_level] * 16
                #thresh_list[asic * 4 + trpixel] = thresh_level
                for moduleID in self.moduleIDList:
                    if self.scan_type=="thresh":
                        self.setStaticThresh(moduleID, thresh_list)
                    if self.scan_type=="pe":
                        self.setPeThresh(moduleID,thresh_list,vped_dac=self.VpedList[self.moduleIDList.index(moduleID)])

                numTACKsReceived1 = self._read_tacks()
                self.open_trigger_mask()
                start_time = time.time()

                for __ in range(self.n_hitmaps):
                    pattern = piCom.requestHitPattern(self.pi)
                    hitfile.write("{}   ".format(thresh_level))
                    for modHits in pattern:
                        hitfile.write("{}   ".format(modHits))
                    hitfile.write("\n")
                    piCom.resetHitPattern(self.pi)
                time.sleep(5)
                stop_time = time.time()
                self.close_trigger_mask()
                numTACKsReceived2 = self._read_tacks()

                time_frame = stop_time - start_time
                if numTACKsReceived2 < numTACKsReceived1:
                    numTACKsReceived2 += 65535
                #TACKrate = (numTACKsReceived2 - numTACKsReceived1) / time_frame
                #QF: subtract the TACK message count for hit maps reading
                # if no modules connected, no tack message will be received;  let's avoid printing -9.6 Hz...
                if numTACKsReceived2 == numTACKsReceived1:
                    TACKrate = 0.0
                else:
                    TACKrate = (numTACKsReceived2 - numTACKsReceived1 - self.n_hitmaps) / time_frame

                print("Thresh: {} DAC, {} seconds, {} TACKs received, TACK rate: {}".format(
                    thresh_level, time_frame, numTACKsReceived2-numTACKsReceived1-self.n_hitmaps, TACKrate))
                #print("Thresh: {} DAC, {} seconds, TACK rate: {}".format(
                #    thresh_level, time_frame, TACKrate))
                scanfile.write("{}  {}\n".format(thresh_level, TACKrate))
                time.sleep(0.5)

        self.log_rate_scan()

        print("###########################################")
        print("######## FINISHED RATE SCAN {} ########".format(self.run_id))
        print("###########################################")

    def thresh_pe_scan(self, asic, trpixel, Vped):
        try:
            assert asic < 4
            assert trpixel < 4
        except AssertionError:
            print("Both ASIC number and Trigger Pixel number need to be less than 4!")
            return False
        self.initialize_run()
        self.scan_file = os.path.join(self.outdir,
                                      f"{self.run_id}_scan.txt")
        with open(self.scan_file, "w") as scanfile:
            scanfile.write(f"Vped  {Vped}")
            for thresh_level in self.pe_thresholds:
                print("Reading module temperatures:")
                self.read_all_adcs(close_trigger_mask=False)
                print(f"Setting ASIC {asic}, Trigger Pixel {trpixel} to {thresh_level}")
                thresh_list = [0] * 16
                thresh_list[asic * 4 + trpixel] = thresh_level
                for moduleID in self.moduleIDList:
                    self.setPeThresh(moduleID, thresh_level)
                '''
                if thresh_level > 800:
                    sleep_time = 5
                elif 400 < thresh_level <= 800:
                    sleep_time = 10
                else:
                    sleep_time = 20
                '''
                sleep_time = 1 #FIXME
                trig_count_start = piCom.requestTrigCount(self.pi)
                print(trig_count_start)
                self.open_trigger_mask()
                time_start = time.time()
                time.sleep(sleep_time)
                time_stop = time.time()
                self.close_trigger_mask()
                trig_count_stop = piCom.requestTrigCount(self.pi)
                trig_count_delta = trig_count_stop - trig_count_start
                time_delta = time_stop - time_start
                rate = trig_count_delta / time_delta
                print(f"Thresh: {thresh_level} DAC, {time_delta} seconds, {trig_count_delta} Trig Counts received, Rate: {rate}")
                scanfile.write(f"{thresh_level}  {rate}\n")
        self.log_rate_scan()
        print("###########################################")
        print("######## FINISHED RATE SCAN {} ########".format(self.run_id))
        print("###########################################")

    def thresh_pe_scan_reg(self, asic, trpixel, Vped):
        try:
            assert asic < 4
            assert trpixel < 4
        except AssertionError:
            print("Both ASIC number and Trigger Pixel number need to be less than 4!")
            return False
        trigger_module_id = self.trigger_modules[0]
        trigger_module_index = self.moduleIDList.index(trigger_module_id)
        trigger_module = self.moduleList[trigger_module_index]
        
        self.initialize_run()
        self.scan_file = os.path.join(self.outdir,
                                      f"{self.run_id}_scan.txt")
        piCom.resetHitPattern(self.pi)
        piCom.disableTACK(self.pi)
        thresh_list = [0] * 16
        for moduleID in self.moduleIDList:
            self.setStaticThresh(moduleID, thresh_list)
        print("Reading module temperatures:")
        self.read_all_adcs(close_trigger_mask=False)
        print(f"ASIC {asic}, trpixel {trpixel}, Vped {Vped}")
        self.open_trigger_mask()
 
        with open(self.scan_file, "w") as scanfile:
            scanfile.write(f"Vped  {Vped}\nModule {self.moduleIDList[0]}\nASIC {asic}\nTrigger Pixel {trpixel}\n")
            for thresh_level in self.pe_thresholds:
                #print(f"Setting ASIC {asic}, Trigger Pixel {trpixel} to {thresh_level}")
                #thresh_list = [0] * 16
                #thresh_list[asic * 4 + trpixel] = thresh_level
                trigger_module.WriteASICSetting("Thresh_{}".format(trpixel), asic, int(thresh_level), True)
                #offset the thresh in the noise on adjacent pixels when Vped above 1106
                offset_thresh = 23*(Vped - 1106)
                #offset_thresh = 0
                if trpixel < 2:
                    trigger_module.WriteASICSetting("Thresh_{}".format(2), asic, int(2500-offset_thresh), True)
                    trigger_module.WriteASICSetting("Thresh_{}".format(3), asic, int(2500-offset_thresh), True)
                else:
                    trigger_module.WriteASICSetting("Thresh_{}".format(0), asic, int(2500-offset_thresh), True)
                    trigger_module.WriteASICSetting("Thresh_{}".format(1), asic, int(2500-offset_thresh), True)
                
                '''
                if thresh_level > 800:
                    sleep_time = 5
                elif 400 < thresh_level <= 800:
                    sleep_time = 10
                else:
                    sleep_time = 20
                '''
                sleep_time = 0.2 #FIXME
                trigCount1 = piCom.requestTrigCount(self.pi)
                       
                #trig_count_start = np.uint16(trigger_module.ReadRegister(0xf)[1] & 0xffff)
                #print(trig_count_start)
                #self.open_trigger_mask()
                time_start = time.time()
                time.sleep(sleep_time)
                #self.close_trigger_mask()
                #trig_count_stop = np.uint16(trigger_module.ReadRegister(0xf)[1] & 0xffff)
                trigCount2 = piCom.requestTrigCount(self.pi)
                time_stop = time.time()
                #print(trig_count_stop)
                #print(trigCount1, trigCount2)
                #trig_count_delta = trig_count_stop - trig_count_start
                trig_count_delta = trigCount2 - trigCount1
                time_delta = time_stop - time_start
                rate = trig_count_delta / time_delta
                if trigCount1>trigCount2:
                    rate2 = (trigCount2 - trigCount1 + 2**32)/time_delta
                else:
                    rate2 = (trigCount2 - trigCount1)/time_delta
                print(f"Thresh: {thresh_level} DAC, {np.round(time_delta,2)} seconds, {trig_count_delta} Trig Counts received, Rate: {rate2}")
                scanfile.write(f"{thresh_level} {rate2}\n")
        self.close_trigger_mask()
        self.log_rate_scan()
        print("###########################################")
        print("######## FINISHED RATE SCAN {} ########".format(self.run_id))
        print("###########################################")


    def log_rate_scan(self):
        """
        Log critical information about the run to a text file
        so it can be formatted for putting on Confluence.
        TODO: Log to a database instead.
        """

        rate_scan_log = {**self.run_info}
        rate_scan_log['origin_timestamp'] = self.origin_timestamp
        rate_scan_log['run_timestamp'] = self.run_timestamp
        rate_scan_log['run_type'] = 'rate_scan'
        rate_scan_log['run_id'] = self.run_id
        rate_scan_log['modules'] = self.moduleIDList
        rate_scan_log['trigger_modules'] = self.trigger_modules
        rate_scan_log['masked_trigger_pixels'] = self.masked_trigger_pixels
        rate_scan_log['loaded_tuning_temps'] = self.tuning_temps
        rate_scan_log['failed_modules'] = self.failed_modules
        rate_scan_log['HV_on'] = self.HVon
        rate_scan_log['pe_thresholds'] = list(self.pe_thresholds)

        # Append to log of all runs
        with open(self.logfile, 'ab') as logfile:
            pickle.dump(rate_scan_log, logfile)

        # Also save a human-readable version to the run directory
        run_log_file = os.path.join(self.outdir,
                                    "{}_log.txt".format(self.run_id))
        with open(run_log_file, 'w') as logfile:
            yaml.dump(rate_scan_log, logfile, default_flow_style=False)

class TriggerTester(PsctTool):

    TIME_FRAME = 1.0 #seconds

    # should be only in TriggerTester
    def __init__(self, moduleIDList, trigModID, HVon=0, coincidenceLogic=3,
                 addBias=0):
        super().__init__(moduleIDList, [trigModID], HVon=HVon, addBias=addBias)
        self.trigger_module_id = trigModID
        trigger_module_index = self.moduleIDList.index(trigModID)
        self.trigger_module = self.moduleList[trigger_module_index]
        # proper default should be 3 right?
        self.coincidenceLogic = coincidenceLogic

        self.VpedStart = None
        self.VpedStop = None
        self.VpedStep = None

        self.threshStart = 0
        self.threshStop = 1600
        self.threshStep = 50

        self.asicList = [0, 1, 2, 3]
        self.groupList = [0, 1, 2, 3]

        self.threshScanOutBase = None
        self.threshScanOutDir = None

        self.threeFold_mod0ID = None
        self.threeFold_mod0asic = None
        self.threeFold_mod0group = None
        self.threeFold_mod1ID = None
        self.threeFold_mod1asic = None
        self.threeFold_mod1group = None
        self.threeFold_mod2IDList = None



        self.filename = ""

    def scanBookkeeping(self):

        self.run_timestamp = datetime.datetime.utcnow()
        dataset = self.run_timestamp.strftime('%Y%m%d_%H%M')
        self.threshScanOutBase = "{}/cameraIntegration/triggerScan/FEE{}".format(PsctTool.outdir, self.trigger_module_id)
        self.threshScanOutDir = "{}/dat_{}".format(self.threshScanOutBase, dataset)
        self.filename = "FEE{}/dat_{}".format(self.trigger_module_id, dataset)

        print("Writing to directory: {}".format(self.threshScanOutDir))

        if not os.path.isdir(self.threshScanOutBase):
            os.mkdir(self.threshScanOutBase)
        if not os.path.isdir(self.threshScanOutDir):
            os.mkdir(self.threshScanOutDir)

    def singleModScan(self):
        if self.coincidenceLogic != 1:
            print("Check that your coincidenceLogic is correct!")
        else:
            self.scanBookkeeping()

            self.open_trigger_mask()
            for asic in self.asicList:
                for group in self.groupList:
                    threshScanOutName = "{}/a{}g{}.txt".format(self.threshScanOutDir, asic, group)

                    for thresh in range(self.threshStart, self.threshStop, self.threshStep):
                        self.close_trigger_mask()
                        temp = self.read_adc(self.trigger_module)
                        self.open_trigger_mask()
                        self.trigger_module.WriteASICSetting("Thresh_{}".format(group), asic, int(thresh), True)
                        time.sleep(0.2)
                        numTACKsReceived1 = np.uint16(self.trigger_module.ReadRegister(0xf)[1] & 0xffff)
                        time.sleep(TriggerTester.TIME_FRAME)
                        numTACKsReceived2 = np.uint16(self.trigger_module.ReadRegister(0xf)[1] & 0xffff)
                        if numTACKsReceived2 >= numTACKsReceived1:
                            TACKrate = (numTACKsReceived2 - numTACKsReceived1) / TriggerTester.TIME_FRAME
                        else:
                            TACKrate = (numTACKsReceived2 + 65535 - numTACKsReceived1)/ TriggerTester.TIME_FRAME

                        if thresh == 0:
                            TACKrate = 0
                        trigCount1 = piCom.requestTrigCount(self.pi)
                        time.sleep(TriggerTester.TIME_FRAME)
                        trigCount2 = piCom.requestTrigCount(self.pi)
                        trigRate = (trigCount2 - trigCount1)/(1.0*TriggerTester.TIME_FRAME)
                        print("ASIC: {}, Group: {}, Thresh: {} DAC, TACK rate: {}, Trigger rate: {}, Temp: {} C".format(asic, group, thresh, TACKrate, trigRate, temp[0]))

                        with open(threshScanOutName, 'a') as threshScanOutFile:
                            threshScanOutFile.write("{} {} {}\n".format(thresh, trigRate, temp))

                    time.sleep(0.5)
                    self.setAllThreshHigh(self.trigger_module_id)
                    time.sleep(0.5)

    def singleModScan3fold(self):
        if self.coincidenceLogic != 3:
            print("Check that your coincidenceLogic is correct!")
        else:
            self.scanBookkeeping()

            self.open_trigger_mask()
            for asic in self.asicList:
                for group in self.groupList:
                    threshScanOutName = "{}/a{}g{}.txt".format(self.threshScanOutDir, asic, group)
                    if group < 2:
                        self.trigger_module.WriteASICSetting("Thresh_{}".format(2), asic, int(1800), True)
                        self.trigger_module.WriteASICSetting("Thresh_{}".format(3), asic, int(1800), True)
                    else:
                        self.trigger_module.WriteASICSetting("Thresh_{}".format(0), asic, int(1800), True)
                        self.trigger_module.WriteASICSetting("Thresh_{}".format(1), asic, int(1800), True)

                    for thresh in range(self.threshStart, self.threshStop, self.threshStep):
                        self.close_trigger_mask()
                        temp = self.read_adc(self.trigger_module)
                        self.open_trigger_mask()
                        self.trigger_module.WriteASICSetting("Thresh_{}".format(group), asic, int(thresh), True)
                        time.sleep(0.2)
                        numTACKsReceived1 = np.uint16(self.trigger_module.ReadRegister(0xf)[1] & 0xffff)
                        time.sleep(TriggerTester.TIME_FRAME)
                        numTACKsReceived2 = np.uint16(self.trigger_module.ReadRegister(0xf)[1] & 0xffff)
                        if numTACKsReceived2 >= numTACKsReceived1:
                            TACKrate = (numTACKsReceived2 - numTACKsReceived1) / TriggerTester.TIME_FRAME
                        else:
                            TACKrate = (numTACKsReceived2 + 65535 - numTACKsReceived1)/ TriggerTester.TIME_FRAME

                        if thresh == 0:
                            TACKrate = 0
                        trigCount1 = piCom.requestTrigCount(self.pi)
                        time.sleep(TriggerTester.TIME_FRAME)
                        trigCount2 = piCom.requestTrigCount(self.pi)
                        trigRate = (trigCount2 - trigCount1)/(1.0*TriggerTester.TIME_FRAME)
                        print("ASIC: {}, Group: {}, Thresh: {} DAC, TACK rate: {}, Trigger rate: {}, Temp: {} C".format(asic, group, thresh, TACKrate, trigRate, temp))

                        with open(threshScanOutName, 'a') as threshScanOutFile:
                            threshScanOutFile.write("{} {} {}\n".format(thresh, trigRate, temp))

                    if group < 2:
                        self.trigger_module.WriteASICSetting("Thresh_{}".format(2), asic, int(0), True)
                        self.trigger_module.WriteASICSetting("Thresh_{}".format(3), asic, int(0), True)
                    else:
                        self.trigger_module.WriteASICSetting("Thresh_{}".format(0), asic, int(0), True)
                        self.trigger_module.WriteASICSetting("Thresh_{}".format(1), asic, int(0), True)

                    time.sleep(0.5)
                    self.setAllThreshHigh(self.trigger_module_id)
                    time.sleep(0.5)

    def changeVpedScan(self):
        for nextVped in range(self.VpedStart, self.VpedStop, self.VpedStep):
            print("\nSwitching Vped to {} DAC\n".format(nextVped))
            self.trigger_module.WriteSetting('Vped_value', nextVped)
            self.singleModScan()

    def threeFoldScan(self):
        """
        Function that tests the 3 fold coincidence logic.
        Does so by choosing 2 groups (w/in a module or b/w modules), and then iterates through surrounding groups
        Need to specify 'threeFold' parameters before running.
        """
        if self.coincidenceLogic != 3:
            print("Check that your coincidenceLogic is correct!")
        elif None in [self.threeFold_mod0ID, self.threeFold_mod0asic,
                      self.threeFold_mod0group, self.threeFold_mod1ID,
                      self.threeFold_mod1asic, self.threeFold_mod1group,
                      self.threeFold_mod2IDList]:
            print("Make sure that you have defined all three-fold variables")
        else:
            self.scanBookkeeping()

            self.open_trigger_mask()

            mod0Ind = self.moduleIDList.index(self.threeFold_mod0ID)
            mod1Ind = self.moduleIDList.index(self.threeFold_mod1ID)

            for mod2ID in self.threeFold_mod2IDList:
                mod2Ind = self.moduleIDList.index(mod2ID)
                for asic2 in range(PsctTool.num_asic):
                    for gr2 in range(PsctTool.num_groups_per_asic):
                        threeFold_outname = '{}/m{}a{}g{}_m{}a{}g{}_m{}a{}g{}.txt'.format(self.threshScanOutDir,
                                self.threeFold_mod0ID, self.threeFold_mod0asic, self.threeFold_mod0group,
                                self.threeFold_mod1ID, self.threeFold_mod1asic, self.threeFold_mod1group,
                                mod2ID, asic2, gr2)

                        for thresh in range(self.threshStart, self.threshStop,
                                            self.threshStep):
                            self.moduleList[mod0Ind].WriteASICSetting("Thresh_{}".format(self.threeFold_mod0group), self.threeFold_mod0asic, int(thresh), True)
                            time.sleep(0.5)
                            self.moduleList[mod1Ind].WriteASICSetting("Thresh_{}".format(self.threeFold_mod1group), self.threeFold_mod1asic, int(thresh), True)
                            time.sleep(0.5)
                            self.moduleList[mod2Ind].WriteASICSetting("Thresh_{}".format(gr2), asic2, int(thresh), True)
                            time.sleep(0.5)

                            numTACKsReceived1 = np.uint16(self.trigger_module.ReadRegister(0xf)[1] & 0xffff)
                            time.sleep(TriggerTester.TIME_FRAME)
                            numTACKsReceived2 = np.uint16(self.trigger_module.ReadRegister(0xf)[1] & 0xffff)
                            TACKrate = (numTACKsReceived2 - numTACKsReceived1) / TriggerTester.TIME_FRAME

                            if not thresh:
                                TACKrate = 0

                            with open(threeFold_outname, 'a') as threeFoldOutFile:
                                threeFoldOutFile.write("{} {}\n".format(thresh, TACKrate))

                            self.setAllThreshHigh(self.threeFold_mod0ID)
                            time.sleep(0.5)
                            self.setAllThreshHigh(self.threeFold_mod1ID)
                            time.sleep(0.5)
                            self.setAllThreshHigh(mod2ID)
                            time.sleep(0.5)


class TuneNodeABC(PsctTool):
    """
    This class is set up to accommodate functionality to tune the TARGET7 trigger chain at different temperatures and produce files with setting and achieved bias voltages.
    """

    #can add class attributes here (ones that aren't specific to a certain run)
    #ideas: output dirs, static parameters (leslie's asic params,
    TM_DAQ_PORT = 8107
    T7_RandomBit0 = 0x37

    # should be only in DataTaker
    # needs to be incremented after every run and also initialized to run_control value right at the start
    def __init__(self, moduleIDList, trigger_modules,run_duration=120,
                 static_threshold=None,
                 HVon=0, numBlock=2, chPerPacket=32,
                 kNPacketsPerEvent=64, kBufferDepth=10000,
                 triggerDly=648, addBias=0, packetSeparation=1000,
                 packetDelay=0, read_adc_period=30, read_temperatures=True,
                 read_currents=False, pSocketBufferSize=999424, run_info=None, tuning_temp=None, new_tune=False):
        super().__init__(moduleIDList, trigger_modules, HVon=HVon,
                         numBlock=numBlock, static_threshold=static_threshold,
                         addBias=addBias, read_temperatures=read_temperatures,
                         read_currents=read_currents, tuning_temp=tuning_temp, new_tune=new_tune)

        self.chPerPacket = chPerPacket
        self.kNPacketsPerEvent = kNPacketsPerEvent
        self.kBufferDepth = int(kBufferDepth)
        self.triggerDly = triggerDly
        self.packetSeparation = packetSeparation
        self.packetDelay = packetDelay

        self.maxStepCount = 20

        self.new_tune = new_tune
        self.tuning_temp = tuning_temp


        self.refVoltageA = 1.25
        self.refVoltageB = 1.25
        self.refVoltageC = 1.25


        self.data_file = ""

        self.read_adc_period = read_adc_period

        self.packetsPerEvent = int((self.kNPacketsPerEvent*len(self.moduleIDList))/self.chPerPacket)
        self.kPacketSize = int(2*(10 + self.chPerPacket*(self.numBlock*32 + 1)))

        self.pSocketBufferSize = pSocketBufferSize

        #self.forceFrequency = 100
        #self.calFrequency = 100
        #self.runDuration = run_duration
        self.actual_duration = 0

        self.run_info = run_info
        if self.run_info is None:
            self.run_info = {}

        # contains results of the last completed run
        #self.nPacketsWritten = None
        #self.nEvents = None
        #self.num_packets_lost = None

        #TODO add in writer, listener, buf into constructor
        #self.listener = None
        #self.buf = None
        #self.writer = None











    def assignNodeA(self, module, asic, ch):# set ch2 0 ~ 15
        """
        This sets everything up to measure trigger node A.
        """
        reg1 = ch*2 << 4
        module.WriteTARGETRegister((asic==0),(asic==1),(asic==2),(asic==3),False, True,self.T7_RandomBit0, reg1)
        return 0

    def readNode(self, module, asic):# set ch2 0 ~ 15
        """
        This function reads the voltage from trigger node A.
        """
        #ch_1=asic*4
        #ch_a=ch_1+(2*(ch_1<8)-1)*((ch_1>3)*(ch_1<12)+1)*4
        if(asic==0):
            ch_a = 4
        elif(asic==1):
            ch_a = 12
        elif(asic==2):
            ch_a = 0
        elif(asic==3):
            ch_a = 8

        module.WriteSetting("AddressFPGAMonitoring", 0x10 + ch_a)
        data = module.ReadRegister(0x28)
        #print data, data[1]&0xffff, (data[1] &0xffff)>>4
        volts = ( (data[1] & 0xffff) >> 4)*3./4096.
        volts
        return volts


    def assignNodeB(self, module, asic,ch): # set ch2 0 ~ 15

        #reg2 = ch2 * 32 + 16
        reg2 = (2*ch+1) << 4
        module.WriteTARGETRegister((asic==0),(asic==1),(asic==2),(asic==3),False, True,self.T7_RandomBit0, reg2)
        return 0


    def assignNodeC(self,module,asic,group):

        regr = group * 16 + 512
        module.WriteTARGETRegister((asic==0),(asic==1),(asic==2),(asic==3),False, True,self.T7_RandomBit0, regr)
        return 0

    def tuneNodeA(self,asic,ch):  #,NodeA0,NodeA,Vofs1_start,max_interval=200,tolerance=0.01):
        #print("Start tuning node A. For ASIC{} and channel {}".format(asic, ch))
        start_setting = 1500

        voltage = np.zeros(len(self.moduleList))
        temperature = np.zeros(len(self.moduleList))
        setting = np.ones(len(self.moduleList))*start_setting
        changeSetting = np.ones(len(self.moduleList))*100
        changeVoltage = np.zeros(len(self.moduleList))

        for i, module in enumerate(self.moduleList):
            self.assignNodeA(module, asic, ch)# set ch2 0 ~ 15
            module.WriteASICSetting("Vofs1_{}".format(ch), asic, int(setting[i]), True)
        time.sleep(0.5)
        for i, module in enumerate(self.moduleList):
            voltage[i] = self.readNode(module, asic)

        stepCount=0
        while( (abs(self.refVoltageA-voltage)>0.003).any() and stepCount<self.maxStepCount):
                if(stepCount==0):
                    changeSetting = 100 * ( (self.refVoltageA - voltage)/abs(self.refVoltageA - voltage) ).astype(int)
                    #print("FIRST STEP", changeSetting)
                else:
                    #print( self.refVoltageA, voltage, changeVoltage, ( (self.refVoltageA-voltage)*1.0/changeVoltage ) )
                    #changeSetting = (  ( (self.refVoltageA-voltage)*1.0/changeVoltage )*abs(changeSetting) ).astype(int)
                    changeSetting = (  (self.refVoltageA-voltage)*changeVoltage ** ((abs(changeVoltage) > 0) * -1.0)*abs(changeSetting) ).astype(int)

                if( (abs(changeSetting)>500).any() ):
                #        changeSetting=500
                    print("ALERT:, changeSetting:", changeSetting, "Voltage:", voltage, "ChangeV:",changeVoltage)

                    changeSetting = changeSetting*( changeSetting<500 ) + 500*( changeSetting>=500 )

                if( (changeSetting==0).all() ):
                        changeSetting= changeSetting + 1*(abs(self.refVoltageA-voltage)>0.003)

                setting = setting+changeSetting
                if( (setting> 4095).any() or (setting<0).any()   ):
                    print("ALERT, Setting is:", setting, "The Changesetting was:", changeSetting)
                    setting = setting * (1*( setting>0 )*(setting<4095) ) + 1500*(setting >= 4095) + 1500*(setting <= 0)


                temp = np.array(voltage)
                #print(setting)
                start_timeA = time.time()
                for i, module in enumerate(self.moduleList):
                    module.WriteASICSetting("Vofs1_{}".format(ch), asic, int(setting[i]), True)
                stop_timeA = time.time()

                time.sleep(0.5)
                for i, module in enumerate(self.moduleList):
                    voltage[i] = self.readNode(module, asic)
                changeVoltage=abs( voltage - temp)
                #print("Result: Change setting:", changeSetting, " new voltage:", voltage, "old voltage:", temp, "Changevoltage", changeVoltage, "Elapsed time for reading: ", stop_timeA - start_timeA)
                stepCount+=1

        for i, module in enumerate(self.moduleList):

            #print( self.read_adc(module)[0])
            temperature[i] = self.read_adc(module)[0][0]

        print("Final tuning result node A. For ASIC{} and channel {}".format(asic, ch), " voltage:", voltage, "DAC setting:", setting, "Temperature:", temperature )
        if( (abs(self.refVoltageA-voltage)>0.003).any() ):
            print("********************************************ALERT: ALGORITHM DID NOT CONVERGE!!!!********************************************")

        return setting, voltage, temperature



    def tuneNodeB(self,asic,ch):  #,NodeA0,NodeA,Vofs1_start,max_interval=200,tolerance=0.01):
        #print("Start tuning node B. For ASIC{} and channel {}".format(asic, ch))
        start_setting = 1500
        temperature = np.zeros(len(self.moduleList))

        voltage = np.zeros(len(self.moduleList))
        setting = np.ones(len(self.moduleList))*start_setting
        changeSetting = np.ones(len(self.moduleList))*100
        changeVoltage = np.zeros(len(self.moduleList))

        for i, module in enumerate(self.moduleList):
            self.assignNodeB(module, asic, ch)# set ch2 0 ~ 15
            module.WriteASICSetting("Vofs2_{}".format(ch), asic, int(setting[i]), True)
        time.sleep(0.5)
        for i, module in enumerate(self.moduleList):
            voltage[i] = self.readNode(module, asic)

        stepCount=0
        while(( abs(self.refVoltageB-voltage)>0.003).any() and stepCount<self.maxStepCount):
                if(stepCount==0):
                    changeSetting = 100 * ( (self.refVoltageB - voltage)/abs(self.refVoltageB - voltage) ).astype(int)
                else:
                    #print( self.refVoltageB, voltage, changeVoltage, ( (self.refVoltageB-voltage)*1.0/changeVoltage ) )
                    #changeSetting = (  ( (self.refVoltageB-voltage)*1.0/changeVoltage )*abs(changeSetting) ).astype(int)
                    changeSetting = (  (self.refVoltageB-voltage)*changeVoltage ** ((abs(changeVoltage) > 0) * -1.0)*abs(changeSetting) ).astype(int)

                if( (abs(changeSetting)>500).any() ):
                #        changeSetting=500
                    print("ALERT:, changeSetting:", changeSetting, "Voltage:", voltage, "ChangeV:",changeVoltage)

                    changeSetting = changeSetting*( changeSetting<500 ) + 500*( changeSetting>=500 )
                #if(changeSetting==0):
                #        changeSetting=1
                if( (changeSetting==0).all() ):
                        changeSetting= changeSetting + 1*(abs(self.refVoltageA-voltage)>0.003)

                setting = setting+changeSetting
                if( (setting> 4095).any() or (setting<0).any()   ):
                    print("ALERT, Setting is:", setting, "The Changesetting was:", changeSetting)
                    setting = setting * (1*( setting>0 )*(setting<4095) ) + 1500*(setting >= 4095) + 1500*(setting <= 0)


                temp = np.array(voltage)
                #print(setting)
                for i, module in enumerate(self.moduleList):
                    module.WriteASICSetting("Vofs2_{}".format(ch), asic, int(setting[i]), True)
                time.sleep(0.5)
                for i, module in enumerate(self.moduleList):
                    voltage[i] = self.readNode(module, asic)

                changeVoltage=abs( voltage - temp)
                #print("Result: Change setting:", changeSetting, " new voltage:", voltage, "old voltage:", temp, "Changevoltage", changeVoltage)
                stepCount+=1

        print("Final tuning result node B. For ASIC{} and channel {}".format(asic, ch), " voltage:", voltage, "DAC setting:", setting )
        if( (abs(self.refVoltageB-voltage)>0.003).any() ):
            print("********************************************ALERT: ALGORITHM DID NOT CONVERGE!!!!********************************************")
        for i, module in enumerate(self.moduleList):
            temperature[i] = self.read_adc(module)[0][0]

        return setting, voltage, temperature

    def tuneNodeC(self,asic,group):  #,NodeA0,NodeA,Vofs1_start,max_interval=200,tolerance=0.01):



        #print("Start tuning node C. For ASIC{} and group {}".format(asic, group))
        start_setting = 1500
        temperature = np.zeros(len(self.moduleList))

        voltage = np.zeros(len(self.moduleList))
        setting = np.ones(len(self.moduleList))*start_setting
        changeSetting = np.ones(len(self.moduleList))*100
        changeVoltage = np.zeros(len(self.moduleList))

        for i, module in enumerate(self.moduleList):
            self.assignNodeC(module, asic, group)# set ch2 0 ~ 15
            module.WriteASICSetting("PMTref4_{}".format(group), asic, int(setting[i]), True)
        time.sleep(0.5)

        for i, module in enumerate(self.moduleList):
            voltage[i] = self.readNode(module, asic)

        stepCount=0
        while( ( abs(self.refVoltageC-voltage)>0.003).any() and stepCount<self.maxStepCount):
                if(stepCount==0):
                    changeSetting = 100 * ( (self.refVoltageC - voltage)/abs(self.refVoltageC - voltage) ).astype(int)
                else:
                    #print( self.refVoltageC, voltage, changeVoltage, ( (self.refVoltageC-voltage)*1.0/changeVoltage ) )
                    changeSetting = (  (self.refVoltageC-voltage)*changeVoltage ** ((abs(changeVoltage) > 0) * -1.0)*abs(changeSetting) ).astype(int)

                if( (abs(changeSetting)>500).any() ):
                #        changeSetting=500
                    print("ALERT:, changeSetting:", changeSetting, "Voltage:", voltage, "ChangeV:",changeVoltage)
                    changeSetting = changeSetting*( changeSetting<500 ) + 500*( changeSetting>=500 )
                #if(changeSetting==0):
                #        changeSetting=1
                if( (changeSetting==0).all() ):
                        changeSetting= changeSetting + 1*(abs(self.refVoltageA-voltage)>0.003)

                setting = setting+changeSetting
                if( (setting> 4095).any() or (setting<0).any()   ):
                    print("ALERT, Setting is:", setting, "The Changesetting was:", changeSetting)
                    setting = setting * (1*( setting>0 )*(setting<4095) ) + 1500*(setting >= 4095) + 1500*(setting <= 0)

                temp = np.array(voltage)
                #print(setting)
                for i, module in enumerate(self.moduleList):
                    module.WriteASICSetting("PMTref4_{}".format(group), asic, int(setting[i]), True)
                time.sleep(0.5)
                for i, module in enumerate(self.moduleList):
                    voltage[i] = self.readNode(module, asic)
                changeVoltage=abs( voltage - temp)
                #print("Result: Change setting:", changeSetting, " new voltage:", voltage, "old voltage:", temp, "Changevoltage", changeVoltage)
                stepCount+=1


        print("Final tuning result node C. For ASIC{} and group {}".format(asic, group), " voltage:", voltage, "DAC setting:", setting )
        if( (abs(self.refVoltageC-voltage)>0.003).any() ):
            print("********************************************ALERT: ALGORITHM DID NOT CONVERGE!!!!********************************************")
        for i, module in enumerate(self.moduleList):
            temperature[i] = self.read_adc(module)[0][0]

        return setting, voltage, temperature

    def triggerTuning(self, pmtref_4_voltage):
        self.refVoltageC = pmtref_4_voltage
        for idx, mod_id in enumerate(self.moduleIDList):
            if mod_id in self.failed_modules:
                self.moduleIDList.pop(idx)
                self.moduleList.pop(idx)

        allModsNodeA = np.zeros((len(self.moduleList), self.num_asic, self.num_channels_per_asic, 3))
        allModsNodeB = np.zeros((len(self.moduleList), self.num_asic, self.num_channels_per_asic, 3))
        allModsNodeC = np.zeros((len(self.moduleList), self.num_asic, self.num_groups_per_asic, 3))

        allModsNodeA_temp = np.zeros((len(self.moduleList), self.num_asic, self.num_channels_per_asic))
        allModsNodeB_temp = np.zeros((len(self.moduleList), self.num_asic, self.num_channels_per_asic))
        allModsNodeC_temp = np.zeros((len(self.moduleList), self.num_asic, self.num_groups_per_asic))



        start_tuningA = time.time()
        #Tune NodeA of all initialized modules:
        for asic in range(self.num_asic):
            for channel in range(self.num_channels_per_asic):
                settings, voltages, temperatures = self.tuneNodeA(asic, channel)
                for modind in range(len(self.moduleList)):
                    allModsNodeA[modind, asic, channel] = np.array([settings[modind], voltages[modind], self.refVoltageA])
                    allModsNodeA_temp[modind, asic, channel] = temperatures[modind]
        stop_tuningA = time.time()
        print("IT TOOK ", stop_tuningA - start_tuningA, "SECONDS, TO TUNE NODE A ON ALL CHANNELS AND MODULES.")
        #Tune NodeB of all initialized modules:
        start_tuningB = time.time()
        for asic in range(self.num_asic):
            for channel in range(self.num_channels_per_asic):
                settings, voltages, temperatures = self.tuneNodeB(asic, channel)
                for modind in range(len(self.moduleList)):
                    allModsNodeB[modind, asic, channel] = np.array([settings[modind], voltages[modind], self.refVoltageB])
                    allModsNodeB_temp[modind, asic, channel] = temperatures[modind]
        stop_tuningB = time.time()
        print("IT TOOK ", stop_tuningB - start_tuningB, "SECONDS, TO TUNE NODE B ON ALL CHANNELS AND MODULES.")

        #Tune NodeC of all initialized modules:
        start_tuningC = time.time()
        for asic in range(self.num_asic):
            for group in range(self.num_groups_per_asic):
                settings, voltages, temperatures = self.tuneNodeC(asic, group)
                for modind in range(len(self.moduleList)):
                    allModsNodeC[modind, asic, group] = np.array([settings[modind], voltages[modind], self.refVoltageC])
                    allModsNodeC_temp[modind, asic, group] = temperatures[modind]
        stop_tuningC = time.time()
        print("IT TOOK ", stop_tuningC - start_tuningC, "SECONDS, TO TUNE NODE C ON ALL CHANNELS AND MODULES.")


        tunedDataDir = '/data/triggerTuningDatabase/'
        good_temps = []
        bad_temp_mods = []
        for index, modID in enumerate(self.moduleIDList):
            avTemp = round( ( allModsNodeA_temp[index].mean() + allModsNodeB_temp[index].mean() + allModsNodeC_temp[index].mean() )/3.0, 1)
            #To make sure that every module gets a sensible temperature written into the tuning file:
            if(avTemp>0 and avTemp<90):
                good_temps.append(avTemp)
            else:
                print(f"Module {modID}: Bad temp {avTemp}")
                bad_temp_mods.append((index, modID))
                continue


            filename = tunedDataDir + "mod_"+str(modID)+"_pmtref4voltage_"+str(pmtref_4_voltage)+"_triggerTuning.hdf5"
            f = h5py.File(filename, "a")

            keyList = [key for key in f.keys()]
            if str(avTemp) not in keyList:

                temp = f.create_group(str(avTemp))

                temp.create_dataset("A", data=allModsNodeA[index])
                temp.create_dataset("B", data=allModsNodeB[index])
                temp.create_dataset("C", data=allModsNodeC[index])
        stored_good_av_temp = np.mean(good_temps)
        for index, modID in bad_temp_mods: #in bad_temps:
            filename = tunedDataDir + "mod_" + str(modID) + "_pmtref4voltage_" + str(pmtref_4_voltage) + "_triggerTuning.hdf5"
            f = h5py.File(filename, "a")
            keyList = [key for key in f.keys()]
            if str(stored_good_av_temp) not in keyList:
                temp = f.create_group(str(stored_good_av_temp))
                temp.create_dataset("A", data=allModsNodeA[index])
                temp.create_dataset("B", data=allModsNodeB[index])
                temp.create_dataset("C", data=allModsNodeC[index])




