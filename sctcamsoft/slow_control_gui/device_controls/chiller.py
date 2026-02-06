from sctcamsoft.slow_control_gui.device_controls.device_controls import DeviceControls
from sctcamsoft.slow_control_gui.device_controls.display_utils import draw_lineedit_val

class ChillerControls(DeviceControls):
    def __init__(self, widgets, update_signal, 
                 timer_signal, send_command_signal):

        super().__init__('chiller', ['pressure', 'temperature'], 
                 widgets, 20, update_signal, 
                 timer_signal, send_command_signal)

    def draw(self):

        draw_lineedit_val(self.get_val('pressure'),
                          self.is_expired('pressure'),
                          None,
                          self.widgets.chiller_pressure_lineedit,
                          "Chiller", "pressure",
                          self.widgets)

        draw_lineedit_val(self.get_val('temperature'),
                          self.is_expired('temperature'),
                          None,
                          self.widgets.chiller_temp_lineedit,
                          "Chiller", "temperature",
                          self.widgets)
