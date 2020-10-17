#!/bin/bash
# Execute this in a folder with outputs.
# It only uses the total average throughput as output.

DUR=30
echo MTU K Throughput
grep 0.0-$DUR *.txt | sed 's/:/ /g' | sed 's/-/ /g' | sort -h -k2 | awk '{print $1, $2, $11}'
