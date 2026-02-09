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
        QVBoxLayout, QWidget, QMessageBox)
#import serial
#import time
import pexpect
from pexpect import pxssh
import sys
import argparse

import struct
import functools

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

flasher_order = ["top", "middle", "bottom"]

# connect to pi, navigate to program dirs
def executePiConnection():
    if not windows_system:
        # Use encoding compatible with Python 2 flasher scripts on the Pi
        ssh = pxssh.pxssh()#encoding='latin-1')
        # increase sync_multiplier if having trouble syncing prompt
        ssh.login("172.17.2.6","pi",sync_multiplier=3)
    else:
        ssh = pexpect.popen_spawn.PopenSpawn('ssh pi@cta5',timeout=50)
    ssh.prompt(timeout=100)
                                           #last line of program prompt
    return ssh


# sets the duration and frequency to trigger all (top, middle, bottom) flashers
def set_flasher_trigger(duration, freq):
    print("Setting flasher trigger to {} Hz for {} s".format(freq,duration))
    if not dry_run:
        ssh.sendline('python {}/rpiToArduino.py {} {}'.format(ftrigger_script_dir, duration, freq))
        ssh.prompt(timeout=100)
        print(ssh.before)
    else:
        print("Pranked! I didn't actually do it because you wanted a dry run.")
    
# writes the LED pattern of the flasher through the port which it's connected
def write_patterns(flasher_states):
    for i, pattern in enumerate(flasher_states):
            print("Configuring LED pattern {:010b} for flasher {} ({})".format(pattern, 
                                                                          i, 
                                                                          flasher_order[i]))
    if not dry_run:
        ssh.sendline("python {}/LED_Flasher_Test_all.py {:010b} {:010b} {:010b}".format(fpattern_script_dir,
                                                            flasher_states[0],
                                                            flasher_states[1],
                                                            flasher_states[2]))
        ssh.prompt(timeout=100)
        print(ssh.before)
    else:
        print("Pranked! I didn't actually do it because you wanted a dry run.")
        
# creates box for dim LEDs within a flasher box
def createDimBox(flasher_num, dimLEDBoxes, dim_layouts, LED_ID_checkBoxes):
    #pattern's 5 most significant bits are L2  L5  L7  L9  L10 (dim)
    dimLEDBoxes[flasher_num] = QGroupBox("Dim LEDs")
    
    LED_ID_checkBoxes[flasher_num][2-1] = QCheckBox("L2 (100 Ω)")
    LED_ID_checkBoxes[flasher_num][5-1] = QCheckBox("L5 (110 Ω)")
    LED_ID_checkBoxes[flasher_num][7-1] = QCheckBox("L7 (120 Ω)")
    LED_ID_checkBoxes[flasher_num][9-1] = QCheckBox("L9 (140 Ω)")
    LED_ID_checkBoxes[flasher_num][10-1] = QCheckBox("L10 (130 Ω)")
    
    dim_layouts[flasher_num] = QHBoxLayout()
    dim_layouts[flasher_num].addWidget(LED_ID_checkBoxes[flasher_num][2-1])
    dim_layouts[flasher_num].addWidget(LED_ID_checkBoxes[flasher_num][5-1])
    dim_layouts[flasher_num].addWidget(LED_ID_checkBoxes[flasher_num][7-1])
    dim_layouts[flasher_num].addWidget(LED_ID_checkBoxes[flasher_num][9-1])
    dim_layouts[flasher_num].addWidget(LED_ID_checkBoxes[flasher_num][10-1])
    dim_layouts[flasher_num].addStretch(1)
    dimLEDBoxes[flasher_num].setLayout(dim_layouts[flasher_num])

#creates box for bright LEDs within a flasher box
def createBrightBox(flasher_num, dimLEDBoxes, dim_layouts, LED_ID_checkBoxes):
    #pattern's 5 least significant bits are L1  L3  L4  L6  L8 (bright)
    brightLEDBoxes[flasher_num] = QGroupBox("Bright LEDs")
    
    LED_ID_checkBoxes[flasher_num][1-1] = QCheckBox("L1  (80 Ω) ")
    LED_ID_checkBoxes[flasher_num][3-1] = QCheckBox("L3  (80 Ω) ")
    LED_ID_checkBoxes[flasher_num][4-1] = QCheckBox("L4  (80 Ω) ")
    LED_ID_checkBoxes[flasher_num][6-1] = QCheckBox("L6  (80 Ω) ")
    LED_ID_checkBoxes[flasher_num][8-1] = QCheckBox("L8  (80 Ω) ")
    
    bright_layouts[flasher_num] = QHBoxLayout()
    bright_layouts[flasher_num].addWidget(LED_ID_checkBoxes[flasher_num][1-1])
    bright_layouts[flasher_num].addWidget(LED_ID_checkBoxes[flasher_num][3-1])
    bright_layouts[flasher_num].addWidget(LED_ID_checkBoxes[flasher_num][4-1])
    bright_layouts[flasher_num].addWidget(LED_ID_checkBoxes[flasher_num][6-1])
    bright_layouts[flasher_num].addWidget(LED_ID_checkBoxes[flasher_num][8-1])
    bright_layouts[flasher_num].addStretch(1)
    brightLEDBoxes[flasher_num].setLayout(bright_layouts[flasher_num])

# if "Trigger flashers" button pressed, execute set_flasher_trigger function
def on_trigger_clicked(flasher_num):
    set_duration = flasher_durations[flasher_num].text()
    set_freq = flasher_freqs[flasher_num].text()
    print("Setting flashers to {} Hz for {} s".format(set_freq,set_duration))
    set_flasher_trigger(set_duration, set_freq)

