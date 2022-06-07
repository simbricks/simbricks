#!/bin/bash

cd ../pyexps/ae
# Run 2 hosts connected to one switch. Bit rate: 0 GB
echo "Run Run 2 hosts connected to one switch. Bit rate: 0 GB"
./pktgen.sh 2 0 run_switch >  ../../out/pktgen/2h1s0b.out 2>&1
python3 data_decmp.py ../../out/pktgen/2h1s0b.out 2>&1

# Run 2 hosts connected to one switch. Bit rate: 100 GB
echo "Run 2 hosts connected to one switch. Bit rate: 100 GB"
./pktgen.sh 2 100 run_switch >  ../../out/pktgen/2h1s100b.out 2>&1
python3 data_decmp.py ../../out/pktgen/2h1s100b.out 2>&1
# Run 32 hosts connected to one switch. Bit rate: 0 GB
echo "Run 32 hosts connected to one switch. Bit rate: 0 GB"
./pktgen.sh 32 0 run_switch >  ../../out/pktgen/32h1s0b.out 2>&1
python3 data_decmp.py ../../out/pktgen/32h1s0b.out 2>&1
# Run 32 hosts connected to one switch. Bit rate: 100 GB
echo "Run 32 hosts connected to one switch. Bit rate: 100 GB"
./pktgen.sh 32 100 run_switch >  ../../out/pktgen/32h1s100b.out 2>&1
python3 data_decmp.py ../../out/pktgen/32h1s100b.out 2>&1

# This part runs decomposed network configuration.
# 32 hosts are spread to 4 ToR switchs
# ToR switches are connected by 1 root switch

# Run Bit rate: 0 GB
echo "Decomposed Run Bit rate: 0 GB"
./pktgen.sh 32 0 4 run_switch_tor >  ../../out/pktgen/32hT0b.out 2>&1
python3 data_decmp.py ../../out/pktgen/32hT0b.out 2>&1
# Run Bit rate: 100 GB
echo "Decomposed Run Bit rate: 100 GB"
./pktgen.sh 32 100 4 run_switch_tor >  ../../out/pktgen/32hT100b.out 2>&1
python3 data_decmp.py ../../out/pktgen/32hT100b.out 2>&1