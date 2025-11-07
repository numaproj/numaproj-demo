#!/bin/bash
set -euxo pipefail
export LC_ALL=C

screen -d -m -- kubectl port-forward -n monitoring service/grafana 3000:3000
