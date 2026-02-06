from sctcamsoft.slow_control_gui.device_controls.device_controls import DeviceControls
from sctcamsoft.slow_control_gui.device_controls.display_utils import draw_lineedit_val
from sctcamsoft.slow_control_gui.device_controls.led_control import led_control

VALUE_TIMEOUT_SECONDS = 35
import numpy as np
class FanControls(DeviceControls):
    def __init__(self, widgets, update_signal, 
                 timer_signal, send_command_slot):

        super().__init__('fan', ['fan_voltage', 'fan_current'],
                 widgets, 6, update_signal, 
                 timer_signal, send_command_slot)
        self.widgets=widgets
        #self.send_command('fan/open_connection')
        self.widgets.pushButton_2.clicked.connect(lambda: self.send_command('fans_on'))
        # widgets.pushButton_2.clicked.connect(lambda: led_control('on', self.widgets._led2))
        self.widgets.pushButton_3.clicked.connect(lambda: self.send_command('fans_off'))
        # widgets.pushButton_3.clicked.connect(lambda: led_control('off', self.widgets._led2))

    def draw(self):

        voltage=self.get_val('voltage')
        current=self.get_val('current')
        if(voltage==None or current==None):
            print("No Fan Voltage/Current reading yet")
        else:
            if (np.float(voltage)>22 and np.float(current)>10): #Fan is on
                led_control('on', self.widgets._led2)
            else:
                led_control('off', self.widgets._led2)
        draw_lineedit_val(voltage,
                          self.is_expired('voltage'), 
                          self.get_alert_if_asserted('fan_voltage'),
                          self.widgets.lineEdit_3,
                          "Fan","voltage",
                          self.widgets)

        draw_lineedit_val(current,
                          self.is_expired('current'), 
                          self.get_alert_if_asserted('fan_current'),
                          self.widgets.lineEdit_4,
                          "Fan","current",
                          self.widgets)


