#! /bin/bash

set -x
RUN=5

itr=0
while [ $itr -lt $RUN ]
do
    nswitch=2
    while [ $nswitch -lt 6 ]
    do
        bash -x pyexps/pktgen.sh 2 $nswitch &> out/pktgen/chain/s${nswitch}-h2-${itr}.out
        ((nswitch++))
    done
    ((itr++))
done
