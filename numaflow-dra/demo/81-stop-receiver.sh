#!/bin/bash
set -euxo pipefail
export LC_ALL=C

PROC=make
TIMEOUT=${TIMEOUT:-10}  # Maximum wait time in seconds (can be overridden by environment variable)

main() {
  # Try to stop the process, continue even if it's not running
  pkill -x "$PROC" || true

  echo "Waiting for $PROC to stop (timeout: ${TIMEOUT}s)..."

  # Wait until the process disappears or timeout occurs
  for ((i=0; i<TIMEOUT; i++)); do
    if ! pgrep -x "$PROC" >/dev/null 2>&1; then
      echo "$PROC stopped"
      return 0
    fi
    sleep 1
  done

  echo "Timeout: $PROC is still running after ${TIMEOUT}s" >&2
  return 1
}

main "$@"
