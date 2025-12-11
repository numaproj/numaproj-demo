#!/bin/bash
set -euxo pipefail
export LC_ALL=C

main() {
    ps -C x11vnc -C kubectl -C ffmpeg -C mediamtx -C screen -o ppid,pid,args ||:
    kubectl get pod
}

main "$@"
exit 0
