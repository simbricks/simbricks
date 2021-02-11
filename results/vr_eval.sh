#!/bin/bash
# Copyright 2021 Max Planck Institute for Software Systems, and
# National University of Singapore
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


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
