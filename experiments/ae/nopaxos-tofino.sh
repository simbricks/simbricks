#!/bin/bash
SB_BASE="$(readlink -f $(dirname ${BASH_SOURCE[0]})/../..)"

start_tofino () {
    $SDE/run_tofino_model.sh -p nopaxos --log-dir /tmp --json-logs-enable -q &
    sleep 5
    $SDE/run_switchd.sh -p nopaxos &
    sleep 20
    $SDE/run_bfshell.sh -b /simbricks/sims/net/tofino/p4/nopaxos_setup.py
}

cleanup () {
    killall -9 tofino-model
    killall -9 run_tofino_model.sh
    killall -9 bf_switchd
    killall -9 run_switchd.sh
    rm -f /tmp/model.ldjson
}

run_experiment () {
    start_tofino
    python3 run.py pyexps/ae/nopaxos.py --filter nopaxos-qt-ib-tofino-$1 --force --verbose
    cleanup
}

# Run nopaxos with Tofino sequencer in Figure 10
for i in 1 2 3 4 5 6 8 10
do
    run_experiment $i
done

# Parse nopaxos result
python3 pyexps/ae/data_nopaxos.py out/ > ae/nopaxos.data
