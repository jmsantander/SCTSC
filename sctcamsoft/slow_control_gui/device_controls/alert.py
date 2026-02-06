import time
import threading
import sctcamsoft.slow_control_gui.device_controls.display_utils as dis
import os
from sctcamsoft.slow_control_gui.device_controls.led_control import led_control
import socket
"""
If any alert was marked in the dis.alert_sm(global variable), alert.py will record the alert
and make the warning sound

also will try to check the server every 3 seconds to test the connection.

"""
class alert:
    def __init__(self, widgets, timer_signal,hostname):
         timer_signal.connect(self._on_timer)
         timer_signal.connect(self._check_server)
         self.hostname=hostname
         self.widgets = widgets
    def _on_timer(self):
        for k, v in dis.alert_sm.items():
            for k1, v1 in v.items():
                if v1==True:
                    str =k+" "+k1+" "+"warning"
                    # os.system('say %s' % (str)) #only works in MacOS


    def _check_server(self):
        a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        location = (self.hostname, 54321)
        result_of_check = a_socket.connect_ex(location)
        if result_of_check == 0:
            led_control('on', self.widgets._led1)
            self.widgets.label_3.setText("Connected")
            # print("Port is open")
        else:
            # print("Port is not open")
            led_control('off', self.widgets._led1)
            self.widgets.label_3.setText("No connection")