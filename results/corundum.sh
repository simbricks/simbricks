#!/bin/bash

source common-functions.sh

for exp in QemuBm QemuVerilator GemVerilator
do
  for n in 1 8
  do
    case $n in
      1) word=One ;;
      8) word=Eight ;;
      *) echo "bad n $n" 1>&2 ; exit 1 ;;
    esac
    case $exp in
        QemuBm) dn=qemu-corundum-bm-switched-$n ;;
        QemuVerilator) dn=qemu-corundum-verilator-switched-$n ;;
        GemVerilator) dn=gem5-timing-corundum-verilator-switched-$n-nocp ;;
        *) echo "bad experiment $exp" 1>&2 ; exit 1 ;;
    esac


    avg_tput="`iperf_tputs $dn | average`"
    avg_dur="`exp_durations $dn | average`"

    echo "\\newcommand{\\DataCorundum${exp}${word}AvgTput}{$avg_tput}"
    echo "\\newcommand{\\DataCorundum${exp}${word}AvgDur}{$avg_dur}"

  done
done
