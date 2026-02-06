import logging
import os
import sys
import time

import h5py
import pymysql
import numpy as np

# have to give it the full filename if running as a standalone program

nasic = 4
nchannel = 16
ngroup = 4

# this should eventually be changed to an env variable
homedir = os.environ['HOME']
#tunedDataDir = '%s/target5and7data/module_assembly' % homedir

#FIXME: This is a temporary choice, to avoid usage of the remote target5and7data directory. -TM 07/13/2018
tunedDataDir = '/data/triggerTuningDatabase/'

# stores the identifying dataset associated with the tuned values of each module
moduleDict = {
    1:'1_20180326_1107',
    2:'2_20180416_1713',
    3:'3_20180417_0939',
    4:'4_20180322_1824',
    5:'5_20181209_1911',
    6:'6_20180417_1126',
    7:'7_20181212_1956',
    8:'8_20181212_2011',
    9:'9_20180417_1330',
    100:'100_20180418_1513',
    101:'101_20160108_1534',
    103:'103_20181209_1854',
    106:'106_20180329_1044',
    107:'107_20180418_1549',
    #107:'107_20160111_0600',
    108:'108_20180418_1411',
    #108:'108_20160111_1006',
    110:'110_20180418_1436',
    #110:'110_20160112_0626',
    111:'111_20180418_1525',
    #111:'111_20160112_1023',
    112:'112_20180418_1203',
    #112:'112_20160112_1150',
    #113:'113_20160115_0537',
    114:'114_20180418_1537',
    #114:'114_20160112_2057',
    115:'115_20180418_1228',
    #115:'115_20180410_1051',
    #116:'116_20160112_2218',
    #118:'118_20160112_2351',
    119:'119_20180418_1400',
    #119:'119_20160113_0109',
    121:'121_20180418_1423',
    #121:'121_20180410_1701',
    123:'123_20180418_1448',
    #123:'123_20160113_0417',
    124:'124_20180418_1502',
    #124:'124_20160113_0541',
    125:'125_20180418_1255',
    #125:'125_20160113_0703',
    126:'126_20180418_1307',
    #126:'126_20180416_1113',
    #128:'128_20160113_1009'
    }

moduleDict_11_degree = {
    115: '115_20181201_1826',
    8:'8_20181212_2011',
    7:'7_20181212_1956'}

moduleDict_16_degree = {
    115:'115_20181011_2144'}

moduleDict_25_degree = {
    1:'1_20180423_1653',
    2:'2_20180423_1705',
    3:'3_20180423_1718',
    4:'4_20180424_1106',
    6:'6_20180423_1731',
    9:'9_20180423_1744',
    118:'118_20180418_1242',
    125:'125_20180418_1255',
    126:'126_20180418_1307',
    101:'101_20180418_1345',
    119:'119_20180418_1400',
    108:'108_20180418_1411',
    121:'121_20180418_1423',
    110:'110_20180418_1436',
    115:'115_20180418_1228',
    123:'123_20180418_1448',
    124:'124_20180418_1502',
    112:'112_20180418_1203',
    100:'100_20180418_1513',
    111:'111_20180418_1525',
    114:'114_20180418_1537',
    107:'107_20180418_1549',
    106:'106_20180425_0922'
    }

#Temperature may have changed significantly during this run
moduleDict_28_degree = {
    1:'1_20180619_1455',
    2:'2_20180619_1756',
    3:'3_20180619_1352',
    4:'4_20180619_1546',
    6:'6_20180619_1652',
    9:'9_20180619_1404',
    125:'125_20180619_1418',
    126:'126_20180619_1431',
    119:'119_20180619_1508',
    108:'108_20180619_1520',
    121:'121_20180619_1533',
    115:'115_20180619_1559',
    123:'123_20180619_1613',
    124:'124_20180619_1627',
    112:'112_20180619_1639',
    100:'100_20180619_1706',
    111:'111_20180619_1718',
    114:'114_20180619_1730',
    107:'107_20180619_1743',
    106:'106_20180619_1443',
    }
# Former entry for 126: '126_20160113_0837'
# Former entry for 121: 121:'121_20160113_0230'


