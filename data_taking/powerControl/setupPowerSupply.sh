#!/bin/bash

# Author: Thomas Meures
# Purpose: Wrapper for standard power supply control




if [ $# -eq 2 ]; then
	startup=$1
	HVENABLE=$2
else
	read -p "Would you like to start powering the backplane or shutdown (Input 1 for startup, 0 for shutdown: " startup
	echo "You have selected: " $startup
fi

if [ $startup -eq 0 ];then
	echo "Power is shutting down!"
	bash psbitcontrol.sh 0
	sleep 2
	bash mainPowerSwitch.sh 0
	sleep 1
	#python ../fanPowerOFF.py
else
	echo "Starting power supply!"
	#python ../fanPower.py
	sleep 1
	bash mainPowerSwitch.sh 1
	sleep 2
	
	if [ $# -ne 2 ]; then
		read -p "Would you like to enable HV (yes=1, No=0):" HVENABLE
	fi
	if [ $HVENABLE -eq 1 ]; then
		echo "Enabling HV."
		bash psbitcontrol.sh 010001
	else
		echo "HV OFF"
		echo "Please make sure that HV is disabled in tuneModule.py for data taking (just for safety. It probably does not hurt to leave it alone)."
		bash psbitcontrol.sh 000001
	fi
fi
