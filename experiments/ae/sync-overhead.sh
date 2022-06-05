#!/bin/bash

# Runs low event workload (sleep 10) with Simbricks
# It will generate raw simulation json file result in out/
python3 run.py pyexps/ae/no_traffic.py --filter noTraf-gt-ib-sw-sleep --force --verbose

# Runs high event workload (dd) with Simbricks
# It will generate raw simulation json file result in out/
python3 run.py pyexps/ae/no_traffic.py --filter noTraf-gt-ib-sw-busy --force --verbose

# Runs high event workload (dd) without Simbricks (standalone gem5)
# It will generate raw simulation json file result in out/
python3 run.py pyexps/ae/no-simbricks.py --filter no_simb-gt-sleep --force --verbose

# Runs high event workload (dd) without Simbricks (standalone gem5)
# It will generate raw simulation json file result in out/
python3 run.py pyexps/ae/no-simbricks.py --filter no_simb-gt-busy --force --verbose



# Process the results and prints
python3 pyexps/ae/data_sync_overhead.py out/ > ae/sync_overhead.data

