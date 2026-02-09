#!/bin/bash
#
# Author:	Thomas Meures
# Date:		22 March 2017
# Version:	v0.0
# Description:	Control main switch of Wiener power supply
#


STATE=$1
snmpset -v 2c -m /home/ctauser/CameraSoftware/trunk/data_taking/powerControl/WIENER-CRATE-MIB-2.txt -c guru 172.17.2.2 sysMainSwitch.0 i $STATE
 
