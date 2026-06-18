#!/bin/bash

ip=$1
port=$2
proxy_host_ip=$3

if [[ "$ip" = "" ]] || [[ "$port" = "" ]] || [[ "$proxy_host_ip" = "" ]]; then
    echo "Error: you need to specify both ip and port"
    echo "Usage: simbricks-executor-local IP PORT PROXY_HOST_IP"
    exit 1
fi

sudo chmod o+rw /dev/kvm
make convert-images-raw
exec simbricks-executor-local "$ip" "$port" "$proxy_host_ip"