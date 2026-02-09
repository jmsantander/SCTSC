'''
psct_toolkit_ctc.py: a toolkit for controlling and reading out the pSCT camera
Authors: Zach Curtis-Ginsberg
Created: September 2025
Last edited: Feb 3 2026
Point of contact: curtisginsbe@wisc.edu
Based on:
- psct_toolkit.py by Colin Adams, Leslie Taylor, and other
- TC_utils.py by Leonardo Di Venere, Serena Loporchio, edited by Luca Riitano, Zach Curtis-Ginsberg
- CTC_datataking.py by Luca Riitano, Zach Curtis-Ginsberg
'''


import datetime
import itertools
import os
import pickle
import subprocess
import sys
import time
import argparse

import pandas as pd
import numpy as np
import yaml
import h5py
import enlighten

import target_driver
import target_io
import target_calib

import piCom
import run_control
from MyLogging import logger

class PsctTool():
    '''
    An object posessing the basic attributes and methods for using the pSCT camera. It contains the subclasses:
        DataTaker: perform readout on camera
        TriggerTester: perform scans measuing only triggers with no readout
    '''

    # DACQ subnet IP addresses
    subnet_port_ip = {10: "192.168.10.1", 12: "192.168.12.1"} # Changed from T7 camera
    
    module_def = 'SCTCTC_MSA_FPGA_Firmware0xC0000006.def' # FPGA def file
    ctc_def = 'CTC_ASIC.def' # CTC def file
    ct5tea_def = 'CT5TEA_ASIC.def' # CT5TEA def file

    num_asic = 4 # ASICs per module
    num_groups_per_asic = 4 # Trigger groups per ASIC
    num_channels_per_asic = 16 # Channels per ASIC
    groupsPerMod = num_asic * num_groups_per_asic # Trigger groups per module
    total_blocks = 512 # Storage blocks per channel
    
    # Module/ASIC/Channel fixed settings, should these all just be set in the def file?
    fixed_settings = {'SSTIN_disable': 1, # To disable SST during ramp -> reduce noise
                    # Will be set in def file 'Zero_Enable': 0x0, # TargetIO reader cannot handle zero suppression
                    # Will be set in def file 'DoneSignalSpeedUp': 0,
                    # Will be set in def file 'TACK_TriggerType': 0x0,
                    # Will be set in def file 'TACK_TriggerMode': 0x0,
                    # Will be set in def file 'Vdischarge': 300, # Chosen constant
                    # Will be set in def file 'Vpedbias': 1000, # Chosen constant
                    # Will be set in def file 'WilkinsonClockFreq': 2,
                    # Will be set in def file 'RampSignalDuration': 1312, # Gives theoretical max event rate of ~12.35 kHz
                    'SSToutFB_Delay': 58,
                    ### Needs to be calibrated 'Wbias': 985,
                    'Thresh': 2000, # Chosen constant
                    'TACK_Source' : 0 # 0 is BP, 1 is internal TACK generator
                    'TACK_TriggerType' : 0 ### Maybe shouldn't touch
                    'TACK_TriggerMode' : 0 ### Maybe shouldn't touch
                    'TACK_TriggerDead' : 0 ### Maybe shouldn't touch
                    # Will be set in def file 'SelectSampleClockPhase' : 0x0,
                    # Will be set in def file 'Select_ClockDelay' : 0x1, 
                    # Will be set in def file 'Trig_Gain': 0x15,
                    # Will be set in def file 'Trig_Enable': 0x1,
                    # Will be set in def file 'TriggerDelay': 485, ### This is not static
                    # Will be set in def file 'TPGControl': 0,
                    # Will be set in def file 'Test_Output': 0,
                    # Will be set in def file 'RCLR_LENGTH_END': 0x7,
                    # Will be set in def file 'DurationofDeadtime': 125, # 8 ns per value -> 1 us deadtime, in FPGA def file it says units of us but that's wrong
                    'Hardsync_Phase': 0x1ff, # Is this correct?
                    'Hardsync_Period': 0x3f, # Is this correct?
                    } ### I think this list is complete

    outdir = '/data/ctcdata/' # Output directory for data
    run_control_dir = '/home/ctauser/ctcdata/run_control/' # Output directory for run control files
    logfile = '/home/ctauser/ctcdata/run_log/' # Log file path


    def __init__(self, moduleIDList, trigger_modules, HVon, numBlock=2, num_packets_per_event=1,
                static_threshold=None, pe_threshold=None, read_temperatures=False,
                read_currents=False, retry=False, n_retry=1, smart=False):
        # Load module configuration
        fpm_config = pd.read_csv('FPM_config.csv')
        fee_config = pd.read_csv('FEE_config.csv')
        
        self.moduleIDList = moduleIDList
        self.numBlock = numBlock
        self.kMaxChannelInPacket = int(64 / num_packets_per_event)
        self.kNPacketsPerEvent = num_packets_per_event
        self.kPacketSize = target_driver.DataPacket_CalculatePacketSizeInBytes(self.kMaxChannelInPacket, 32 * self.numBlock)
        self.kBufferDepth = 10000 # Should this change?
        
        self.HVon = HVon
        self.smart = smart
        # Not sure if the trigger masking will be used yet
        if self.HVon:
            masked_tr_pix_file = 'masked_trigger_pixels_HVon.yml'
        else:
            masked_tr_pix_file = 'masked_trigger_pixels_HVoff.yml'
        logger.info('Loading masked trigger pixels from file {}...'.format(masked_tr_pix_file))
        with open(masked_tr_pix_file, 'r') as f:
            self.masked_trigger_pixels = yaml.safe_load(f)
        if self.masked_trigger_pixels is None:
            self.masked_trigger_pixels = {}

        # Determine module network settings
        self.board_IPs = {}
        self.subnets = {}
        for mod_id in self.moduleIDList:
            loc = (fee_config.module_id == mod_id)
            self.board_IPs[mod_id] = fee_config.ip_address.loc[loc].values[0]
            self.subnets[mod_id] = fee_config.dacq_subnet.loc[loc].values[0]

        # Not sure if the trigger masking will be used yet
        # Determine trigger mask positions
        # The first seven (32 -25) trigger mask positions are never used
        self.trigger_mask_positions = [None, None, None, None, None, None, None]
        self.trigger_mask_positions.extend([mod_id for pos, mod_id in sorted(zip(
            fpm_config.trigger_mask_position, fpm_config.module_id))])
        
        # Determine slots for powering modules
        self.power_slots = {mod_id: slot for slot, mod_id
                            in zip(fpm_config.slow_control_slot,
                                    fpm_config.module_id)}

        self.moduleList = []
        self.trigger_modules = trigger_modules

        if static_threshold is None:
            static_threshold = [1000] * self.groupsPerMod #### to be changed
        self.static_threshold = static_threshold
        
        if pe_threshold is None:
            pe_threshold = [11] * self.groupsPerMod ### to be changed?
        self.pe_threshold = pe_threshold
        
        self.pi = piCom.executeConnection()
        
        self.failed_modules = []
        self._trigger_mask_is_open = False
        
        self.run_id = None
        self.read_temperatures = read_temperatures
        self.read_currents = read_currents
        self.write_temperatures = read_temperatures
        self.write_currents = read_currents
        self.temperature_file = None
        self.current_file = None
        self.registers_file = None
        
        self.origin_timestampe = None
        self.run_timestamp = None
        
        self.retry = retry
        self.n_retry = n_retry


    def initModules(self):
        '''
        Initialze modules
        '''
        # Power on all modules one by one (in a backplane)
        # Do not power on all modules at once!!!
        slots = []
        for module_id in self.moduleIDList:
            slots.append(self.power_slots[module_id])
            piCom.powerFEE(self.pi, slots)
            logger.info(f'Powering Module {module_id}')
            time.sleep(0.5)
        
        # Wait for the modules to boot
        time.sleep(10)
        self.establishConnections(self.moduleIDList)
        
        if self.retry is True:
            if self.failed_modules != []:
                for i in range(self.n_retry):
                    logger.warning('Retrying failed modules: {}'.format(self.failed_modules))
                    slots = []
                    for module_id in self.moduleIDList:
                        if module_id not in self.failed_modules:
                            slots.append(self.power_slots[module_id])
                    
                    for module_id in self.failed_modules:
                        slots.append(self.power_slots[module_id])
                        piCom.powerFEE(self.pi, slots)
                        time.sleep(0.5)
                    
                    time.sleep(10)
                    self.establishConnections(self.moduleIDList)
                    
                    if self.failed_modules == []:
                        break
        
        logger.info('***** Setting ASIC Parameters *****')
        self.setASICParams()
        time.sleep(1)
        
        # Match up the system time as closely as possible to
        # the origin of the backplane time
        # This is approximate, mostly due to network latency
        time1 = datetime.datetime.now(datetime.UTC)
        piCom.sendClockReset(self.pi)
        time2 = datetime.datetime.now(datetime.UTC)
        self.origin_timestamp = time1 + (time2 - time1) / 2
        logger.info('Origin timestamp set to {}'.format(self.origin_timestamp))
        logger.info('**** Syncing Now *****')
        piCom.sendSync(self.pi)
        time.sleep(1)

        self.modsToReady()
        
        # Require that all modules are connected
        if self.failed_modules != []:
            logger.error('The following modules failed to connect: {}'.format(self.failed_modules))
            sys.exit('Some modules failed to connect. Exiting...')


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
                                                PsctTool.ctc_def,
                                                PsctTool.ct5tea_def,
                                                idx))
            else:
                idx = i
                self.moduleList.append(
                    target_driver.TargetModule(PsctTool.board_def,
                                                PsctTool.ctc_def,
                                                PsctTool.ct5tea_def,
                                                idx))
            subnet_ip = self.subnet_port_ip[self.subnets[moduleID]]
            board_ip = self.board_IPs[moduleID]
            
            logger.info('Establishing connection to module ID {} at board IP {} on subnet {}'.format(
                moduleID, board_ip, subnet_ip))

            fail = self.moduleList[idx].EstablishSlowControlLink(subnet_ip, board_ip)
            self.moduleList[idx].Initialise()
            self.moduleList[idx].EnableDLLFeedback()

            if fail==0 or fail==3:
                self.connected_modules.append(moduleID)
                port = np.uint16(0)
                dataPort = np.uint16(0)
                regVal = self.moduleList[idx].ReadRegister(0x80)
                port = (regVal[1] >> 16) & 0xFFFF
                dataPort = regVal[1] & 0xFFFF
                
                logger.info('Slow control link established with slow control port {}, data port {}'.format(port, dataPort))
                
                address = 0x02 # LSW of serial code
                hexLSW = self.queryBoard(self.moduleList[idx], address)
                address = 0x03 # MSW of serial code
                hexMSW = self.queryBoard(self.moduleList[idx], address)
                serialCode = '{}{}'.format(hexMSW, hexLSW[2:10])
                
                ret, fw = self.moduleList[idx].ReadRegister(0)
                
                logger.info('Module ID {} has serial code {}, firmware version {}'.format(moduleID, serialCode, fw))
                
                # integer value to identify modules
                self.moduleList[idx].WriteSetting('DetectorID', idx)
                self.moduleList[idx].WriteSetting('CTAID', moduleID)
                
                # Initialze SMART if needed
                if self.smart:
                    self.moduleList[idx].WriteSetting('SMART_SPI_Enable', 0x1)
                else:
                    self.moduleList[idx].WriteSetting('SMART_SPI_Enable', 0x0)
                
                # Preemptively disable triggering
                self.moduleList[idx].WriteSetting('TACK_TriggerEnable', 0) # disable all triggers
                
            else:
                logger.error('Failed to establish slow control link with: {}'.format(fail))
                self.failed_modules.append(moduleID)
        
        for ID in IDList:
            idx = self.moduleIDList.index(ID)
            module = self.moduleList[idx]
            state = module.GetState()
            logger.info('Module ID {} state: {}'.format(ID, state))
            TC_OK = module.GoToPreSync()
            logger.info('Module ID {} into PreSync with return: {}'.format(ID, TC_OK))
            time.sleep(0.1)
            state = module.GetState()
            time.sleep(0.1)
            logger.info('Module ID {} state: {}'.format(ID, state))


    def setASICParams(self):
        '''
        Set the ASIC parameters for all modules
        '''
        for i, moduleID in enumerate(self.moduleIDList):
            idx = self.moduleIDList.index(moduleID)
            module = self.moduleList[idx]
            logger.info('Setting ASIC parameters for module ID {}'.format(moduleID))
            
            # Set Vpeds and VpedBias
            vped_file = 'Vped_settings_module_{}.txt'.format(moduleID) ###
            with open(vped_file, 'r') as f:
                content =f.readlines()
                content = [x.strip() for x in content]
            for asic in range(self.num_asic):
                #logger.debug('VpedBias ASIC {}: {}'.format(asic, PsctTool.fixed_settings['Vpedbias']))
                #module.WriteTriggerASICSetting('VpedBias', asic, int(PsctTool.fixed_settings['Vpedbias']), True) # Standard value: 900
                for channel in range(self.num_channels_per_asic):
                    vped = int(content[asic*16+channel])
                    logger.debug('Vped ASIC {}, channel {}: {}'.format(asic, channel, vped))
                    module.WriteTriggerASICSetting('Vped_{}'.format(channel), asic, vped, True)
            
            # Set SSToutFB_Delay and VtrimT
            vtrimt_file = 'VtrimT_settings_module_{}.txt'.format(moduleID) ###
            sstoutfb = int(PsctTool.fixed_settings['SSToutFB_Delay']) ###
            with open(vtrimt_file, 'r') as f:
                content =f.readlines()
                content = [x.strip() for x in content]
            for asic in range(self.num_asic):
                vtrimt = int(content[asic])
                logger.debug('SSToutFB_Delay ASIC {}: {}'.format(asic, sstoutfb))
                module.WriteASICSetting('SSToutFB_Delay', asic, sstoutfb, True, False) # Standard value: 58
                logger.debug('VtrimT ASIC {}: {}'.format(asic, vtrimt))
                module.WriteASICSetting('VtrimT', asic, vtrimt, True, False)
            
            # Set Ramp and Clock
            isel_file = 'Isel_settings_module_{}.txt'.format(moduleID) ###
            vdischarge = int(PsctTool.fixed_settings['Vdischarge']) ###
            wilkclk = int(PsctTool.fixed_settings['WiklinsonClockFreq']) ###
            rampsig = int(PsctTool.fixed_settings['RampSignalDuration']) ###
            with open(isel_file, 'r') as f:
                content =f.readlines()
                content = [x.strip() for x in content]
            for asic in range(self.num_asic):
                isel = int(content[asic])
                logger.debug('Isel ASIC {}: {}'.format(asic, isel))
                module.WriteASICSetting('Isel', asic, isel, True)
                logger.debug('Vdischarge ASIC {}: {}'.format(asic, vdischarge))
                module.writeASICSetting('Vdischarge', asic, vdischarge)
            logger.debug('Wilkinson Clock Freq: {}'.format(wilkclk))
            module.WriteSetting('WilkinsonClockFreq', wilkclk) # Standard value: 2
            logger.debug('RampSignalDuration: {}'.format(rampsig))
            module.WriteSetting('RampSignalDuration', rampsig) # Standard value: 1312


    def prepareDAQs(self):
        '''
        Prepare modules for data-taking
        '''
        for i, moduleID in enumerate(self.moduleIDList):
            idx = self.moduleIDList.index(moduleID)
            module = self.moduleList[idx]
            logger.info('Preparing module ID {} for data-taking'.format(moduleID))
            
            # Enable ASICs
            ###
            
            # Set module settings
            sstin = int(PsctTool.fixed_settings['SSTIN_disable']) ###
            clockphase = int(PsctTool.fixed_settings['SelectSampleClockPhase']) ###
            clockdelay = int(PsctTool.fixed_settings['Select_ClockDelay']) ###
            zeroenable = int(PsctTool.fixed_settings['Zero_Enable']) ###
            sigspeed = int(PsctTool.fixed_settings['DoneSignalSpeedUp']) ###
            
            logger.debug('SSTIN_disable: {}'.format(sstin))
            module.WriteSetting('SSTIN_disable', sstin) # Standard value: 1
            logger.debug('SelectSampleClockPhase: {}'.format(clockphase))
            module.WriteSetting('SelectSampleClockPhase', clockphase) # Standard value: 0x0
            logger.debug('Select_ClockDelay: {}'.format(clockdelay))
            module.WriteSetting('Select_ClockDelay', clockdelay)
            logger.debug('Zero_Enable: {}'.format(zeroenable))
            module.WriteSetting('Zero_Enable', zeroenable) # Standard value: 0
            logger.debug('DoneSignalSpeedUp: {}'.format(sigspeed))
            module.WriteSetting('DoneSignalSpeedUp', sigspeed) # Standard value: 0
            logger.debug('NumberOfBlocks: {}'.format(self.numBlock))
            module.WriteSetting('NumberOfBlocks', self.numBlock - 1)
            logger.debug('MaxChannelsInPacket: {}'.format(self.kMaxChannelInPacket))
            module.WriteSetting('MaxChannelsInPacket', self.kMaxChannelInPacket)
            
            trigger_delay_file = 'TriggerDelay_settings_module_{}.txt'.format(moduleID)
            with open(trigger_delay_file, 'r') as f:
               content = f.readlines()
               content = [x.strip() for x in content]
            trigger_delay = int(content[0])
            logger.debug('TriggerDelay: {}'.format(trigger_delay))
            module.WriteSetting('TriggerDelay', trigger_delay)
            
            logger.debug('TACK_Source: {}'.format(PsctTool.fixed_settings['TACK_Source']))
            module.WriteSetting('TACK_Source', int(PsctTool.fixed_settings['TACK_Source'])) # 0 = BP, 1 = internal
            logger.debug('TACK_TriggerType: {}'.format(PsctTool.fixed_settings['TACK_TriggerType']))
            module.WriteSetting('TACK_TriggerType', int(PsctTool.fixed_settings['TACK_TriggerType'])) # Standard value: 0x0
            logger.debug('TACK_TriggerMode: {}'.format(PsctTool.fixed_settings['TACK_TriggerMode']))
            module.WriteSetting('TACK_TriggerMode', int(PsctTool.fixed_settings['TACK_TriggerMode'])) # Standard value: 0x0
            
            if triggertype == 2:
                logger.info('Hardsync_Phase: {}'.format(PsctTool.fixed_settings['Hardsync_Phase']))
                module.WriteSetting('Hardsync_Phase', int(PsctTool.fixed_settings['Hardsync_Phase']))
                logger.info('Hardsync_Period: {}'.format(PsctTool.fixed_settings['Hardsync_Period']))
                module.WriteSetting('Hardsync_Period', int(PsctTool.fixed_settings['Hardsync_Period']))
            elif triggertype == 1:
                logger.info('Trigger Direction: External')
                module.WriteSetting('ExtTriggerDirection', 0x0)
            elif triggertype == 0:
                logger.info('Trigger Direction: Internal')
                module.WriteSetting('ExtTriggerDirection', 0x1)
            else:
                logger.error('Invalid trigger type specified: {}'.format(triggertype))
                sys.exit('Invalid trigger type specified: {}'.format(triggertype))


    def setTriggerParams(self):
        '''
        Setting ASIC trigger parameters for all modules
        '''
        for i, moduleID in enumerate(self.moduleIDList):
            idx = self.moduleIDList.index(moduleID)
            module = self.moduleList[idx]
            logger.info('Setting trigger parameters for module ID {}'.format(moduleID))
            
            if self.pe_threshold is not None:
                # Set pe thresholds
                pe_thresh_file = 'pe_thresholds_module_{}.txt'.format(moduleID)
                with open(pe_thresh_file, 'r') as f:
                    content =f.readlines()
                    content = [x.strip() for x in content]
                wbias_file = 'wbias_module_{}.txt'.format(moduleID)
                with open(wbias_file, 'r') as f:
                    wbias_content = f.readlines()
                    wbias_content = [x.strip() for x in wbias_content]
                for asic in range(self.num_asic):
                    for group in range(self.num_groups_per_asic):
                        pmtref4 = int(content[asic*4+group])
                        wbias = int(wbias_content[asic*4+group])
                        logger.debug('Wbias ASIC {}, group {}: {}'.format(asic, group, wbias))
                        module.WriteTriggerASICSetting('Wbias_{}'.format(group), asic, wbias, True) # Standard value: 985?
                        logger.debug('PMTref4 ASIC {}, group {}: {}'.format(asic, group, pmtref4))
                        module.WriteTriggerASICSetting('PMTref4_{}'.format(group), asic, pmtref4, True)
                        logger.debug('Thresh ASIC {}, group {}: {}'.format(asic, group, int(PsctTool.fixed_settings['Thresh'])))
                        module.WriteTriggerASICSetting('Thresh_{}'.format(group), asic, int(PsctTool.fixed_settings['Thresh']), True)
                    for ch in range(self.num_channels_per_asic):
                        logger.debug('Gain ASIC {}, channel {}: {}'.format(asic, ch, PsctTool.fixed_settings['Trig_Gain']))
                        module.WriteTriggerASICSetting('TriggerGain_Ch{}'.format(ch), asic, int(PsctTool.fixed_settings['Trig_Gain']), True)
                        logger.debug('TriggerEnable ASIC {}, channel {}: {}'.format(asic, ch, PsctTool.fixed_settings['Trig_Enable']))
                        module.WriteTriggerASICSetting('TriggerEnable_Ch{}'.format(ch), asic, int(PsctTool.fixed_settings['Trig_Enable']), True) # Enable all trigger channels?
                
            elif self.static_threshold is not None:
                # Set static thresholds
                pmtref4 = int(self.static_threshold)
                wbias_file = 'wbias_module_{}.txt'.format(moduleID)
                with open(wbias_file, 'r') as f:
                    wbias_content = f.readlines()
                    wbias_content = [x.strip() for x in wbias_content]
                for asic in range(self.num_asic):
                    for group in range(self.num_groups_per_asic):
                        pmtref4 = int(content[asic*4+group])
                        wbias = int(wbias_content[asic*4+group])
                        logger.debug('Wbias ASIC {}, group {}: {}'.format(asic, group, wbias))
                        module.WriteTriggerASICSetting('Wbias_{}'.format(group), asic, wbias, True) # Standard value: 985?
                        logger.debug('PMTref4 ASIC {}, group {}: {}'.format(asic, group, pmtref4))
                        module.WriteTriggerASICSetting('PMTref4_{}'.format(group), asic, pmtref4, True)
                        logger.debug('Thresh ASIC {}, group {}: {}'.format(asic, group, int(PsctTool.fixed_settings['Thresh'])))
                        module.WriteTriggerASICSetting('Thresh_{}'.format(group), asic, int(PsctTool.fixed_settings['Thresh']), True)
                    for ch in range(self.num_channels_per_asic):
                        logger.debug('Gain ASIC {}, channel {}: {}'.format(asic, ch, PsctTool.fixed_settings['Trig_Gain']))
                        module.WriteTriggerASICSetting('TriggerGain_Ch{}'.format(ch), asic, int(PsctTool.fixed_settings['Trig_Gain']), True)
                        logger.debug('TriggerEnable ASIC {}, channel {}: {}'.format(asic, ch, PsctTool.fixed_settings['Trig_Enable']))
                        module.WriteTriggerASICSetting('TriggerEnable_Ch{}'.format(ch), asic, int(PsctTool.fixed_settings['Trig_Enable']), True) # Enable all trigger channels?
            else:
                logger.error('No trigger thresholds specified!')
                sys.exit('No trigger thresholds specified!')


    def read_temperatues(self):
        '''
        Read and log temperatures from all modules
        '''
        for i, moduleID in enumerate(self.moduleIDList):
            idx = self.moduleIDList.index(moduleID)
            module = self.moduleList[idx]
            temp1, temp2, temp3, temp4 = -1.0, -1.0, -1.0, -1.0
            ret,temp1 = module.GetTempI2CPrimary()
            logger.debug('Module ID {} Primary Temp: {}'.format(moduleID, temp1))
            ret,temp2 = module.GetTempI2CAux()
            logger.debug('Module ID {} Aux Temp: {}'.format(moduleID, temp2))
            #ret, temp3 =  module.GetTempI2CPower()
            #logger.debug('Module ID {} Power Temp: {}'.format(moduleID, temp3))
            #ret, temp4 =  module.GetTempSIPM()
            #logger.debug('Module ID {} SiPM Temp: {}'.format(moduleID, temp4))
            #return self.temp1, self.temp2, self.temp3, self.temp4


    def read_hv(self):
        '''
        Read and log HV currents from all modules
        '''
        for i, moduleID in enumerate(self.moduleIDList):
            idx = self.moduleIDList.index(moduleID)
            module = self.moduleList[idx]
            ret, current = module.ReadHVCurrentInput()
            correction_factor = 10.0 ### is this correct? INFN_Test_System the FW is expecting 1 ohm resistor shunt, but we are using 0.1 ohm 1%...
            current_amps = current * correction_factor
            logger.debug('Module ID {} HV Current: {} A (not calibrated)'.format(moduleID, current_amps))
            time.sleep(0.01)
            ret, voltage = module.ReadHVVoltageInput()
            logger.debug('Module ID {} HV Voltage: {} V'.format(moduleID, voltage))
            #return current_amps, voltage


    def modsToReady(self):
        for module in self.moduleList:
            fail = module.GoToReady()
            logger.info('Failed:? {}'.format(fail))
            if fail != 0:
                logger.error('MODULE FAILED "GO TO READY"')
        
        for module in self.moduleList:
            state = module.GetState()
            logger.info('Module state: {}'.format(state))


    def closeMods(self):
        '''
        Closes connections to all modules and powers them off
        '''
        for module in self.moduleList:
            module.CloseSockets()
        piCom.powerFEE(self.pi, None)


    def open_trigger_mask(self):
        piCom.setTriggerMask(self.pi)
        self._trigger_mask_is_open = True

    def close_trigger_mask(self):
        piCom.setTriggerMaskClosed(self.pi)
        self._trigger_mask_is_open = False


class DataTaker(PsctTool):
    """
    A subclass of PsctTool possessing the ability to perform various data taking (readout) tasks. Those include:

    Attributes:

    """


class TriggerTester(PsctTool):
    """
    A subclass of PsctTool possessing the ability to perform various trigger (readout) tasks. Those include:

    Attributes:

    """
    TIME_FRAME = 1.0 #seconds