#!/bin/bash

dir=../corundum_bm

cpp_lines="`cloc --csv $dir/{corundum_bm.cc,corundum_bm.h} | tail -n1 | sed 's/.*,//'`"

echo "\\newcommand{\\DataLocCorundumBM}{$cpp_lines}"
