#!/bin/bash
set -euxo pipefail
export LC_ALL=C

declare bin
bin="$(realpath "$(dirname "${BASH_SOURCE[0]}")")"

declare log
log="${bin}/video-receive-server.log"

main() {
    if pgrep -f '/python video-receive-server.py' ; then
        exit 1
    else
        pushd "${bin}/../video-receive-server" >/dev/null 2>&1
        # Let poetry (kicked by make start-receiver) not freeze
        # See https://github.com/python-poetry/poetry/issues/1917#issuecomment-1235998997
        export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
        screen -d -m -L -Logfile "${log}" -- make start-receiver
        popd >/dev/null 2>&1
    fi
}

main "$@"
exit 0
