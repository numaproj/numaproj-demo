#!/bin/bash
set -euxo pipefail
export LC_ALL=C

declare bin
bin="$(realpath "$(dirname "${BASH_SOURCE[0]}")")"

declare log
log="${bin}/mediamtx.log"

main() {
    if pgrep -x mediamtx ; then
        exit 1
    else
        pushd "${bin}/../video-streaming-server/mediamtx" >/dev/null 2>&1
        screen -d -m -L -Logfile "${log}" -- ./mediamtx
        pgrep -x mediamtx
        popd >/dev/null 2>&1
    fi
}

main "$@"
exit 0
