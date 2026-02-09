import pexpect
import time
import sys

NUM_SLOTS = 32

# connect to pi, navigate to program and execute it
def executeConnection():
    # Start ssh application
    ssh = pexpect.spawn('ssh pi@172.17.2.6', timeout=50)
    ssh.expect('$')
    # Navigate to directory
    # ssh.sendline("cd /home/pi/Desktop/BP_SPI_interface")
    ssh.sendline("cd /home/pi/Desktop/BP_SPI_interface")
    ssh.expect('$')
    # Execute program
    ssh.sendline("sudo ./bp_test_pi")
    ssh.expect('exit')  # last line of program prompt
    return ssh

def executeConnectionForHitpattern():
    # Start ssh application
    ssh = pexpect.spawn('ssh pi@172.17.2.6', timeout=50)
    ssh.expect('$')
    # Navigate to directory
    # ssh.sendline("cd /home/pi/Desktop/BP_SPI_interface")
    ssh.sendline("cd /home/pi/Desktop/pi_hpread")
    ssh.expect('$')
    # Execute program
    ssh.sendline("sudo ./bp_test_pi")
    ssh.expect('exit')  # last line of program prompt
    return ssh

def logout(ssh):
    ssh.sendline("x")
    ssh.sendline("logout")

# sends a sync signal
def sendSync(ssh):
    ssh.sendline("s")
    ssh.expect("exit")
    print(ssh.before.decode())

# part of automating trigger hitpattern readout and file movement
def recordHitpatternFile(ssh, rate, duration):
    ssh.sendline("9")
    ssh.expect("Enter")  # Prompt for the rate in Hz
    ssh.sendline(str(rate))
    ssh.expect("Enter")  # Prompt for the duration in s
    ssh.sendline(str(duration))
    print("recordHitpatternFile() executed")

def moveHitpatternFile(ssh, runID):
    print("Trying moveHitpatternFile()")
    ssh.sendline("x")
    time.sleep(1)
    ssh.sendline(f"mv hitpattern.txt hitpattern{runID}.txt")
    time.sleep(1)
    ssh.sendline("logout")
    print("moveHitpatternFile() executed")

def sendClockReset(ssh):
    ssh.sendline("l")
    ssh.expect("exit")
    print(ssh.before.decode())

#Get Hardware trigger count
def requestTrigCount(ssh):
    ssh.sendline("c")
    ssh.expect("HW")
    dataOut = ssh.before
    lines = dataOut.decode().strip().split(' ')
    return int(lines[-1])

def requestHitPattern(ssh):
    hitPattern = []
    ssh.sendline("7")
    ssh.expect("read:")
    for __ in range(32):
        ssh.expect(",")
        dataOut = ssh.before
        lines = dataOut.decode().strip().split(',')
        hitPattern.append(lines[0])
    return hitPattern

def resetHitPattern(ssh):
    ssh.sendline("l")

def getTimingInformation(ssh):
    '''In progress function for testing the lack of nanosecond level precision
    This one is for getting the ns clock time'''
    ssh.sendline("c")
    ssh.expect(" ns")
    clock_time = ssh.before.decode().strip().split(' ')
    return int(clock_time[-1])

def setTrigAtTime(ssh, des_time, until=True):
    '''
    Args:
    ssh: duh
    until(int): time until the desired trigger, in ns
    '''
    if until:
        current_time = getTimingInformation(ssh)
        trigger_time = current_time + des_time
    else:
        trigger_time = des_time
    trigger_time_hex = hex(trigger_time)[2:]
    trigger_time_hex = "0"*(16-len(trigger_time_hex))+trigger_time_hex
    ssh.sendline("d")
    ssh.expect("hex: ")
    #print(trigger_time_hex[:4]
    ssh.sendline(trigger_time_hex[:4])
    ssh.expect("hex: ")
    #print(trigger_time_hex[4:8]
    ssh.sendline(trigger_time_hex[4:8])
    ssh.expect("hex: ")
    #print(trigger_time_hex[8:12]
    ssh.sendline(trigger_time_hex[8:12])
    ssh.expect("hex: ")
    #print(trigger_time_hex[12:16]
    ssh.sendline(trigger_time_hex[12:16])
    print("The times: ", current_time, trigger_time, hex(trigger_time))

    #do something afterwards? No, that will be in brendan_DataGathering.py
    return trigger_time

