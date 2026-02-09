
#!/bin/bash

# Author: Thomas Meures
# Purpose: Check output currents for safety.

echo ""
echo "Measured Currents"
echo "_________________"
snmpwalk -v 2c -m $CTA_CONTROL_DIR/powerControl/WIENER-CRATE-MIB-2.txt -c guru 172.17.2.2 outputMeasurementCurrent.u0
snmpwalk -v 2c -m $CTA_CONTROL_DIR/powerControl/WIENER-CRATE-MIB-2.txt -c guru 172.17.2.2 outputMeasurementCurrent.u4
echo ""
echo "Measured Voltages"
echo "_________________"
snmpwalk -v 2c -m $CTA_CONTROL_DIR/powerControl/WIENER-CRATE-MIB-2.txt -c guru 172.17.2.2 outputMeasurementSenseVoltage.u0
snmpwalk -v 2c -m $CTA_CONTROL_DIR/powerControl/WIENER-CRATE-MIB-2.txt -c guru 172.17.2.2 outputMeasurementSenseVoltage.u4
