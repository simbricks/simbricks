#!/bin/bash

# Runs simulation with varying PCI latency configuration
# It will generate raw simulation json file result in out/
python3 run.py pyexps/ae/f9_latency.py --filter pci-gt-ib-sw-* --force --verbose

# Process the results and prints
python3 pyexps/ae/data_pci_latency.py out/ > ae/pci_latency.data

