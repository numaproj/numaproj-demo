#!/bin/sh
set -eux

if [ "$SCRIPT" = "inf-stream-yolov4" ]; then
    python inference_stream_yolov4.py

else
    echo "Error: Unknown SCRIPT '$SCRIPT'"
    exit 1
fi
