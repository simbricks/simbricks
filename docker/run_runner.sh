#!/bin/bash

namespace=$1
runner_id=$2

if [[ "$namespace" = "" ]] || [[ "$runner_id" = "" ]]; then
    echo "Error: you need to specify both namespace and runner_id"
    echo "Usage: simbricks-runner NAMESPACE RUNNER_ID"
    exit 1
fi

make convert-images-raw
NAMESPACE="$namespace" RUNNER_ID="$runner_id" exec simbricks-runner