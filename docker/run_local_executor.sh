#!/bin/bash

eval "$(micromamba shell hook --shell bash)"
micromamba activate base

ip=$1
port=$2
proxy_host_ip=$3
convert=$4

if [[ "$ip" = "" ]] || [[ "$port" = "" ]] || [[ "$proxy_host_ip" = "" ]]; then
    echo "Error: you need to specify both ip and port"
    echo "Usage: simbricks-executor-local IP PORT PROXY_HOST_IP"
    exit 1
fi

sudo chmod o+rw /dev/kvm

# Try to convert images in global input dir to raw format
if [ -d "$GLOBAL_INPUT_DIR" ] && [ "$convert" != "False" ] && [ "$convert" != "false" ]; then
    for subdir in "$GLOBAL_INPUT_DIR"/images/*/; do
        image_name="$(basename "$subdir")"
        qemu-img convert -f qcow2 -O raw -S 4k \
            "$GLOBAL_INPUT_DIR"/images/"$image_name"/"$image_name" \
            "$GLOBAL_INPUT_DIR"/images/"$image_name"/"$image_name".raw
    done
fi

exec simbricks-executor-local "$ip" "$port" "$proxy_host_ip"
