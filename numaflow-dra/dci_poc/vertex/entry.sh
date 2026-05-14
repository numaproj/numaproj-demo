#!/bin/sh
set -eux

if [ "$SCRIPT" = "source" ]; then
    exec python source.py
elif [ "$SCRIPT" = "reduce" ]; then
    exec python reduce.py
elif [ "$SCRIPT" = "sink" ]; then
    exec python sink.py
else
    echo "Error: Unknown SCRIPT '$SCRIPT'"
    exit 1
fi