# takes report from test suite run, scans it for tuning values,
# and returns them in a list
def readVals(filename):
    values = {'Vofs1': np.zeros((nasic, nchannel), dtype='int'),
              'Vofs2': np.zeros((nasic, nchannel), dtype='int'),
              'PMTref4': np.zeros((nasic, ngroup), dtype='int')}
    with open(filename) as testfile:
        for line in testfile.readlines():
            words = line.split()
            if not words or words[0] not in values:
                continue
            setting = words[0]
            asic = words[7] if setting == 'Vofs1' else words[8]
            # channel if Vofs1 or Vofs2, group if PMTref4
            idx = words[9][:-1] if setting == 'Vofs1' else words[10][:-1]
            dac_counts = words[10] if setting == 'Vofs1' else words[11]
            values[setting][int(asic)][int(idx)] = int(dac_counts)

    return tuple(values.values())

def writeBoard(module, Vped, Vofs1, Vofs2, PMTref4):
    # write Vped
    module.WriteSetting('Vped_value', Vped)

    # write Vofs1, Vofs2, PMTref4
    for asic in range(4):
        for group in range(4):
            for ch in range(group*4, group*4 + 4, 1):
                module.WriteASICSetting("Vofs1_{}".format(ch), asic,
                                        int(Vofs1[asic][ch]), True)
                module.WriteASICSetting("Vofs2_{}".format(ch), asic,
                                        int(Vofs2[asic][ch]), True)
            module.WriteASICSetting("PMTref4_{}".format(group), asic,
                                    int(PMTref4[asic][group]), True)


# needs module, 2 module dicts, and list of vtrim voltages
# (or alternatively, a list of vbias voltages)
def getTrims(moduleID):

    nQuads = 100
    hiSide = 70.00 #V

    logging.info(moduleID) #YYY module ID

    # connect to MySQL
    try:
        sql = pymysql.connect(port=3406, host='romulus.ucsc.edu',
                              user='CTAreadonly', password='readCTAdb',
                              database='CTAoffline')
    except:
        sql = pymysql.connect(port=3406, host='remus.ucsc.edu',
                              user='CTAreadonly', password='readCTAdb',
                              database='CTAoffline')
    cursor = sql.cursor()

    # figure out the FPM from SQL
    select_position = "SELECT sector, position FROM associations WHERE module=%(module)s"
    cursor.execute(select_position, {'module': moduleID})
    FPM = cursor.fetchone()
    logging.info(FPM)

    # get quadrant associations for FPM
    select_quads = "SELECT q0, q1, q2, q3 FROM associations WHERE module=%(module)s"
    cursor.execute(select_quads, {'module': moduleID})
    quads = cursor.fetchone()
    logging.info(quads[::-1])

    # grabs the 4 trim voltages of each ASIC/quadrant
    select_trims = "SELECT g0, g1, g2, g3 FROM trimlist WHERE quad=%(quad)s"

    trimsToWrite = []

    # creates a list of the trim voltages for each pixel in each ASIC/quadrant
    # (16 in total)
    for quad in quads:
        cursor.execute(select_trims, {'quad': quad})
        quadtrims = [trim for trim in cursor.fetchone()]
        quadtrims = quadtrims[::-1]
        # The entries for these quadrants are in the wrong order
        # in the database. Correct them here instead of fixing there.
        if moduleID == 124 and quad == "17":
            quadtrims = quadtrims[::-1]
        if moduleID == 119 and quad == "49":
            quadtrims = [quadtrims[i] for i in [3, 1, 2, 0]]
        trimsToWrite.append(quadtrims)

    # ASICs have a reverse correspondence with quadrants
    # a0=q3, a1=q2, a2=q1, a3=q0
    # we reverse the list here because
    # we use the ASICs as indices to set trim voltages in setTrims
    trimsToWrite = trimsToWrite[::-1]

    cursor.close()
    sql.close()

    return trimsToWrite


