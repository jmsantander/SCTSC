from sctcamsoft.slow_control_gui.device_controls.device_controls import DeviceControls
from sctcamsoft.slow_control_gui.device_controls.display_utils import draw_lineedit_val
from sctcamsoft.slow_control_gui.device_controls.led_control import led_control

VALUE_TIMEOUT_SECONDS = 35

class PowerControls(DeviceControls):
    def __init__(self, widgets, update_signal,
                 timer_signal, send_command_slot):
        super().__init__('power', [],
                 widgets, 6, update_signal, 
                 timer_signal, send_command_slot)

        self.widgets.cam_power_on.clicked.connect(
            lambda: self.send_command('power_on_no_HV'))
        self.widgets.cam_power_on_with_hv.clicked.connect(
            lambda: self.send_command('power_on'))
        self.widgets.cam_power_on_with_hv.clicked.connect(
            lambda: led_control('on', self.widgets._led3))

        self.widgets.cam_power_off.clicked.connect(
            lambda: self.send_command('power_off'))
        self.widgets.cam_power_off.clicked.connect(
            lambda: led_control('off', self.widgets._led3))



    def draw(self):
        draw_lineedit_val(self.get_val('supply_current'),
                          self.is_expired('supply_current'),
                          self.get_alert_if_asserted('power_supply_current'),
                          self.widgets.supply_current_lineedit,
                          "Power","supply_current",
                          self.widgets)

        draw_lineedit_val(self.get_val('supply_nominal_voltage'),
                          self.is_expired('supply_nominal_voltage'),
                          "NA",
                          self.widgets.supply_nom_volts_lineedit,
                          "Power","supply_nominal_voltage",
                          self.widgets)

        draw_lineedit_val(self.get_val('supply_measured_voltage'),
                          self.is_expired('supply_measured_voltage'),
                          "NA",
                          self.widgets.supply_meas_volts_lineedit,
                          "Power","supply_measured_voltage",
                          self.widgets)

        draw_lineedit_val(self.get_val('HV_current'),
                          self.is_expired('HV_current'),
                          self.get_alert_if_asserted('HV_current'),
                          self.widgets.hv_current_lineedit,
                          "Power","hv_current",
                          self.widgets)

        draw_lineedit_val(self.get_val('HV_nominal_voltage'),
                          self.is_expired('HV_nominal_voltage'),
                          "NA",
                          self.widgets.hv_nom_volts_lineedit,
                          "Power","HV_nominal_voltage",
                          self.widgets)
        
        draw_lineedit_val(self.get_val('HV_measured_voltage'),
                          self.is_expired('HV_measured_voltage'),
                          "NA",
                          self.widgets.hv_meas_volts_lineedit,
                          "Power","HV_measured_voltage",
                          self.widgets)