# if "Program LEDs" button pressed, execute write_pattern function for that flasher
def on_programLEDs_clicked():
    #here parse the various buttons that are selected
    #send info to the PSOC
    flasher_states = [None]*3
    singleFlasherStates = [[None]*10,[None]*10,[None]*10]
    LED_IDs = ["L1","L2","L3","L4","L5","L6","L7","L8","L9","L10"]
    bitShiftDict = {"L1":4, "L2":9, "L3":3, "L4":2, "L5":8, 
                    "L6":1, "L7":7, "L8":0, "L9":6, "L10":5}
    for flasher_num in range(3):
        for i, ID in enumerate(LED_IDs):
            singleFlasherStates[flasher_num][i] = LED_ID_checkBoxes[flasher_num][i].isChecked() << bitShiftDict[ID]
    
    for flasher_num in range(3):
        flasher_state = 0
        for i in range(len(LED_IDs)):
            flasher_state = flasher_state | singleFlasherStates[flasher_num][i]
        flasher_states[flasher_num] = flasher_state
    
    check_program = QMessageBox.question(None,
                                         "Confirm programming",
                                         "Flasher 0 (top):    {:010b}\n"\
                                         "Flasher 1 (middle): {:010b}\n"\
                                         "Flasher 2 (bottom): {:010b}\n"\
                                         "Do you wish to program the flashers to these states?"\
                                         .format(flasher_states[0],flasher_states[1],flasher_states[2]),
                                         QMessageBox.Yes | QMessageBox.Cancel,
                                         QMessageBox.Cancel)

    if check_program == QMessageBox.Yes:
        alert = QMessageBox()
        #pattern's 5 least significant bits are L1  L3  L4  L6  L8 (bright)
        #pattern's 5 most significant bits are L2  L5  L7  L9  L10 (dim)
        #so should go in like: L2  L5  L7  L9  L10 L1  L3  L4  L6  L8
        write_patterns(flasher_states)
        
        alert.setText("Ok, programming completed")
        alert.exec_()

# set up arduino
# =============================================================================
# ser = serial.Serial(arduino_port,9600)
# if(ser.isOpen()==False):
# 	print("SERIAL PORT FAILED TO OPEN.")
# 	exit()
# else:
# 	print("Serial Port %s Opened"%port)
# =============================================================================
if not dry_run:
    ssh = executePiConnection()

app = QApplication([])
app.setStyle('Fusion')
#app.setStyleSheet("QGroupBox { margin: 2ex; }")
window = QWidget()
mainLayout = QGridLayout()

flasher_durations = [None]*3
flasher_freqs = [None]*3
header_labels = [None]*3
trigger_buttons = [None]*3

dimLEDBoxes = [None]*3
dim_layouts = [None]*3
brightLEDBoxes = [None]*3
bright_layouts = [None]*3
LED_ID_checkBoxes = [[None]*10,[None]*10,[None]*10]

for i in range(3):
    createDimBox(i, dimLEDBoxes, dim_layouts, LED_ID_checkBoxes)
    createBrightBox(i, brightLEDBoxes, bright_layouts, LED_ID_checkBoxes)

flasher_boxes = [None]*3
flasher_layouts = [None]*3

for i in range(3):
    flasher_boxes[i] = QGroupBox("Flasher {} ({})".format(i, flasher_order[i]))
    flasher_layouts[i] = QVBoxLayout()
    flasher_boxes[i].setLayout(flasher_layouts[i])
    flasher_boxes[i].setObjectName("flasher{}".format(i))
    flasher_boxes[i].setStyleSheet("QGroupBox#flasher{} {{ font-weight: bold; }}".format(i))
#    flasher_boxes[i].setStyleSheet("QGroupBox { font-weight: bold; }")
#    flasher_boxes[i].setStyleSheet("QGroupBox#flasher{} {{ margin: 2ex; }}".format(i))

for i in range(3):
    flasher_layouts[i].addWidget(dimLEDBoxes[i])
    flasher_layouts[i].addWidget(brightLEDBoxes[i])

for i in range(3):
    mainLayout.addWidget(flasher_boxes[i])

run_button = QPushButton('Program flasher patterns')
run_button.clicked.connect(on_programLEDs_clicked)    
mainLayout.addWidget(run_button)

separator = QFrame()
separator.setFrameShape(QFrame.HLine)
separator.setLineWidth(1)
mainLayout.addWidget(separator)

resistance_label = QLabel("Remember that P=V^2/R (higher resistance => dimmer light output)")
mainLayout.addWidget(resistance_label)

arduino_box = QGroupBox("Set flasher triggers")
arduino_box.setObjectName("arduino")
arduino_box.setStyleSheet("QGroupBox#arduino { font-weight: bold; }")

arduino_layout = QGridLayout()
arduino_box.setLayout(arduino_layout)

for i in range(1):
#    header_labels[i] = QLabel("Flasher trigger")
    flasher_durations[i] = QLineEdit()
    flasher_durations[i].setPlaceholderText("Flasher duration [s]")
    flasher_freqs[i] = QLineEdit()
    flasher_freqs[i].setPlaceholderText("Flasher rate [Hz]")
    trigger_buttons[i] = QPushButton("Trigger flashers".format(i))
    trigger_buttons[i].clicked.connect(functools.partial(on_trigger_clicked,i))
#    arduino_layout.addWidget(header_labels[i],0,i)
    arduino_layout.addWidget(flasher_durations[i],1,i)
    arduino_layout.addWidget(flasher_freqs[i],2,i)
    arduino_layout.addWidget(trigger_buttons[i],3,i)

mainLayout.addWidget(arduino_box)

window.setLayout(mainLayout)
window.show()
app.exec_()
