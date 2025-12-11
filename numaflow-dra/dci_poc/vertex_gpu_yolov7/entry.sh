#!/bin/sh
set -eux

if [ "$SCRIPT" = "inf-stream-yolov7" ]; then
    python inference_stream_yolov7.py

else
    echo "Error: Unknown SCRIPT '$SCRIPT'"
    exit 1
fi
