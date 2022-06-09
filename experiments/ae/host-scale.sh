#!/bin/bash

# Runs simulation with varying PCI latency configuration
# It will generate raw simulation json file result in out/
python3 run.py pyexps/ae/f7_sacle.py --filter host-* --force --verbose

# Process the results and prints
python3 pyexps/ae/data_host_scale.py out/ > ae/host_scale.data

