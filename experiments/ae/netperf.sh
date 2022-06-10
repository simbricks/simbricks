#!/bin/bash

# Runs only combinations listed in Table 1 by default

if [ -z "$1" ] || [ $1 == "selected" ];
then
    echo "Run only Table 1 combinations"
    python3 run.py pyexps/ae/t1_netperf.py --filter nf-qemu-sw-ib --force --verbose
    python3 run.py pyexps/ae/t1_netperf.py --filter nf-gt-ns3-ib --force --verbose
    python3 run.py pyexps/ae/t1_netperf.py --filter nf-qemu-sw-cv --force --verbose
    python3 run.py pyexps/ae/t1_netperf.py --filter nf-qt-sw-cv --force --verbose

elif [ $1 == "all" ];
then
    echo "Run all the combinations in Appendix 4, Table 3"
    python3 run.py pyexps/ae/t1_netperf.py --filter=* --force --verbose 

fi


# Process the results and prints
python3 pyexps/ae/data_netperf.py out/ > ae/netperf.data

