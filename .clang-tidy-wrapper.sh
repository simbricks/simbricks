#!/bin/bash
IGNORES="sims/nic/i40e_bm/base/*.h /usr/share/verilator/include/*.h"



# This is an ugly hack to exclude individual headers, until clang-tidy has a
# proper mechanism for this (e.g. https://reviews.llvm.org/D34654)
lf="["
for f in $IGNORES
do
    lf="$lf{\"name\":\"$f\",\"lines\":[[9999999,9999999]]},"
done
lf="$lf{\"name\":\".c\"},{\"name\":\".cc\"},{\"name\":\".h\"}]"

tidy=$1
shift

files=
for f in `cat .lint-files`
do
    [ ! -f $f ] && continue
    [ ${f: -2} == ".h" ] && continue
    files="$files $f"
done
$tidy --quiet --format-style=file --header-filter='.*' --line-filter="$lf" \
    $files -- "$@"
