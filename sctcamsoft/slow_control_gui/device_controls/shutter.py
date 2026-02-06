from sctcamsoft.slow_control_gui.device_controls.device_controls import DeviceControls
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class ShutterControls(DeviceControls):
    def __init__(self, widgets, update_signal,
                 timer_signal, send_command_signal):

        super().__init__('shutter', ['close_sensor', 'open_sensor'],
                 widgets, 20, update_signal,
                 timer_signal, send_command_signal)
        self.widgets.setStyleSheet("QProgressBar"
                          "{"
                          "border: solid grey;"
                          "border-radius: 15px;"
                          " color: black; "
                          "}"
                          "QProgressBar::chunk "
                          "{background-color: black;"
                          "border-radius :15px;"
                          "}")

    def draw(self):
        close_sensor=self.get_val('close_sensor')
        open_sensor= self.get_val('open_sensor')
        if close_sensor=="0":  #not fully closed
           if open_sensor=="0": #fully open
               self.widgets.progressBar.setValue(1)
               self.widgets.label_2.setText("Shutter is open")
               self.widgets.label_2.setFont(QFont('Arial', 10))

           else:
               self.widgets.progressBar.setValue(3)  #half open
               self.widgets.label_2.setText("Shutter is half open")
               self.widgets.label_2.setFont(QFont('Arial', 10))
        else:          #closed
            self.widgets.progressBar.setValue(6)
            self.widgets.label_2.setText("Shutter is closed")
            self.widgets.label_2.setFont(QFont('Arial', 10))


