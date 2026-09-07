#!/bin/sh
set -eux

if [ "$SCRIPT" = "source" ]; then
    exec python source.py
elif [ "$SCRIPT" = "brightness" ]; then
    exec python brightness.py
elif [ "$SCRIPT" = "motion" ]; then
    exec python motion.py
elif [ "$SCRIPT" = "reduce" ]; then
    exec python reduce.py
elif [ "$SCRIPT" = "sink" ]; then
    exec python sink.py
else
    echo "Error: Unknown SCRIPT '$SCRIPT'"
    exit 1
fi
