# Test code for CHEC LED Flasher
import sys

# Sends <Add><Space><lo><Space><hi><Space><CR> to configure LEDs
# (The last space is redundant but makes the PSoC code easier to write)
# 115200 Baud, 8 Data Bits, No Parity, 1 Stop Bit

# Add: P1 P2 A4 A3 A2  A1 1  1
# lo:  L2 L5 L7 L9 L10 0  1  1
# hi:  L1 L3 L4 L6 L8  1  1  1

# P1 & P2 are the pointing LEDs
# A4-A1 is the flasher address (set to zero)
# L1-L10 are the 10 flasher LEDs (lo and hi brightness)

# Command bytes must be >= 3 hence bits 0 and 1 are always set

# Leave a small gap between messages for the flasher to process
# each command sequence

import serial
import time

#ser = serial.Serial('COM5',115200)
#QF mac: 
#ser = serial.Serial('/dev/tty.usbserial-FTA65VLD',115200)
#ser = serial.Serial('/dev/tty.usbserial-FTA6CTV1',115200)
# flasher 2
#ser = serial.Serial('/dev/tty.usbserial-FT98DF0Q',115200)
# flasher 4
#ser = serial.Serial('/dev/tty.usbserial-FTA6CTO4',115200)
# flasher 1 FTA65VHF
#ser = serial.Serial('/dev/tty.usbserial-FTA65VHF',115200)
# flasher 3 FTA6BLF4
#ser = serial.Serial('/dev/tty.usbserial-FTA6BLF4',115200)


#ser = serial.Serial('/dev/ttyUSB0',115200)
#ser = serial.Serial('/dev/tty.usbserial-FT98DF0Q',115200)


def write_ser(dev):
    ser = serial.Serial(dev, 115200)
    print 'CHEC LED Flasher Test'
    print("Device {}".format(dev))
    
    time.sleep(1)
    
    print 'Configuring LEDs'
    
    # Flasher 0
    ser.write(chr(0b11000011)) # Byte 1 (Add): P1  P2  A4  A3  A2  A1  1  1
    ser.write(chr(32)) # Space
    ser.write(chr(0b11111011)) # Byte 2 (Lo) : L2  L5  L7  L9  L10 0   1  1
    ser.write(chr(32)) # Space
    ser.write(chr(0b11111111)) # Byte 3 (Hi) : L1  L3  L4  L6  L8  1   1  1
    ser.write(chr(32)) # Space
    ser.write(chr(13)) # CR
    
    time.sleep(0.01)
    
    # Flasher 1
    #ser.write(chr(0b00000111)) # Byte 1 (Add): P1  P2  A4  A3  A2  A1  1  1
    #ser.write(chr(32)) # Space
    #ser.write(chr(0b00000011)) # Byte 2 (Lo) : L2  L5  L7  L9  L10 0   1  1
    #ser.write(chr(32)) # Space
    #ser.write(chr(0b00000111)) # Byte 3 (Hi) : L1  L3  L4  L6  L8  1   1  1
    #ser.write(chr(32)) # Space
    #ser.write(chr(13)) # CR
    
    #time.sleep(0.01)
    
    # Flasher 2
    #ser.write(chr(0b00001011)) # Byte 1 (Add): P1  P2  A4  A3  A2  A1  1  1
    #ser.write(chr(32)) # Space
    #ser.write(chr(0b00000011)) # Byte 2 (Lo) : L2  L5  L7  L9  L10 0   1  1
    #ser.write(chr(32)) # Space
    #ser.write(chr(0b00000111)) # Byte 3 (Hi) : L1  L3  L4  L6  L8  1   1  1
    #ser.write(chr(32)) # Space
    #ser.write(chr(13)) # CR
    
    #time.sleep(0.01)
    
    # Flasher 3
    #ser.write(chr(0b00001111)) # Byte 1 (Add): P1  P2  A4  A3  A2  A1  1  1
    #ser.write(chr(32)) # Space
    #ser.write(chr(0b00000011)) # Byte 2 (Lo) : L2  L5  L7  L9  L10 0   1  1
    #ser.write(chr(32)) # Space
    #ser.write(chr(0b00000111)) # Byte 3 (Hi) : L1  L3  L4  L6  L8  1   1  1
    #ser.write(chr(32)) # Space
    #ser.write(chr(13)) # CR
    
    #time.sleep(1)
    
    print 'Received:'
    
    try:
        while ser.inWaiting() > 0:
            print(ser.read(1))
            print "0x%0.2X"%ord(ser.read(1))
    except KeyboardInterrupt:
        print("Measurement stopped")
        pass
    finally:
        print 'Bye!'
        ser.close()
        print("Serial connection closed")
    
    #print 'Now toggling RTS/Trigger...'
    
    #try:
    #    while True:
    #        ser.setRTS(True)
    #        #time.sleep(0.001)
    #        ser.setRTS(False)
    #        #time.sleep(0.001)
    
    #except KeyboardInterrupt:
    #    print 'Ctrl-C Received!'
    
    #finally:
    
    #print 'Bye!'
    #ser.close()
    #print("Serial connection closed")

if(len(sys.argv) < 2):
    print("Too few arguments, need at least one device e.g., '/dev/tty.usbserial-FTA6BLF4'")
else:
    for dev in sys.argv[1:]:
        write_ser(dev)