def setTrims(module, trimsToWrite, HV, addBias=0, moduleID=0, write_log=None):
    """
    Information on what's done here can be found at:
    https://datasheets.maximintegrated.com/en/ds/MAX5713-MAX5715.pdf
    """
    nAsic = 4
    nTrgPxl = 4
    asicDict = {0: 0b0001, 1: 0b0010, 2: 0b0100, 3: 0b1000}
    if HV:
        print("HV is being switched ON")
        module.WriteSetting("HV_Enable", 0b1)
        module.WriteSetting("SelectLowSideVoltage", 0b1)
        # selects all asics
        module.WriteSetting("HVDACControl", 0b1111)
        # sets reference voltage for all asics to 4.096 V
        module.WriteSetting("LowSideVoltage", 0x73000)
        for asic in range(nAsic):
            module.WriteSetting("HVDACControl", asicDict[asic])
            for tpxl in range(nTrgPxl):
                # picks correct trim voltage from list, converts to mV,
                # and converts that to hex
                # db includes -0.6 V trim subtraction from GT breakdown values
                intTrim = int((trimsToWrite[asic][tpxl])*1000 + addBias)
                # QF 2020-Jan-29
                # add a check for range 0-4
                # set it to 0 if intTrim is negative
                # set it to 4V if larger
                if intTrim > 4000:
                    print("trim + bias gives {} mV; I'm setting it to 4000 mV.".format(intTrim))
                    intTrim = 4000
                elif intTrim < 0:
                    print("trim + bias gives {} mV; I'm setting it to 0 mV.".format(intTrim))
                    intTrim = 0
                codeload = 0x30000
                triggerPixel = int("0x%s000"%(tpxl), 16)
                hexWrite = (intTrim | codeload | triggerPixel)
                # value written here will be 0x3XYYY
                # 3 specifies that this is a code n load n operation
                # X specifies trigger ch/pxl as either 0,1,2,3 (in hex)
                # YYY specifies the low side voltage in mV
                print(intTrim)
                if write_log is not None:
                    with open(write_log, 'a') as logfileio:
                        logfileio.write("Mod {} asic {} trig pix {} trim voltage {} mV\n".format(moduleID, asic, tpxl, intTrim))

                module.WriteSetting("LowSideVoltage", hexWrite)
    else:
        print("HV stays OFF")
        module.WriteSetting("HV_Enable", 0b0)
        module.WriteSetting("SelectLowSideVoltage", 0b0)
        # selects all asics
        module.WriteSetting("HVDACControl", 0b0000)


