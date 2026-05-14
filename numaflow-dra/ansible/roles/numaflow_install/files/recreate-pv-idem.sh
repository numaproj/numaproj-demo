#!/bin/bash
#
# Synopsys
# ========
# ./recreate-pv-idem.sh pv_name
#
# Description
# ===========
# Create a new PV with the specified name. If the PV already exists in
# "Released" status, delete then re-create it. Otherwise, do nothing.
#
# Parameters
# ==========
# - pv_name: .metadata.name of a PV
#
# Exit code
# =========
# - 0: OK (no change)
# - 1: Changed
# - 2 or greater: Error
#
export LANG=C LC_ALL=C
# DO NOT set -Cueo pipefail to control exit code properly
set -x

# Return code
# ===========
# - 0: Success
# - 4: No such PV
# - Otherwise: Error
#
# See also: https://jqlang.org/manual/#invoking-jq (-e option)
#
get_pv_status() {
  local pv_name
  pv_name="$1"

  kubectl get -o json pv |
    jq --arg pv_name "${pv_name}" -M -e -r \
      '.items[]|select(.metadata.name==$pv_name)|.status.phase'
}

delete_pv() {
  local pv_name
  pv_name="$1"

  kubectl delete pv "${pv_name}" || return $?
  kubectl wait --for=delete "pv/${pv_name}"
}

create_pv() {
  local pv_name
  pv_name="$1"

  cat <<EOF | kubectl create -f - || return $?
apiVersion: v1
kind: PersistentVolume
metadata:
  name: ${pv_name}
spec:
  capacity:
    storage: 3Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/disks/${pv_name}
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
EOF

  kubectl wait --for=create "pv/${pv_name}"
}

main() {
  if [[ $# != 1 ]] ; then
    exit 2
  fi

  local pv_name
  pv_name="$1"

  local pv_status
  if pv_status="$(get_pv_status "${pv_name}")" ; then
    # There is a PV with the specified name
    case "${pv_status}" in
    Released)
      # Delete the released PV then re-create it
      delete_pv "${pv_name}" || exit 2
      create_pv "${pv_name}" || exit 2
      exit 1
      ;;
    *)
      # The PV cannot be deleted
      exit 0
      ;;
    esac
  elif [[ $? == 4 ]] ; then
    # There is no PV with the specified name; create it
    create_pv "${pv_name}" || exit 2
    exit 1
  else
    # Error
    exit 2
  fi
}

main "$@"

# Fallback
exit 2
