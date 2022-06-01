#!/bin/bash
SB_BASE="$(readlink -f $(dirname ${BASH_SOURCE[0]})/../..)"
NS3_BASE="$SB_BASE/sims/external/ns-3"

# Runs ns-3 data points in Figure 1
# It will generate simulation result files in simbricks/sims/external/ns-3
./pyexps/ae/ns3-dctcp.sh `nproc`
python3 pyexps/ae/data_ns3_dctcp.py $NS3_BASE > ae/dctcp_ns3.data

# Runs Simbricks data points in Figure 1
# It will generate simulation results in out/
python3 run.py pyexps/ae/f1_dctcp.py --filter gt-ib-* --force --verbose --parallel

# Process the results and prints
python3 pyexps/ae/data_sb_dctcp.py out/ > ae/dctcp_simbricks.data

