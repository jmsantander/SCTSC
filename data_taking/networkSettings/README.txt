#####
Instructions for network settings.

To setup the server for module operation execute the following:

For the DACQ boards:
$ ./setupTMAddressesDACQ.sh

For the server network interfaces:
$ sudo ./networkSettings.sh

## for troubleshooting
1: reset network interfaces 
$ sudo ifconfig eth0 down
$ sudo ifconfig eth0 up

2: start dhclient if necessary
$ sudo dhclient eth0

3: run network setting script
$ sudo ./networkSettings.sh

4: reset DACQ board
go to pi to do this

5: Setup DACQ boards again
$ ./setupTMAddressesDACQ.sh

