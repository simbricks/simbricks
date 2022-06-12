#!/bin/bash
SB_BASE="$(readlink -f $(dirname ${BASH_SOURCE[0]})/../..)"
GEM5_BASE="$SB_BASE/sims/external/gem5"

# Runs dist-gem5 data points in Figure 9
# It will generate simulation result files in simbricks/sims/external/gem5/util/dist/test/run-*.out
echo "Start running dist-gem5 data points"
cd $GEM5_BASE/util/dist/test
./exp_run.sh
echo "Done running dist-gem5 data points"
# Process the results and prints
python3 pyexps/ae/data_dist.py $GEM5_BASE/util/dist/test/ > ae/dist_gem5.data

# Runs Simbricks data points in Figure 9
# It will generate simulation results in simbricks/sims/external/gem5/util/simbricks/run-*.out
echo "Start running simbricks data points"
cd $GEM5_BASE/util/simbricks
./exp_run.sh
echo "Done running simbricks data points"
# Process the results and prints
python3 pyexps/ae/data_dist.py $GEM5_BASE/util/simbricks/ > ae/dist_simbricks.data

