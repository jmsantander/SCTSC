#!/data/software/anaconda2/bin/python
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 18 14:06:41 2019

@author: colin adams :^)

Many apologies, this should have been written in an object-oriented fashion.
"""
# TODO do timestamp logging in database for flasher information


from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
        QDial, QDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QScrollBar, QSizePolicy,
        QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit,
        QVBoxLayout, QFormLayout, QWidget, QMessageBox)
#import serial
#import time
import pexpect
from pexpect import pxssh
import sys
import argparse

import struct
import functools

import pymysql
from datetime import datetime

parser=argparse.ArgumentParser()
parser.add_argument('--dry_run',
                        type=bool,
                        default=False,
                        help='Run without controlling the flasher (default=False)')
args = parser.parse_args()

chr = functools.partial(struct.pack,'B')

windows_system = False
dry_run = args.dry_run

arduino_port = "/dev/ttyUSB0"

ftrigger_script_dir = "/home/pi"
fpattern_script_dir = "/home/pi/Desktop"

# flasher port names f0_top, f1_middle, f2_bottom
dev_names=["/dev/ttyUSB_flasher0_top", 
           "/dev/ttyUSB_flasher1_middle", 
           "/dev/ttyUSB_flasher2_bottom"]

flasher_order = {0:"top", 1:"middle", 2:"bottom"}
# bit 0|1|2|3|4|5|6|7|8|9 -> L2|L5|L7|L9|L10|L1|L3|L4|L6|L8
bit_list = {0:"L2",1:"L5",2:"L7",3:"L9",4:"L10",
            5:"L1",6:"L3",7:"L4",8:"L6",9:"L8"}
# bit resistance for each L#
LED_resistance = {"L2":100,"L5":110,"L7":120,"L9":140,"L10":130,
                    "L1":80,"L3":80,"L4":80,"L6":80,"L8":80}

LED_IDs = ["L1","L2","L3","L4","L5","L6","L7","L8","L9","L10"]
bitShiftDict = {"L1":4, "L2":9, "L3":3, "L4":2, "L5":8, 
                "L6":1, "L7":7, "L8":0, "L9":6, "L10":5}

class WidgetGallery(QDialog):
    def __init__(self, parent=None):
        super(WidgetGallery, self).__init__(parent)

        self.executePiConnection()

        self.createTriggerBox()
        self.createPatternBox()

        mainLayout = QGridLayout()
        mainLayout.addWidget(self.patternBox,0,0)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setLineWidth(1)
        mainLayout.addWidget(separator,0,1)

        mainLayout.addWidget(self.triggerBox,0,2)

        self.setLayout(mainLayout)

    def createPatternBox(self):
        self.patternBox = QGroupBox("Set LED patterns")
        self.patternBox.setObjectName("pattern")
        self.patternBox.setStyleSheet("QGroupBox#pattern {font-weight: bold; }")
        self.patternLayout = QVBoxLayout()
        self.patternBox.setLayout(self.patternLayout)

        self.flasherBoxes = [None]*3
        self.dimLEDBoxes = [None]*3
        self.brightLEDBoxes = [None]*3
        
        self.flasherLayouts = [None]*3
        self.dimLayouts = [None]*3
        self.brightLayouts = [None]*3

        self.LED_ID_checkBoxes = [[None]*10 for i in range(3)]
        self.flasher_states = [None]*3

        self.resistanceLabel = QLabel("Remember that P = V^2/R (higher resistance => dimmer light output)")
        self.patternLayout.addWidget(self.resistanceLabel)

        for flasher_num in range(3):
            self.createFlasherBox(flasher_num)
            self.patternLayout.addWidget(self.flasherBoxes[flasher_num])

        self.runButton = QPushButton("Program flasher patterns")
        self.runButton.clicked.connect(self.on_programLEDs_clicked)
        self.patternLayout.addWidget(self.runButton)

    def createFlasherBox(self,flasher_num):
        self.flasherBoxes[flasher_num] = QGroupBox("Flasher {} ({})".format(flasher_num,flasher_order[flasher_num]))
        
        self.flasherLayouts[flasher_num] = QVBoxLayout()
        self.flasherBoxes[flasher_num].setLayout(self.flasherLayouts[flasher_num])
        self.flasherBoxes[flasher_num].setObjectName("flasher{}".format(flasher_num))
        self.flasherBoxes[flasher_num].setStyleSheet("QGroupBox#flasher{} {{ font-weight:bold; }}".format(flasher_num))

        self.dimLEDBoxes[flasher_num] = QGroupBox("Dim LEDs")
        self.brightLEDBoxes[flasher_num] = QGroupBox("Bright LEDs")
        self.dimLayouts[flasher_num] = QHBoxLayout()
        self.brightLayouts[flasher_num] = QHBoxLayout()

        for LED_ind in range(10):
            self.LED_ID_checkBoxes[flasher_num][LED_ind] = QCheckBox("{} {}({} Ω){}".format(LED_IDs[LED_ind], " " if LED_resistance[LED_IDs[LED_ind]] < 100 else "", LED_resistance[LED_IDs[LED_ind]], " " if LED_resistance[LED_IDs[LED_ind]] < 100 else ""))
        for LED_ind in range(10):
            LED_num = LED_ind+1
            
            # if LED is bright add check box to bright layout, else add to dim
            if LED_resistance["L{}".format(LED_num)] < 100: #Ohms
                self.brightLayouts[flasher_num].addWidget(self.LED_ID_checkBoxes[flasher_num][LED_ind])
            else:
                self.dimLayouts[flasher_num].addWidget(self.LED_ID_checkBoxes[flasher_num][LED_ind])
        self.brightLayouts[flasher_num].addStretch(1)
        self.dimLayouts[flasher_num].addStretch(1)

        self.dimLEDBoxes[flasher_num].setLayout(self.dimLayouts[flasher_num])
        self.brightLEDBoxes[flasher_num].setLayout(self.brightLayouts[flasher_num])

        self.flasherLayouts[flasher_num].addWidget(self.dimLEDBoxes[flasher_num])
        self.flasherLayouts[flasher_num].addWidget(self.brightLEDBoxes[flasher_num])

        toggleButton = QPushButton("Toggle LEDs OFF/ON")
        toggleButton.clicked.connect(functools.partial(self.on_toggle_clicked,flasher_num))
        self.flasherLayouts[flasher_num].addWidget(toggleButton)

    def createTriggerBox(self):
        self.triggerBox = QGroupBox("Set flasher triggers")
        self.triggerBox.setObjectName("trigger")
        self.triggerBox.setStyleSheet("QGroupBox#trigger { font-weight: bold; }")

        self.triggerLayout = QFormLayout()
        self.triggerBox.setLayout(self.triggerLayout)

        self.durPrompt = QLabel("Flasher duration [s]")
        self.freqPrompt = QLabel("Flasher rate [Hz]")

        self.flasherDuration = QLineEdit()
        self.flasherFreq = QLineEdit()

        self.triggerButton = QPushButton("Trigger flashers")
        self.triggerButton.clicked.connect(self.on_trigger_clicked)

        self.triggerLayout.addRow(self.durPrompt,self.flasherDuration)
        self.triggerLayout.addRow(self.freqPrompt, self.flasherFreq)
        self.triggerLayout.addRow(self.triggerButton)


    # connect to pi, navigate to program dirs
    def executePiConnection(self):
        if not windows_system:
            # Use encoding compatible with Python 2 flasher scripts on the Pi
            self.ssh = pxssh.pxssh()#encoding='latin-1')
            # increase sync_multiplier if having trouble syncing prompt
            self.ssh.login("172.17.2.6","pi",sync_multiplier=3)
        else:
            self.ssh = pexpect.popen_spawn.PopenSpawn('ssh pi@cta5',timeout=50)
        
        self.ssh.prompt(timeout=20)
        
    # if "Trigger flashers" button pressed, execute set_flasher_trigger function
    def on_trigger_clicked(self):
        set_duration = self.flasherDuration.text()
        set_freq = self.flasherFreq.text()
        
        trigger_msg = QMessageBox.question(None,"Confirming programming","Do you wish to program the flashers to {} Hz for {} s?".format(set_freq,set_duration), QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

        if trigger_msg == QMessageBox.Yes:
            alert = QMessageBox()
            self.set_flasher_trigger(set_duration,set_freq)
            alert.setText("Ok, programming completed")
            alert.exec_()

    # sets the duration and frequency to trigger all (top, middle, bottom) flashers
    def set_flasher_trigger(self,duration,freq):
        print("Setting flasher trigger to {} Hz for {} s".format(freq,duration))
        if not dry_run:
            self.ssh.sendline('python {}/rpiToArduino.py {} {}'.format(ftrigger_script_dir, duration, freq))
            self.ssh.prompt(timeout=100)
            print(self.ssh.before)
        else:
            print("Pranked! I didn't actually do it because you wanted a dry run.")
    
    
    # if "Program LEDs" button pressed, execute write_pattern function for that flasher
    def on_programLEDs_clicked(self):
        #here parse the various buttons that are selected
        #send info to the PSOC
        singleFlasherStates = [[None]*10,[None]*10,[None]*10]
        for flasher_num in range(3):
            for i, ID in enumerate(LED_IDs):
                singleFlasherStates[flasher_num][i] = self.LED_ID_checkBoxes[flasher_num][i].isChecked() << bitShiftDict[ID]
        for flasher_num in range(3):
            flasher_state = 0
            for i in range(len(LED_IDs)):
                flasher_state = flasher_state | singleFlasherStates[flasher_num][i]
            self.flasher_states[flasher_num] = flasher_state
        
        check_program = QMessageBox.question(None,
                                             "Confirm programming",
                                             "Flasher 0 (top):    {:010b}\n"\
                                             "Flasher 1 (middle): {:010b}\n"\
                                             "Flasher 2 (bottom): {:010b}\n"\
                                             "Do you wish to program the flashers to these states?"\
                                             .format(self.flasher_states[0],self.flasher_states[1],self.flasher_states[2]),
                                             QMessageBox.Yes | QMessageBox.Cancel,
                                             QMessageBox.Cancel)

        if check_program == QMessageBox.Yes:
            alert = QMessageBox()
            #pattern's 5 least significant bits are L1  L3  L4  L6  L8 (bright)
            #pattern's 5 most significant bits are L2  L5  L7  L9  L10 (dim)
            #so should go in like: L2  L5  L7  L9  L10 L1  L3  L4  L6  L8
            self.write_patterns()
            
            alert.setText("Ok, programming completed")
            alert.exec_()

        
    # writes the LED pattern of the flasher through the port which it's connected
    def write_patterns(self):
        for flasher_num, pattern in enumerate(self.flasher_states):
                print("Configuring LED pattern {:010b} for flasher {} ({})".format(pattern, 
                                                                              flasher_num, 
                                                                              flasher_order[flasher_num]))
        if not dry_run:
            self.ssh.sendline("python {}/LED_Flasher_Test_all.py {:010b} {:010b} {:010b}".format(fpattern_script_dir,
                                                                self.flasher_states[0],
                                                                self.flasher_states[1],
                                                                self.flasher_states[2]))
            self.ssh.prompt(timeout=100)
            print(self.ssh.before)
        else:
            print("Pranked! I didn't actually do it because you wanted a dry run.")


    def on_toggle_clicked(self,flasher_num):
        allOFF=True
        for LED_ind in range(10):
            if self.LED_ID_checkBoxes[flasher_num][LED_ind].isChecked():
                allOFF=False
        
        for LED_ind in range(10):
            if allOFF:
                self.LED_ID_checkBoxes[flasher_num][LED_ind].setChecked(True)
            else:
                self.LED_ID_checkBoxes[flasher_num][LED_ind].setChecked(False)
    """
    def is_flasher_on(self):
        # string to grab the most recent entry in flasher_log table
        select_last_entry = "SELECT * FROM flasher_log order by start_time desc limit 1"
        self.cursor.execute(select_last_entry)
        last_entry = self.cursor.fetchone()
        
        # last flasher sequence stopped at start_time + duration
        stop_time = last_entry[0]+last_entry[1]

        # if last flasher sequence stop_time is beyond the current time: flasher is on
        flasher_on = datetime.utcnow() < stop_time

        return flasher_on
    """

if __name__ == "__main__":
    import sys
    
    app = QApplication([])
    app.setStyle('Fusion')
    gallery = WidgetGallery()
    gallery.show()
    sys.exit(app.exec_())