def sendCalTrig(ssh, run_duration, freq):
    ssh.sendline("t")
    ssh.expect("seconds!")
    print(ssh.before.decode(), "seconds!")
    ssh.sendline(str(run_duration))
    ssh.expect("Hz!")
    print(ssh.before.decode(), "Hz!")
    ssh.sendline(str(freq))
    print("setting cal trig freq to {}".format(freq))


def sendModTrig(ssh, run_duration, freq, output=False):
    ssh.sendline("k")
    ssh.expect("seconds!")
    if output:
        print(ssh.before.decode(), "seconds!")
    ssh.sendline(str(run_duration))
    ssh.expect("Hz!")
    if output:
        print(ssh.before.decode(), "Hz!")
    ssh.sendline(str(freq))
    ssh.expect("exit")

# can find the hex values for the modules being turned on
def turnOnSlot(slotList):
    mask = 0b0
    for slot in slotList:
        turnOn = (0b1<<slot)
        binCommand = (turnOn|mask)
        hexCommand = hex(binCommand)
        mask = binCommand
        print(binCommand)
        print(hexCommand)

# tell backplane which slots to deliver power to
# slots is a list of slot numbers to turn on with all others off
# if slots is not given, turn all slots off
# use hexadecimal number with on bits to specify the slots turned on
def powerFEE(ssh, slots=None):
    if slots:
        # The available slots are 0-31
        bits = [1 if slot in slots else 0 for slot in range(NUM_SLOTS)]
        # Convert list of bits to big-endian hexadecimal representation
        bitstring = ''.join(reversed([str(bit) for bit in bits]))
        hexstring = hex(int(bitstring, 2))
    else:
        hexstring = hex(0)
    try:
        ssh.sendline("n")
        ssh.expect("FFFF:")
        ssh.sendline(hexstring)
        ssh.expect("exit")
    except:
        print(ssh.before.decode())
        sys.exit()

# sets trigger mask with file that closes all triggers (during setup)
def setTriggerMaskClosed(ssh, output=False):
    ssh.sendline("j")
    ssh.expect("read!")
    if output:
        print(ssh.before.decode())
    ssh.sendline("trigger_mask_null")
    ssh.expect("exit")
    if output:
        print(ssh.before.decode())

#This opens the trigger mask to all specified modules
def setTriggerMaskDirectly(ssh, binTrigSlots):
    ssh.sendline("8")
    ssh.expect("mask:")
    ssh.sendline(binTrigSlots)
    ssh.expect("exit")

# sets trigger mask for data taking for single group
def setTriggerMaskSingle(ssh, module, asic, group, output=True):
    ssh.sendline("5")
    ssh.expect("triggering!")
    if output:
        print(ssh.before.decode())
    ssh.sendline(str(module))
    ssh.expect("triggering!")
    if output:
        print(ssh.before.decode())
    ssh.sendline(str(asic))
    ssh.expect("triggering!")
    if output:
        print(ssh.before.decode())
    ssh.sendline(str(group))
    ssh.expect("exit")
    if output:
        print(ssh.before.decode())

# sets trigger mask for data taking
def setTriggerMask(ssh, output=False):
    ssh.sendline("j")
    ssh.expect("read!")
    if output:
        print(ssh.before.decode())
    ssh.sendline("trigger_mask")
    ssh.expect("exit")
    if output:
        print(ssh.before.decode())

def enableTACK(ssh, output=False):
    ssh.sendline("g")
    ssh.expect("16-31")
    if output:
        print(ssh.before.decode())
    ssh.sendline("6f")
    ssh.expect("exit")
    if output:
        print(ssh.before.decode())

def disableTACK(ssh, output=False):
    ssh.sendline("g")
    ssh.expect("16-31")
    if output:
        print(ssh.before.decode())
    ssh.sendline("0")
    ssh.expect("exit")
    if output:
        print(ssh.before.decode())

def setHoldOff(ssh, holdTime, output=False):
    ssh.sendline("o")
    ssh.expect("hex :")
    if output:
        print(ssh.before.decode())
    ssh.sendline(holdTime)
    ssh.expect("exit")
    if output:
        print(ssh.before.decode())

if __name__ == "__main__":
    myssh = executeConnection()
    pattern = requestHitPattern(myssh)
    print(pattern, len(pattern))
