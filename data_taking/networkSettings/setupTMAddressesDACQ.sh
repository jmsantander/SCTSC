#!/bin/bash

BOARD=$1

echo $BOARD


#Wait for boards to come up:






sshpass -p "" scp -o StrictHostKeyChecking=no authorized_keys root@172.17.2.4:.ssh/
sshpass -p "" scp -o StrictHostKeyChecking=no setTMaddresses_dacq1.sh root@172.17.2.4: 
sshpass -p "" ssh -o StrictHostKeyChecking=no root@172.17.2.4 "/bin/bash /root/setTMaddresses_dacq1.sh"



sshpass -p "" scp -o StrictHostKeyChecking=no authorized_keys root@172.17.2.5:.ssh/
sshpass -p "" scp -o StrictHostKeyChecking=no setTMaddresses_dacq2.sh root@172.17.2.5: 
sshpass -p "" ssh -o StrictHostKeyChecking=no root@172.17.2.5 "/bin/bash /root/setTMaddresses_dacq2.sh"
