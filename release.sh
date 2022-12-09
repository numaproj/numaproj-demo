#!/bin/bash

set -x -e

strings=(
    "octo"
    "puffy"
)

for fish in "${strings[@]}"; do
    make image FISH=${fish} DOCKER_PUSH=${DOCKER_PUSH} IMAGE_NAMESPACE=${IMAGE_NAMESPACE}
    make image FISH=${fish} ERROR_RATE=15 DOCKER_PUSH=${DOCKER_PUSH} IMAGE_NAMESPACE=${IMAGE_NAMESPACE}
    make image FISH=${fish} LATENCY=2 DOCKER_PUSH=${DOCKER_PUSH} IMAGE_NAMESPACE=${IMAGE_NAMESPACE}
done
