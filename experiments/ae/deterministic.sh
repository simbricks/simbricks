#!/bin/bash
set -x
# Runs the same simulation by default five times.
if [ -z "$1" ]
then
    echo "set run num to five"
    run_num=5
else
    echo "set run num to $1"
    run_num=$1
fi
python3 run.py pyexps/ae/determ.py --filter dt-gt-ib-sw --force --verbose --runs=$1
START=1

# Parse the json file into experiment's out_dir
for i in $(seq 1 $run_num);
do
    mkdir -p out/dt-gt-ib-sw/${i}
    python3 pyexps/log_parser.py out/dt-gt-ib-sw-$i.json
    
    cat out/dt-gt-ib-sw/${i}/host.client.0 | awk '/system.pc.simbricks_0:/ {print $1}' > out/dt-gt-ib-sw/${i}/host_trim
done


diff out/dt-gt-ib-sw/1/host_trim out/dt-gt-ib-sw/2/host_trim > out/dt-gt-ib-sw/host_trim12.diff