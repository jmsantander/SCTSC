import serial
import sys
import time
#ser = serial.Serial('/dev/ttyACM0',9600)
port = "/dev/ttyACM0"
if(len(sys.argv) < 3):
	print("TOO FEW ARGUMENTS. NEED <DURATION (s)> <FREQUENCY (Hz)> [port]")
	exit()
elif(len(sys.argv) > 4):
	print("TOO MANY ARGUMENTS. NEED <DURATION (s)> <FREQUENCY (Hz)> [port]")
	exit()
if(int(sys.argv[1]) <= 0):
	print("Duration can't be 0 or negative")
	exit()
if(int(sys.argv[2]) <= 0):
	print("Frequency can't be negative")
	exit()
if(len(sys.argv) == 4):
	port = sys.argv[3]
	if port == "":
		print("Invalid Port")
		exit()	
ser = serial.Serial(port,9600)

if(ser.isOpen()==False):
	print("SERIAL PORT FAILED TO OPEN.")
	exit()
else:
	print("Serial Port %s Opened"%port)
sercommand = "%d,%d"%(int(sys.argv[1]),int(sys.argv[2]))
while True:
	time.sleep(.5)
	s = ser.readline()
	s = s.decode('utf-8')
	s = s[:-1] #get rid of the /r/n
	if s != '':
		print("Received %s"%s)
		s = int(s)
	else:
		print("No Response")
		continue
	if s == 1:
		break
time.sleep(.5)
print("Writing %s"%sercommand)
ser.write(sercommand.encode('utf-8'))
time.sleep(1)
output = ser.readline()
print(output)
output = output.decode('utf-8')
print("Confirmation: %s"%output[:-3])
ser.close()

