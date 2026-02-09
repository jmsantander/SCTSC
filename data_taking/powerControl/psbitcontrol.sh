#!/bin/bash
#
# Author:	Colin Adams
# Date:		12 Dec 2016
# Version:	v0.1
# Applied changes:	v0.1: Thomas Meures: remove all control of u2, since this is now a slave to u0

# Description:	Control output for Wiener power supply
# 
# NOTE: need to sleep after setting each outputSwitch
# or you risk undefined behavior (sometimes works)




if [ $# -eq 3 ]; then
	echo "turning on with command line args"
	u0on=$1
	u4on=$2
elif [ $# -eq 1 ]; then
	echo "Using input bitmask!"
	onbits=$(echo "ibase=2; $1"|bc)
	chmask="000001"
	echo $onbits
	echo $chmask
	for i in {0..4}
	do
		
		if [ $i -ne 2 ]; then
			chon=$((($onbits&$chmask)!=0))
			echo "On channel: " $chon
			snmpset -v 2c -m $CTA_CONTROL_DIR/powerControl/WIENER-CRATE-MIB-2.txt -c guru 172.17.2.2 outputVoltage.u0 Float: 70.0
			snmpwalk -v 2c -m $CTA_CONTROL_DIR/powerControl/WIENER-CRATE-MIB-2.txt -c guru 172.17.2.2 outputVoltage.u$i
			snmpset -v 2c -m $CTA_CONTROL_DIR/powerControl/WIENER-CRATE-MIB-2.txt -c guru 172.17.2.2 outputSwitch.u$(($i)) i $chon
			#echo "channel $i is $chon"
		fi
		chmask=$(($chmask << 1))
		echo "CHmask: " $chmask
	done
else
	echo ""
	echo "It's time to select for which channels to enable output"

	echo ""
	echo "Set Voltages"
	echo "____________"
	snmpwalk -v 2c -m $CTA_CONTROL_DIR/powerControl/WIENER-CRATE-MIB-2.txt -c guru 172.17.2.2 outputVoltage.u0
	snmpwalk -v 2c -m $CTA_CONTROL_DIR/powerControl/WIENER-CRATE-MIB-2.txt -c guru 172.17.2.2 outputVoltage.u4

	echo ""
	echo -n "Enable output for u0 (Enable: 1, Disable: 0): "
	read u0on
	echo -n "Enable output for u2 (Enable: 1, Disable: 0): "
	read u2on
	echo -n "Enable output for u4 (Enable: 1, Disable: 0): "
	read u4on
	echo ""

fi

if  [ "$u0on" = "1" ]; then
	echo "u0 will be turned on"
	#snmpset -v 2c -m ~/powerControl/WIENER-CRATE-MIB-2.txt -c guru 10.0.50.241 outputSwitch.1 i 1
fi

if  [ "$u2on" = "1" ]; then
	echo "u2 will be turned on"
	#snmpset -v 2c -m ~/powerControl/WIENER-CRATE-MIB-2.txt -c guru 10.0.50.241 outputSwitch.3 i 1
fi

if  [ "$u4on" = "1" ]; then
	echo "u4 will be turned on"
	#snmpset -v 2c -m ~/powerControl/WIENER-CRATE-MIB-2.txt -c guru 10.0.50.241 outputSwitch.5 i 1
fi

echo ""
echo "Measured Voltages"
echo "_________________"
snmpwalk -v 2c -m $CTA_CONTROL_DIR/powerControl/WIENER-CRATE-MIB-2.txt -c guru 172.17.2.2 outputMeasurementSenseVoltage.u0
snmpwalk -v 2c -m $CTA_CONTROL_DIR/powerControl/WIENER-CRATE-MIB-2.txt -c guru 172.17.2.2 outputMeasurementSenseVoltage.u4

echo ""
echo "Measured Currents"
echo "_________________"
snmpwalk -v 2c -m $CTA_CONTROL_DIR/powerControl/WIENER-CRATE-MIB-2.txt -c guru 172.17.2.2 outputMeasurementCurrent.u0
snmpwalk -v 2c -m $CTA_CONTROL_DIR/powerControl/WIENER-CRATE-MIB-2.txt -c guru 172.17.2.2 outputMeasurementCurrent.u4




