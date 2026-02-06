
import numpy as np
from PyQt5 import QtWidgets, QtGui
from sctcamsoft.slow_control_gui.device_controls.device_controls import DeviceControls
from sctcamsoft.slow_control_gui.device_controls.display_utils import draw_lineedit_val

class network(DeviceControls):
    def __init__(self, widgets, update_signal,
                 timer_signal, send_command_slot):
        self.widgets=widgets
        widgets.pushButton.clicked.connect(lambda: self.send_command('network/check_interface_activity'))  # what's the meaning of this command?

        super().__init__('network', [],
                 widgets, 6, update_signal,
                 timer_signal, send_command_slot)



    def draw(self):
        draw_lineedit_val(self.get_val('eth6'),
                          self.is_expired('eth6'),
                          self.get_alert_if_asserted('eth6_activity'),
                          self.widgets.Network_lineEdit,
                          "Network","eth6",
                          self.widgets)
        draw_lineedit_val(self.get_val('eth7'),
                          self.is_expired('eth7'),
                          self.get_alert_if_asserted('eth7_activity'),
                          self.widgets.Network_lineEdit_2,
                          "Network","eth7",
                          self.widgets)
        draw_lineedit_val(self.get_val('eth8'),
                          self.is_expired('eth8'),
                          self.get_alert_if_asserted('eth8_activity'),
                          self.widgets.Network_lineEdit_5,
                          "Network","eth8",
                          self.widgets)
        draw_lineedit_val(self.get_val('eth9'),
                          self.is_expired('eth9'),
                          self.get_alert_if_asserted('eth9_activity'),
                          self.widgets.Network_lineEdit_6,
                          "Network","eth9",
                          self.widgets)


