#!/bin/bash

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
    python3 pyexps/log_parser.py out/dt-gt-ib-sw-$i.json
done
