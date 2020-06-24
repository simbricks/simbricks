#!/bin/bash

dir=../corundum

vsrcs=""
for f in `sed 's/.*://' $dir/obj_dir/Vinterface__ver.d`
do
    if [[ "$f" == *.v ]]
    then
        vsrcs="$vsrcs $dir/$f"
    fi
done

verilog_lines="`cloc --csv $vsrcs | tail -n1 | sed 's/.*,//'`"
cpp_lines="`cloc --csv $dir/*.cpp $dir/*.h | tail -n1 | sed 's/.*,//'`"

echo "\\newcommand{\\DataLocCorundumVVerilog}{$verilog_lines}"
echo "\\newcommand{\\DataLocCorundumVCPP}{$cpp_lines}"
