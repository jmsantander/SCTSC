/sbin/ifconfig
/wr/bin/rtu_stat

# associates the FEE number to the last two digets of its MAC address
declare -A FEE
FEE+=([103]="dd" [6]="69" [2]="4c" [100]="51" [101]="59" [107]="40" [108]="b4" [110]="65" [111]="7f" [112]="24" [113]="15" [114]="9d" [115]="f7" [116]="f7" [118]="2d" [119]="82" [121]="e5" [123]="6d" [124]="72" [125]="7a" [126]="bc" [128]="83" )

# associates the slot in the backplane [jslot] with the white rabbit position
declare -A slot0
slot0+=([32]=2 [11]=14 [17]=13 [18]=10 [19]=7 [23]=12 [24]=9 [25]=6 [26]=4 [28]=11 [29]=8 [30]=5 [31]=3 )


#/wr/bin/wrs_vlans --rvid 0 --rfid 0 --rmask 0xff685
#/wr/bin/wrs_vlans --rvid 1 --rfid 1 --rmask 0x0097a

#/wr/bin/wrs_vlans --list
#/wr/bin/wrs_vlans --elist

###VLAN settings:
#/wr/bin/wrs_vlans --ep 0 --emode 0 --evid 0
#/wr/bin/wrs_vlans --ep 1 --emode 0 --evid 1
#/wr/bin/wrs_vlans --ep 2 --emode 0 --evid 0
#/wr/bin/wrs_vlans --ep 3 --emode 0 --evid 1
#/wr/bin/wrs_vlans --ep 4 --emode 0 --evid 1
#/wr/bin/wrs_vlans --ep 5 --emode 0 --evid 1
#/wr/bin/wrs_vlans --ep 6 --emode 0 --evid 1
#/wr/bin/wrs_vlans --ep 7 --emode 0 --evid 0
#/wr/bin/wrs_vlans --ep 8 --emode 0 --evid 1
#/wr/bin/wrs_vlans --ep 9 --emode 0 --evid 0
#/wr/bin/wrs_vlans --ep 10 --emode 0 --evid 0
#/wr/bin/wrs_vlans --ep 11 --emode 0 --evid 1
#/wr/bin/wrs_vlans --ep 12 --emode 0 --evid 0
#/wr/bin/wrs_vlans --ep 13 --emode 0 --evid 0
#/wr/bin/wrs_vlans --ep 14 --emode 0 --evid 0
#/wr/bin/wrs_vlans --ep 15 --emode 0 --evid 0
#/wr/bin/wrs_vlans --ep 16 --emode 0 --evid 0
#/wr/bin/wrs_vlans --ep 17 --emode 0 --evid 0
#/wr/bin/wrs_vlans --ep 18 --emode 0 --evid 0


# associates the FEE number to the slot number so that the computer disregards switch and communicates directly with module
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[112]} ${slot0[26]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[114]} ${slot0[30]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[123]} ${slot0[24]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[124]} ${slot0[25]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[115]} ${slot0[23]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[103]} ${slot0[11]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[119]} ${slot0[17]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[108]} ${slot0[18]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[110]} ${slot0[19]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[100]} ${slot0[28]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[111]} ${slot0[29]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[107]} ${slot0[31]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[6]} ${slot0[32]} 0 0


#assign MAC addr for wr in 1st DACQ board
# /wr/bin/rtu_stat add [MAC address] WRswitchNumber 0 0
####/wr/bin/rtu_stat add 02:34:56:78:9B:01 1 0 1
/wr/bin/rtu_stat add 02:34:56:78:9B:02 2 0 0
/wr/bin/rtu_stat add 02:34:56:78:9B:03 3 0 0	#slot j31
/wr/bin/rtu_stat add 02:34:56:78:9B:04 4 0 0	#slot j26
/wr/bin/rtu_stat add 02:34:56:78:9B:05 5 0 0	#slot j30
/wr/bin/rtu_stat add 02:34:56:78:9B:06 6 0 0	#slot j25
/wr/bin/rtu_stat add 02:34:56:78:9B:07 7 0 0	#slot j19
/wr/bin/rtu_stat add 02:34:56:78:9B:08 8 0 0	#slot j29
/wr/bin/rtu_stat add 02:34:56:78:9B:09 9 0 0	#slot j24
/wr/bin/rtu_stat add 02:34:56:78:9B:0a 10 0 0	#slot j18
/wr/bin/rtu_stat add 02:34:56:78:9B:0b 11 0 0	#slot j28
/wr/bin/rtu_stat add 02:34:56:78:9B:0c 12 0 0	#slot j23
/wr/bin/rtu_stat add 02:34:56:78:9B:0d 13 0 0	#slot j17
/wr/bin/rtu_stat add 02:34:56:78:9B:0e 14 0 0	#slot j11
/wr/bin/rtu_stat add 02:34:56:78:9B:0f 15 0 0	
/wr/bin/rtu_stat add 02:34:56:78:9B:10 16 0 0	
/wr/bin/rtu_stat add 02:34:56:78:9B:11 17 0 0	
/wr/bin/rtu_stat add 02:34:56:78:9B:12 18 0 0

###/sbin/ifconfig wr1 192.168.10.3
###sleep 1
###/sbin/ifconfig wr0 192.168.10.2

###for i in {0..18}
###do
###	echo "Setting mtu for wr$i"
###	/sbin/ifconfig wr$i mtu 9000
###done
sleep 1
killall wrsw_rtud
sleep 1
/wr/bin/wrsw_rtud -t 7200 &




sleep 2
ping -c 5 192.168.10.1
sleep 2
ping -c 5 192.168.14.1
