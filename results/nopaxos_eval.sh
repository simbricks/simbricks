#!/bin/bash

source common-functions.sh

for exp in QemuBm QemuVerilator GemBm GemVerilator
do
    case $exp in
        QemuBm) dn=qemu-ns3-nopaxos ;;
        QemuVerilator) dn=qemu-ns3-nopaxos-verilator ;;
        GemBm) dn=gem5-timing-corundum-bm-ns3-nopaxos-nocp ;;
        GemVerilator) dn=gem5-timing-corundum-verilator-ns3-nopaxos-nocp ;;
        *) echo "bad experiment $exp" 1>&2 ; exit 1 ;;
    esac

    avg_lat="`nopaxos_avglatencies $dn | average`"
    min_lat="`nopaxos_avglatencies $dn | min`"
    max_lat="`nopaxos_avglatencies $dn | max`"

    avg_dur="`exp_durations $dn | average`"
    min_dur="`exp_durations $dn | min`"
    max_dur="`exp_durations $dn | max`"

    echo "\\newcommand{\\DataNopaxos${exp}AvgLat}{$avg_lat}"
    echo "\\newcommand{\\DataNopaxos${exp}MinLat}{$min_lat}"
    echo "\\newcommand{\\DataNopaxos${exp}MaxLat}{$max_lat}"

    echo "\\newcommand{\\DataNopaxos${exp}AvgDur}{$avg_dur}"
    echo "\\newcommand{\\DataNopaxos${exp}MinDur}{$min_dur}"
    echo "\\newcommand{\\DataNopaxos${exp}MaxDur}{$max_dur}"
done
