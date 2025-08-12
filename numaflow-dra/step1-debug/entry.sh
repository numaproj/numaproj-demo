#!/bin/sh
set -eux

if [ "$SCRIPT" = "source" ]; then
    python source.py

elif [ "$SCRIPT" = "filter-resize" ]; then
    python filter-resize.py
elif [ "$SCRIPT" = "fr-async" ]; then
    python filter-resize-async.py
elif [ "$SCRIPT" = "fr-stream" ]; then
    python filter-resize-stream.py

elif [ "$SCRIPT" = "sink-debug" ]; then
    python sink-debug.py
else
    echo "Error: Unknown SCRIPT '$APP_MODE'"
    exit 1
fi
