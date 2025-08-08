#!/bin/sh
set -eux

if [ "$SCRIPT" = "inf-stream" ]; then
    python inference-stream.py

else
    echo "Error: Unknown SCRIPT '$APP_MODE'"
    exit 1
fi
