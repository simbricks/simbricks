#!/bin/bash
set -x

# Requires two arguments: number of runs and results directory with json

run_num=$1
dir=$2

# Parse the json file into experiment's out_dir
for i in $(seq 1 $run_num);
do
    mkdir -p $dir/dt-gt-ib-sw/${i}
    python3 pyexps/log_parser.py $dir/dt-gt-ib-sw-$i.json

    cat $dir/dt-gt-ib-sw/${i}/host.client.0 | awk '/system.pc.simbricks_0:/ {print $1}' > $dir/dt-gt-ib-sw/${i}/host_trim
done


diff $dir/dt-gt-ib-sw/1/host_trim $dir/dt-gt-ib-sw/2/host_trim > $dir/dt-gt-ib-sw/host_trim12.diff
