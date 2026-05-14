#!/bin/bash
set -eux

if [ "$SCRIPT" = "fr-stream" ]; then
    # DO NOT set -u to source setup_vars_opencv4.sh
    set +u
    . ../../opencv-cuda/.local/bin/setup_vars_opencv4.sh
    set -u
    python filter_resize_stream.py
else
    echo "Error: Unknown SCRIPT '$SCRIPT'"
    exit 1
fi
