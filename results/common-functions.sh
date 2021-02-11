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


average() {
    awk '{s+=$1}END{printf ("%f", NR?s/NR:"NaN")}'
}

min() {
    awk 'BEGIN{x="NaN"}{x=(x=="NaN" || $1<x ? $1 : x)}END{print x}'
}

max() {
    awk 'BEGIN{x="NaN"}{x=(x=="NaN" || $1>x ? $1 : x)}END{print x}'
}

exp_durations() {
    for e in ../experiments/out/$1/*/
    do
        [ ! -f $e/endtime ] && continue
        start="$(date --date "`head -n 1 $e/starttime`" +%s)"
        end="$(date --date "`tail -n 1 $e/endtime`" +%s)"
        echo $(($end - $start))
    done
}

nopaxos_avglatencies() {
    for f in ../experiments/out/$1/*/qemu.c0.log \
        ../experiments/out/$1/*/gem5.c0.log
    do
        [ ! -f $f ] && continue

        grep "Average latency is" $f | sed 's/.*latency is \([0-9]*\) ns.*/\1/'
    done
}


iperf_tputs() {
    for d in ../experiments/out/$1/*/
    do
        [ ! -d $d ] && continue

        tputs="0"
        for f in $d/qemu.*.log $d/gem5.*.log
        do
            [ ! -f $f ] && continue
            [[ "`basename $f`" = *.a.log ]] && continue

            tp="`grep -e '^\[SUM\]' $f | sed \
                -e 's:.*Bytes\s*\([0-9\.]*\)\s*Kbits/sec:\1:' \
                -e 's:.*Bytes\s*\([0-9\.]*\)\s*Mbits/sec:\1 * 1000:' \
                -e 's:.*Bytes\s*\([0-9\.]*\)\s*Gbits/sec:\1 * 1000000:' | \
                sed -e s///`"
            [ "$tp" = "" ] && continue
            tputs="$tputs + `echo \"scale=2; $tp\" | bc`"
        done
        echo "scale=2; $tputs" | bc
    done
}

iperf_server_tputs() {
    for d in ../experiments/out/$1/*/
    do
        [ ! -d $d ] && continue

        tputs="0"
        for f in $d/qemu.a.log $d/gem5.a.log
        do
            [ ! -f $f ] && continue

            tp="`grep 'bits/sec' $f | sed \
                -e 's:.*Bytes\s*\([0-9\.]*\)\s*Kbits/sec.*:\1:' \
                -e 's:.*Bytes\s*\([0-9\.]*\)\s*Mbits/sec.*:\1 * 1000:' \
                -e 's:.*Bytes\s*\([0-9\.]*\)\s*Gbits/sec.*:\1 * 1000000:' | \
                sed -e s///`"
            [ "$tp" = "" ] && continue
            tputs="$tputs + `echo \"scale=2; $tp\" | bc`"
        done
        echo "scale=2; $tputs" | bc
    done
}
