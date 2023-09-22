#!/bin/bash

set -x -e

strings=(
    "octo"
    "puffy"
)

for fish in "${strings[@]}"; do
    make image FISH=${fish} DOCKER_PUSH=${DOCKER_PUSH} IMAGE_NAMESPACE=quay.io/numaio
    make image FISH=${fish} ERROR_RATE=60 DOCKER_PUSH=${DOCKER_PUSH} IMAGE_NAMESPACE=quay.io/numaio
    make image FISH=${fish} LATENCY=2 DOCKER_PUSH=${DOCKER_PUSH} IMAGE_NAMESPACE=quay.io/numaio
done
