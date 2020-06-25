#!/bin/bash

source common-functions.sh

for exp in QemuBm QemuVerilator GemBm GemVerilator
do
    case $exp in
        QemuBm) dn=qemu-ns3-vr ;;
        QemuVerilator) dn=qemu-ns3-vr-verilator ;;
        GemBm) dn=gem5-timing-corundum-bm-ns3-vr-nocp ;;
        GemVerilator) dn=gem5-timing-corundum-verilator-ns3-vr-nocp ;;
        *) echo "bad experiment $exp" 1>&2 ; exit 1 ;;
    esac

    avg_lat="`nopaxos_avglatencies $dn | average`"
    min_lat="`nopaxos_avglatencies $dn | min`"
    max_lat="`nopaxos_avglatencies $dn | max`"

    avg_dur="`exp_durations $dn | average`"
    min_dur="`exp_durations $dn | min`"
    max_dur="`exp_durations $dn | max`"

    echo "\\newcommand{\\DataVR${exp}AvgLat}{$avg_lat}"
    echo "\\newcommand{\\DataVR${exp}MinLat}{$min_lat}"
    echo "\\newcommand{\\DataVR${exp}MaxLat}{$max_lat}"

    echo "\\newcommand{\\DataVR${exp}AvgDur}{$avg_dur}"
    echo "\\newcommand{\\DataVR${exp}MinDur}{$min_dur}"
    echo "\\newcommand{\\DataVR${exp}MaxDur}{$max_dur}"
done
