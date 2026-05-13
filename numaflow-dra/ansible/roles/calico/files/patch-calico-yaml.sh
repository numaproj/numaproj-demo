#!/bin/bash
#
# Synopsys
# ========
# ./patch-calico-yaml.sh calico_yaml
#
# Description
# ===========
# Patch Calico Manifest in order to append the following snippet
# to the env of the calico-node DaemonSet:
#
#   - name: IP_AUTODETECTION_METHOD
#     value: kubernetes-internal-ip
#
# Parameters
# ==========
# - calico_yaml: Calico Manifest YAML file
#
# Exit code
# =========
# - 0: OK (no change)
# - 1: Changed
# - 2 or greater: Error
#
export LANG=C LC_ALL=C
set -xo pipefail

find_next_nth_begin() {
  local regex calico_yaml
  local -i nth_begin nth_end
  regex="$1"
  nth_begin="$2"
  nth_end="$3"
  calico_yaml="$4"

  local line
  grep -n -x -e "${regex}" "${calico_yaml}" |
    awk -F: -v "b=${nth_begin}" -v "e=${nth_end}" '{if(b<$1 && $1<e){print $1}}' |
    head -n 1
}

main() {
  local calico_yaml="$1"

  local line
  local -i nth_begin nth_end

  line="$(grep -n -e '^# This manifest installs the calico-node container' "${calico_yaml}" | cut -d: -f1)" || exit 2
  nth_begin="${line}"

  line="$(wc -l "${calico_yaml}" | cut -d' ' -f1)"
  nth_end=$((line+1))

  line="$(grep -n -x -e '---' "${calico_yaml}" | awk -F: -v "b=${nth_begin}" '{if(b<$1){print $1}}' | head -n 1)" || exit 2
  if [[ -n "${line:-}" ]] ; then
    nth_end="${line}"
  fi

  nth_begin="$(find_next_nth_begin 'kind: DaemonSet' "${nth_begin}" "${nth_end}" "${calico_yaml}")" || exit 2
  nth_begin="$(find_next_nth_begin 'spec:' "${nth_begin}" "${nth_end}" "${calico_yaml}")" || exit 2
  nth_begin="$(find_next_nth_begin '  template:' "${nth_begin}" "${nth_end}" "${calico_yaml}")" || exit 2
  nth_begin="$(find_next_nth_begin '    spec:' "${nth_begin}" "${nth_end}" "${calico_yaml}")" || exit 2
  nth_begin="$(find_next_nth_begin '      containers:' "${nth_begin}" "${nth_end}" "${calico_yaml}")" || exit 2
  nth_begin="$(find_next_nth_begin '        - name: calico-node' "${nth_begin}" "${nth_end}" "${calico_yaml}")" || exit 2
  nth_begin="$(find_next_nth_begin '          env:' "${nth_begin}" "${nth_end}" "${calico_yaml}")" || exit 2

  line="$(grep -n -e '^          [^ ]' "${calico_yaml}" | awk -F: -v "b=${nth_begin}" '{if(b<$1){print $1}}' | head -n 1)" || exit 2
  if [[ -n "${line:-}" ]] ; then
    nth_end=$((line))
  fi

  tail -n "+$((nth_begin+1))" "${calico_yaml}" |
  head -n 2

  # Assume that the target item is at [0]
  if
    tail -n "+$((nth_begin+1))" "${calico_yaml}" |
      head -n 1 |
      grep -x -e '            - name: IP_AUTODETECTION_METHOD' \
      && \
    tail -n "+$((nth_begin+2))" "${calico_yaml}" |
      head -n 1 |
      grep -x -e '              value: kubernetes-internal-ip'
  then
    # Found
    exit 0
  else
    sed -i -e "${nth_begin}a\\
            - name: IP_AUTODETECTION_METHOD\\
              value: kubernetes-internal-ip" "${calico_yaml}" || exit 2
    # Changed
    exit 1
  fi
}

main "$@"

# Fallback
exit 2
