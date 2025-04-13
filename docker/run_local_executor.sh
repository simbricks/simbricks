#!/bin/bash

ip=$1
port=$2

if [[ "$ip" = "" ]] || [[ "$port" = "" ]]; then
    echo "Error: you need to specify both ip and port"
    echo "Usage: simbricks-executor-local IP PORT"
    exit 1
fi

pwd
ls
sudo chmod o+rw /dev/kvm
make convert-images-raw
exec simbricks-executor-local "$ip" "$port"