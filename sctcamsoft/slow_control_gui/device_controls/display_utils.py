from PyQt5 import QtGui, Qt
from PyQt5.QtGui import QColor
from PyQt5.Qt import QPalette
import os
import logging
import logging.handlers
from sctcamsoft.slow_control_gui.device_controls.log import QTextEditLogger
from datetime import datetime
import numpy as np
alert_sm = {'Fan': {'current': False, 'voltage': False},  # state machine alert
            'Power': {'supply_current': False, 'hv_current': False},
            'Chiller': {'pressure': False, 'temperature': False},
            'Network': {'eth6': False, 'eth7': False, 'eth8': False,'eth9': False},
            }

def draw_lineedit_val(value, is_expired, alert, lineedit, device, _alert_name, widge):
    """Updates a single pyqt lineedit with a value.

    Args:
        value: The value text that should be written into the lineedit.
        is_expired: Boolean, controls text strikethrough.
        alert: An AlertUpdate object, or None. For updating the lineedit's
            background color and tooltip. 
        lineedit: The lineedit widget to update.
    """
    global alert_sm

    font = QtGui.QFont()
    # commented by wd, the expired function may cause confusion to the users and may not needed for the current settings
    # if (is_expired):
    #     font.setStrikeOut(True)
    # else:
    #     font.setStrikeOut(False)
    lineedit.setFont(font)

    palette = QPalette()
    if (alert == None):
        # If the alert is not current asserted, set black-on-white text
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.Text, QColor(0, 0, 0))
        lineedit.setToolTip("")

        alert_sm[device][_alert_name]=False

    elif (alert == "NA"):    #if alert is not available
        pass

    else:
        # If the alert is currently asserted, set white-on red, and 
        # update the tooltip accordingly
        palette.setColor(QPalette.Base, QColor(255, 0, 0))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))

        lineedit.setToolTip(
            f'ALERT\n'
            f'{alert.name}\n'
            f'Current value:   {alert.value} {alert.units}\n'
            f'Lower limit      {alert.lower_limit}\n'
            f'Upper limit:     {alert.upper_limit}\n'
            f'Last sent:       {str(alert.time_sent)}')

        alert_sm[device][_alert_name] =  True
        logTextBox = QTextEditLogger(widge)
        logTextBox.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(logTextBox)  #Handler is an object responsible for dispatching the appropriate log messages
        logging.warning(device + "    " + _alert_name + " " + alert.value + alert.units)
        logging.getLogger().handlers.clear()


        ##file to save logging: to do
        filename=datetime.today().strftime('%Y-%m-%d')+".log"
        fileHandler = logging.FileHandler( filename, mode="a+")
        fileHandler.setLevel(logging.WARNING)
        fileHandler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(fileHandler)

    # # turn on the LED alert
    # if all(value == False for value in alert_sm[device].values())==True:
    #     ledpaint.value=False
    # else:
    #     ledpaint.value = True
    if (value != None):
      value = np.around(np.float(value), decimals=2)  ##round to 2 desimals
    lineedit.setPalette(palette)
    lineedit.setText(str(value))





