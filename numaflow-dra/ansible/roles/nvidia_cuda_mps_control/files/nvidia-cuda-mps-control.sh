#!/bin/bash
export LANG=C LC_ALL=C
set -Cueo pipefail

main() {
    if ! which -s nvidia-cuda-mps-control ; then
        exit 2
    fi

    if [[ -z "${1:-}" ]] ; then
        exit 2
    fi
    local subcommand
    subcommand="$1"
    shift 1

    # PCI_BUS_ID should be a literal capital string "PCI_BUS_ID"
    export CUDA_DEVICE_ORDER=PCI_BUS_ID
    # DO NOT set CUDA_VISIBLE_DEVICES to use all GPU devices
    export CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps
    export CUDA_MPS_LOG_DIRECTORY=/tmp/nvidia-mps

    case "$subcommand" in
    start)
        exec nvidia-cuda-mps-control -d
        ;;
    stop)
        echo quit | nvidia-cuda-mps-control
        ;;
    *)
        exit 2
        ;;
    esac
}

main "$@"
