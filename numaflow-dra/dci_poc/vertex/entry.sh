#!/bin/sh
set -eux

if [ "$SCRIPT" = "source" ]; then
    python source.py
elif [ "$SCRIPT" = "fr-stream" ]; then
    python filter_resize_stream.py
elif [ "$SCRIPT" = "sink" ]; then
    python sink.py
else
    echo "Error: Unknown SCRIPT '$SCRIPT'"
    exit 1
fi
