#!/bin/bash
#
# patch-prometheus-retention.sh -- updates retension
#
# Synopsys
# ========
# ./patch-prometheus-retention.sh [-n namespace] [-p prometheus] [retention]
#
# Description
# ===========
# Patches the given prometheus custom resource (default "k8s") in the given
# namespace (default "monitoring") to make it have the given retention time.
#
# Parametes
# =========
# retention
#   A new retention time such as "24h" or "30d".
#
# Options
# =======
# -n namespace
#   A namespace name.
# -p prometheus
#   A name of prometheus custom resource.
#
# Exit code
# =========
# 0 -- OK (already patched)
# 1 -- Patched
# 2 -- Error
#
export LANG=C LC_ALL=C
set -Cxuo pipefail

declare tmpfile
on_exit() {
  if [ -f "${tmpfile:-}" ] ; then
    rm -f "${tmpfile}"
  fi
}

main() {
  trap on_exit EXIT

  local namespace=monitoring prometheus=k8s
  local optchr
  while getopts n:p: optchr ; do
    case "${optchr}" in
      n)
        namespace="${OPTARG}"
        ;;
      p)
        prometheus="${OPTARG}"
        ;;
      \?)
        exit 2
        ;;
    esac
  done
  shift $((OPTIND-1))

  # There should be exactly one argument
  if [ $# -ne 1 ] ; then
    exit 2
  fi
  local retention
  retention="${1}"

  tmpfile="$(mktemp)" || exit 2
  kubectl get prometheus "${prometheus}" -n "${namespace}" -o json \
    >|"${tmpfile}" || exit 2

  if
    jq -e --arg retention "${retention}" '.spec.retention==$retention' \
      "${tmpfile}" >&2
  then
    # OK (already patched)
    exit 0
  fi

  # Patching. Note that "op" is "add" that works like update-or-insert.
  local patch
  patch="$(printf '[{"op":"add","path":"/spec/retention","value":"%s"}]' \
    "${retention}")" || exit 2
  kubectl patch prometheus "${prometheus}" -n "${namespace}" --type=json -p "${patch}" || exit 2
  # Patched
  exit 1
}

main "$@"
# Fallback to error
exit 2
