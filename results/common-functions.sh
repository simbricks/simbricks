#!/bin/bash

average() {
    awk '{s+=$1}END{print (NR?s/NR:"NaN")}'
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
