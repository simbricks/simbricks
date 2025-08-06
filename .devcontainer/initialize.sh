#!/bin/bash
set -e

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
cd "$SCRIPT_DIR/.."

git submodule update --init
cd sims/external/qemu
git submodule update --init
cd -
DOCKER_REGISTRY="" DOCKER_TAG="" make docker-images
