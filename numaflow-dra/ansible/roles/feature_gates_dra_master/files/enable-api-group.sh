#!/bin/bash
#
# RETURN CODE
# ===========
# 0: Update not required
# 1: Updated successfully
# Otherwise: Error
#
export LANG=C LC_ALL=C
set -xo pipefail

main() {
  local dir=/etc/kubernetes/manifests

  local opthcr
  while getopts d: optchr ; do
    case "${optchr}" in
    d)
      dir="${OPTARG}"
      ;;
    esac
  done
  shift $((OPTIND-1))

  if [[ ! -d "${dir}" ]] ; then
    exit 2
  fi

  cd "${dir}"

  if [[ ! -f kube-apiserver.yaml ]] ; then
    exit 2
  fi

  local command_line
  command_line="$(grep -n -e "- kube-apiserver" kube-apiserver.yaml | head -n 1)"
  if [[ $? -ne 0 ]] ; then
    exit 2
  fi

  local -i nth_line
  nth_line="$(echo "$command_line" | awk -F: '{print $1}')"
  if [[ $? -ne 0 ]] ; then
    exit 2
  fi

  local head_spaces
  head_spaces="$(echo "$command_line" | awk -F: '{print $2}' | awk -F- '{print $1}')"
  if [[ $? -ne 0 ]] ; then
    exit 2
  fi

  local line
  while (( ++nth_line )) ; do
    line="$(tail "+${nth_line}" kube-apiserver.yaml | head -n 1 | grep "^${head_spaces}- ")"
    if [[ -z "${line:-}" ]] ; then
      break
    fi
    if [[ "${line}" == "${head_spaces}- --runtime-config=resource.k8s.io/v1beta1=true" ]] ; then
      exit 0
    elif echo "${line}" | grep "^${head_spaces}- --runtime-config=" >/dev/null ; then
      # Cannot handle with this script
      exit 3
    fi
  done

  sed -i "$((nth_line-1)) a \\${head_spaces}- --runtime-config=resource.k8s.io/v1beta1=true" kube-apiserver.yaml
  if [[ $? -ne 0 ]] ; then
    exit 2
  fi
  exit 1
}

main "$@"
exit 2
