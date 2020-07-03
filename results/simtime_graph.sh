#!/bin/bash

source common-functions.sh

  for n in 0 10 30 50 80 100 150
  do
    dn=gem5-timing-corundum-verilator-pair-udp-${n}m

    avg_tput="`iperf_server_tputs $dn | average`"
    avg_dur="`exp_durations $dn | average`"

    echo "$avg_tput $avg_dur"
  done
