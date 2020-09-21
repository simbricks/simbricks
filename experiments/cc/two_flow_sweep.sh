#!/bin/bash

DUR=30
# K is DCTCP threshold in the unit of cells (208 bytes for BCMXXXXX)
K_START=0
K_END=32
K_INTERVAL=32

MTU=1500

set -x

for ((K=$K_START; K<=$K_END; K+=$K_INTERVAL))
do
    ssh honey1.kaist.ac.kr -p 2222 ~/change_k.sh $K > /dev/null
    EXP=$MTU-$K
    sleep 1
    ssh honey2.kaist.ac.kr -p 2222 sudo taskset 0x02 iperf -c 10.9.9.11 -i 1 -Z dctcp -w 400K -t $DUR > $EXP-1.txt &
    ssh honey3.kaist.ac.kr -p 2222 sudo taskset 0x02 iperf -c 10.9.9.11 -i 1 -Z dctcp -w 400K -t $DUR > $EXP-2.txt 
    wait
    cat $EXP-*.txt
    sleep 3
done

