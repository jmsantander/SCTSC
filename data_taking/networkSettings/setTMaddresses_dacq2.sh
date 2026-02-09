###/sbin/ifconfig
/wr/bin/rtu_stat

# associates the FEE number to the last two digets of its MAC address
declare -A FEE
FEE+=( [1]="16" [2]="4c" [3]="62" [4]="bf" [5]="99" [6]="69" [7]="0e" [8]="c2" [9]="52" [100]="51" [101]="59" [106]="ca" [107]="40" [108]="b4" [110]="65" [111]="7f" [112]="24" [113]="15" [114]="9d" [116]="f7" [118]="2d" [119]="82" [121]="e5" [123]="6d" [124]="72" [125]="7a" [126]="bc" [128]="83" )

# associates slot in the backplane [jslot] to the white rabbit position
declare -A slot0
slot0+=( [12]=15 [13]=10 [14]=8 [15]=4 [20]=9 [21]=3 [5]=16 [6]=14 [27]=2 [7]=11 [8]=7 [9]=5 )

/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[125]} ${slot0[12]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[126]} ${slot0[13]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[106]} ${slot0[14]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[121]} ${slot0[20]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[9]} ${slot0[15]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[8]} ${slot0[21]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[4]} ${slot0[5]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[5]} ${slot0[6]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[7]} ${slot0[27]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[1]} ${slot0[7]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[3]} ${slot0[8]} 0 0
/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[2]} ${slot0[9]} 0 0

# for testing only
#/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[3]} ${slot0[15]} 0 0
#/wr/bin/rtu_stat add 08:00:56:00:03:${FEE[1]} ${slot0[5]} 0 0





#assign MAC addr for wr
/wr/bin/rtu_stat add A6:76:1D:39:80:F4 8 0 0	#port 14
/wr/bin/rtu_stat add A6:76:1D:39:80:F6 10 0 0	#port 13
/wr/bin/rtu_stat add A6:76:1D:39:80:FB 15 0 0	#port 12
/wr/bin/rtu_stat add A6:76:1D:39:80:F5 9 0 0	#port 20
/wr/bin/rtu_stat add A6:76:1D:39:80:F0 4 0 0	#port 15
/wr/bin/rtu_stat add A6:76:1D:39:80:EF 3 0 0	#port 21
/wr/bin/rtu_stat add A6:76:1D:39:80:FC 16 0 0	#port 5
/wr/bin/rtu_stat add A6:76:1D:39:80:FA 14 0 0	#port 6
/wr/bin/rtu_stat add A6:76:1D:39:80:EE 2 0 0	#port 27
/wr/bin/rtu_stat add A6:76:1D:39:80:F1 5 0 0	#slot j9
/wr/bin/rtu_stat add A6:76:1D:39:80:F3 7 0 0    #slot j8
/wr/bin/rtu_stat add A6:76:1D:39:80:F7 11 0 0   #slot j7
###/sbin/ifconfig wr1 192.168.12.3
###/sbin/ifconfig wr1 192.168.11.2
/sbin/ifconfig wr1 192.168.16.2

###for i in {0..18}
###do
###	echo "Setting mtu for wr$i"
###	/sbin/ifconfig wr$i mtu 9000
###done


sleep 1
killall wrsw_rtud
sleep 1
/wr/bin/wrsw_rtud -t 7200 &


sleep 1



ping -c 5 192.168.12.1
sleep 1
ping -c 5 192.168.16.1
