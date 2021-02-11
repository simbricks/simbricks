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