# Set trims to make the shape of a W
# Special purpose - not for regular operation
def setTrimsW(module, moduleID, trimsToWrite):

    # connect to MySQL
    sql = pymysql.connect(port=3406, host='romulus.ucsc.edu',
                          user='CTAreadonly', password='readCTAdb',
                          database='CTAoffline')
    cursor = sql.cursor()

    # figure out the FPM from SQL
    select_position = "SELECT sector, position FROM associations WHERE module=%(module)s"
    cursor.execute(select_position, {'module': moduleID})
    FPM = cursor.fetchone()
    pos = FPM[1]

    cursor.close()
    sql.close()

    closeList = [[[1, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [1, 1, 1, 1], [1, 0, 1, 1]],
                 [[1, 1, 1, 1], [1, 1, 1, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[1, 1, 1, 1], [0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0]],
                 [[1, 0, 1, 0], [1, 1, 0, 1], [0, 0, 0, 0], [0, 1, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 1], [1, 0, 1, 0], [0, 1, 1, 1]],
                 [[1, 1, 1, 1], [0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[1, 1, 1, 1], [1, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]],
                 [[1, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[1, 1, 1, 1], [0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 1, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [1, 1, 1, 1], [1, 0, 1, 0]],
                 [[1, 0, 1, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [1, 0, 1, 0], [0, 0, 0, 0]],
                 [[1, 1, 1, 1], [1, 0, 1, 0], [0, 0, 0, 0], [0, 0, 0, 0]]]
    nAsic = 4
    nTrgPxl = 4
    asicDict = {0 : 0b0001, 1 : 0b0010, 2 : 0b0100, 3 : 0b1000}
    module.WriteSetting("HV_Enable", 0b1)
    module.WriteSetting("SelectLowSideVoltage", 0b1)
    # selects all asics
    module.WriteSetting("HVDACControl", 0b1111)
    # sets reference voltage for all asics to 4.096 V
    module.WriteSetting("LowSideVoltage", 0x73000)
    for asic in range(nAsic):
        module.WriteSetting("HVDACControl", asicDict[asic])
        for tpxl in range(nTrgPxl):
            # picks correct trim voltage from list, converts to mV,
            # and converts that to hex
            # db includes -0.6 V trim subtraction from GT values
            if not closeList[pos][asic][tpxl]:
                intTrim = int(4.095*1000)
            else:
                intTrim = int(trimsToWrite[asic][tpxl]*1000)
            codeload = 0x30000
            triggerPixel = int("0x%s000"%(tpxl), 16)
            hexWrite = (intTrim | codeload | triggerPixel)
            # value written here will be 0x3XYYY
            # 3 specifies that this is a code n load n operation
            # X specifies trigger ch/pxl as either 0,1,2,3 (in hex)
            # YYY specifies the low side voltage in mV
            logging.info(intTrim)
            logging.info(module.WriteSetting("LowSideVoltage", hexWrite))


# Set trims to make the shape of a 1
# Special purpose - not for regular operation
def setTrims1(module, moduleID, trimsToWrite):

    # connect to MySQL
    sql = pymysql.connect(port=3406, host='romulus.ucsc.edu',
                          user='CTAreadonly', password='readCTAdb',
                          database='CTAoffline')
    cursor = sql.cursor()

    # figure out the FPM from SQL
    select_position = "SELECT sector, position FROM associations WHERE module=%(module)s"
    cursor.execute(select_position, {'module': moduleID})
    FPM = cursor.fetchone()
    pos = FPM[1]

    cursor.close()
    sql.close()

    # Pixel access needs to be implemented in the order the FPMs are ordered.
    # ie first line is FPM 4-0, second line is 4-1, etc.
    closeList = [[[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[1, 0, 0, 1], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                 [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]]
    nAsic = 4
    nTrgPxl = 4
    asicDict = {0: 0b0001, 1: 0b0010, 2: 0b0100, 3: 0b1000}
    module.WriteSetting("HV_Enable", 0b1)
    module.WriteSetting("SelectLowSideVoltage", 0b1)
    # selects all asics
    module.WriteSetting("HVDACControl", 0b1111)
    # sets reference voltage for all asics to 4.096 V
    module.WriteSetting("LowSideVoltage", 0x73000)
    for asic in range(nAsic):
        module.WriteSetting("HVDACControl", asicDict[asic])
        for tpxl in range(nTrgPxl):
            # picks correct trim voltage from list, converts to mV,
            # and converts that to hex
            # db includes -0.6 V trim subtraction from GT values
            if not closeList[pos][asic][tpxl]:
                intTrim = int(4.095*1000)
            else:
                intTrim = int((trimsToWrite[(asic)][tpxl])*1000)
            codeload = 0x30000
            triggerPixel = int("0x%s000"%(tpxl), 16)
            hexWrite = (intTrim | codeload | triggerPixel)
            # value written here will be 0x3XYYY
            # 3 specifies that this is a code n load n operation
            # X specifies trigger ch/pxl as either 0,1,2,3 (in hex)
            # YYY specifies the low side voltage in mV
            logging.info(intTrim)
            logging.info(module.WriteSetting("LowSideVoltage", hexWrite))


def raiseTriggerThreshold(module):
    print("Set trigger levels:")
    for asic in range(4):
        for group in range(4):
            print(group, asic, 0x0)
            module.WriteASICSetting("Thresh_{}".format(group), asic, 0x0, True)

# Sets the trigger threshold that has been determined in another test
####Trial code for setting trig thresh for certain PE value for each trigger group
# These trigger levels are for 20PE setting
Default_ThreshLevelList = [729, 754, 804, 679, 665, 743, 754, 615, 604,
                           643, 654, 540, 565, 704, 679, 554]
def setTriggerLevel(module, ThreshLevelList=None):
    if ThreshLevelList is None:
        ThreshLevelList = Default_ThreshLevelList
    time.sleep(1)
    for asic in range(4):
        for group in range(4):
            module.WriteASICSetting("Thresh_{}".format(group), asic,
                                    ThreshLevelList[(asic*4) + group], True)


def getTunedWrite(moduleID, module, Vped, HV=True, numBlock=2, addBias=0, write_log=None):
    # use dict to find dataset to read in from moduleID
    if moduleID in moduleDict_16_degree:
        print("############################################")
        print("****** Loading 16 deg tuning data... ******")
        print("############################################")
        dataset = moduleDict_16_degree[moduleID]
    else:
        dataset = moduleDict[moduleID]

    # create filename from it
    print(tunedDataDir)
    print(dataset)
    filename = "{}/{}/report.txt".format(tunedDataDir, dataset)
    print(filename)
    # read tuning values in from file
    Vofs1, Vofs2, PMTref4 = readVals(filename)
    # write them
    writeBoard(module, Vped, Vofs1, Vofs2, PMTref4)
    time.sleep(0.5)
    if HV:
        trimsToWrite = getTrims(moduleID)
    else:
        trimsToWrite = 0
    logging.info(trimsToWrite)
    logging.info(Vped)
    logging.info(Vofs1)
    logging.info(Vofs2)
    logging.info(PMTref4)
    if moduleID < 20:
        addBias = 0
    setTrims(module, trimsToWrite, HV, addBias, write_log=write_log, moduleID=moduleID)
    time.sleep(0.5)

    print("Setting number of blocks to", numBlock)
    module.WriteSetting("NumberOfBlocks", numBlock - 1)


    #return list of pmtref4 vals
    return PMTref4

def doTunedWrite(moduleID, module, Vped, HV, temp, numBlock=2, addBias=0, write_log=None, pmtref_4_voltage=1.25):
    """ This function should be considered a replacement of getTunedWrite
        that utilizes the newer, smarter tuning algorithm, and the much
        more user-friendly files that it produces. """

    filename = "{}/mod_{}_pmtref4voltage_{}_triggerTuning.hdf5".format(tunedDataDir, moduleID, pmtref_4_voltage)
    f = h5py.File(filename, 'r')
    temps = [float(key) for key in f.keys()]
    temps = np.asarray(temps)
    x = temps[list(np.argpartition(np.abs(temps-temp), 2)[:2])]
    temp_keys = [str(i) for i in x]
    A_data = [f[temp_key]["A"][()] for temp_key in temp_keys]
    B_data = [f[temp_key]["B"][()] for temp_key in temp_keys]
    C_data = [f[temp_key]["C"][()] for temp_key in temp_keys]
    #temp_key = str(temps[np.abs(temps - temp).argmin()])
    #A = f[temp_key]["A"][()]
    #B = f[temp_key]["B"][()]
    #C = f[temp_key]["C"][()]

    module.WriteSetting('Vped_value', Vped)
    Vofs1 = np.zeros((4, 16))
    Vofs2 = np.zeros((4, 16))
    PMTref4 = np.zeros((4, 4))
    # write Vofs1, Vofs2, PMTref4
    for asic in range(4):
        for group in range(4):
            for ch in range(group*4, group*4 + 4, 1):
                A = round(np.interp(temp, x, [A_data[0][asic][ch][0], A_data[1][asic][ch][0]]))
                B = round(np.interp(temp, x, [B_data[0][asic][ch][0], B_data[1][asic][ch][0]]))
                module.WriteASICSetting("Vofs1_{}".format(ch), asic, A, True)
                module.WriteASICSetting("Vofs2_{}".format(ch), asic, B, True)
                Vofs1[asic, ch] = A
                Vofs2[asic, ch] = B
            C = round(np.interp(temp, x, [C_data[0][asic][group][0], C_data[1][asic][group][0]]))
            module.WriteASICSetting("PMTref4_{}".format(group), asic, C, True)
            PMTref4[asic, group] = C
                #module.WriteASICSetting("Vofs1_{}".format(ch), asic,
                #                        int(A[asic][ch][0]), True)
                #module.WriteASICSetting("Vofs2_{}".format(ch), asic,
                #                        int(B[asic][ch][0]), True)
                #Vofs1[asic, ch] = int(A[asic][ch][0])
                #Vofs2[asic, ch] = int(B[asic][ch][0])
            #module.WriteASICSetting("PMTref4_{}".format(group), asic,
            #                        int(C[asic][group][0]), True)
            #PMTref4[asic, group] = int(C[asic][group][0])
    time.sleep(0.5)
    if HV:
        trimsToWrite = getTrims(moduleID)
    else:
        trimsToWrite = 0
    logging.info(trimsToWrite)
    logging.info(Vped)
    logging.info(Vofs1)
    logging.info(Vofs2)
    logging.info(PMTref4)
    #QF 2020-Jan-29, why is this here?
    #if moduleID < 20:
    #    addBias = 0
    setTrims(module, trimsToWrite, HV, addBias, write_log=write_log, moduleID=moduleID)
    time.sleep(0.5)

    print("Setting number of blocks to", numBlock)
    module.WriteSetting("NumberOfBlocks", numBlock - 1)


    #return list of pmtref4 vals
    #return np.asarray(C[:, 0])
    return np.asarray(PMTref4)


if __name__ == "__main__":
    filename = sys.argv[1]
    readVals(filename)
