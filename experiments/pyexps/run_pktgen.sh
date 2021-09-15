#! /bin/bash

set -x
RUN=5

itr=0
while [ $itr -lt $RUN ]
do
    #nswitch=2
    #while [ $nswitch -lt 6 ]
    #do
        #bash -x pyexps/pktgen.sh 2 $nswitch &> out/pktgen/chain/s${nswitch}-h2-${itr}.out
    #    ((nswitch++))
    #done
    #bash -x pyexps/pktgen.sh 10 &> out/pktgen/star/s1-h10-${itr}.out
    bash -x pyexps/pktgen.sh 10 3 &> out/pktgen/star/s3-h10-${itr}.out
    ((itr++))
done
