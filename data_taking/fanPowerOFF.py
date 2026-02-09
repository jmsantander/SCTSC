#!/usr/bin/env python
# Telnet protocol follows example at http://www.pythonforbeginners.com/code-snippets-source-code/python-using-telnet
# Another useful example: https://docs.python.org/2/library/telnetlib.html
# protocol provided to FAN constructor should be 'serial' or (default) 'telnet'
# Telnet supported added May 27 2018 by Justin Vandenbroucke

import time, sys, telnetlib

class FAN(object):
    def __init__(self,protocol='telnet'):
        #if protocol=='serial':
        #    self.ser = serial.Serial(port='/dev/ttyACM0',
        #                             baudrate=115200,
        #                             bytesize=8,
        #                             parity='N',
        #                             stopbits=1)
        if protocol=='telnet':
            host = "172.17.2.3"    # see https://confluence.slac.stanford.edu/display/CTA/pSCT+Network+Configuration
            port = 23
            self.ser = telnetlib.Telnet(host, port)
        else:
            print("ERROR: Unknown protocol '" + protocol + "'.  Exiting.")
            sys.exit(1)
            time.sleep(0.15)

    def sendCmd(self, command):
        self.ser.write("{}\n".format(command).encode('ascii'))
        time.sleep(0.1)

    def close(self):
        self.ser.close()

    def fanON(self):
        self.sendCmd("PWR ON") #5V pulse, used to trigger a laser when not using the LED
            
    def fanOFF(self):
        self.sendCmd("PWR OFF")
        self.close()
        time.sleep(1)

if __name__ == "__main__":

    fan = FAN()
    fan.sendCmd("PWR OFF")
    time.sleep(1)
    fan.close()
