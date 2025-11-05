#!/bin/bash
set -euxo pipefail
export LC_ALL=C

declare bin
bin="$(realpath "$(dirname "${BASH_SOURCE[0]}")")"

main() {
    rm "${bin}"/*.log
}

main "$@"
exit 0
