#!/bin/bash
SB_BASE="$(readlink -f $(dirname ${BASH_SOURCE[0]})/../..)"

# Run nopaxos with endhost sequencer in Figure 10
echo "Start running nopaxos with endhost sequencer data points"
python3 run.py pyexps/ae/nopaxos.py --filter nopaxos-qt-ib-ehseq-* --force --verbose

# Run nopaxos with switch sequencer in Figure 10
echo "Start running nopaxos with switch sequencer data points"
python3 run.py pyexps/ae/nopaxos.py --filter nopaxos-qt-ib-swseq-* --force --verbose

# Parse nopaxos result
python3 pyexps/ae/data_nopaxos.py out/ > ae/nopaxos.data
