from psct_toolkit import DataTaker, TuneNodeABC
from run_info import get_run_info

#moduleIDList = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100,
#                103, 106, 107, 108, 111, 112, 114,
#                115, 119, 121, 123, 124, 125, 126] #current All

moduleIDList = [1, 9, 114, 115]

#trigger_modules = [100, 103, 106, 107, 108, 111,
#                   112, 114, 119, 123, 124, 125]

trigger_modules = moduleIDList

run_duration = 300  # (s) Amount of time to warm the camera
triggers = False # Choose to warm the camera with triggers open / closed

static_threshold = [75]*16
num_blocks = 4
hv_on = False
retry = True

read_adc_period = 30  # seconds
read_temperatures = True
read_currents = False

channels_per_packet = 32
psocket_buffer_size = 999424
packet_separation = 4000
packet_delay = 0
trigger_delay = 668
add_bias = 0  # mV

run_info = get_run_info()

data = DataTaker(moduleIDList, trigger_modules,
                 HVon=hv_on, static_threshold=static_threshold,
                 numBlock=num_blocks, chPerPacket=channels_per_packet,
                 triggerDly=trigger_delay, addBias=add_bias,
                 packetSeparation=packet_separation,
                 packetDelay=packet_delay,
                 read_adc_period=read_adc_period,
                 read_temperatures=read_temperatures,
                 read_currents=read_currents,
                 pSocketBufferSize=psocket_buffer_size, run_info=run_info, retry=retry)

try:
    data.prepareModules()
    if triggers is True:
        data.open_trigger_mask()
    else:
        data.close_trigger_mask()
     
    data.initialize_run()
    data.special_sleep()
    data.close_trigger_mask()
    #data.triggerTuning() 
    data.closeMods()
except:
    data.closeMods()
    raise

