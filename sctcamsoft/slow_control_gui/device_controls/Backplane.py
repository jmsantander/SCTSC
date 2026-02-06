from PyQt5 import QtWidgets, QtGui
from sctcamsoft.slow_control_gui.device_controls.device_controls import DeviceControls
from sctcamsoft.slow_control_gui.device_controls.display_utils import draw_lineedit_val

class BackplaneControls(DeviceControls):
    def __init__(self, widgets, update_signal,
                 timer_signal, send_command_slot):
        self.widgets=widgets
        widgets.comboBox_3.addItem("backplane/reboot_dacq_1")
        widgets.comboBox_3.addItem("backplane/reboot_dacq_2")
        widgets.pushButton_9.clicked.connect(lambda: self.send_command(widgets.comboBox_3.currentText())) #go button
        super().__init__('backplane', [],
                 widgets, 6, update_signal,
                 timer_signal, send_command_slot)
    def draw(self):
        pass


