#!/bin/bash
#
# Synopsys
# ========
# ./create-or-update-dashboard.sh json_file
#
# Description
# ===========
# Create a dashboard for demo in the local Grafana (http://localhost:3000).
# If it already exists, update it instaed.
#
# Parameters
# ==========
# json_file
#   A dashboard definition file exported from Grafana.
#
# Exit code
# =========
# 0: OK (no need to create nor update)
# 1: Changed (created or updated)
# 2 or greater: Error
#
export LANG=C LC_ALL=C
set -xo pipefail

API=http://admin:admin@localhost:3000/apis/dashboard.grafana.app/v1beta1/namespaces/default/dashboards

declare tmpdir

setup_tmpdir() {
  tmpdir="$(command mktemp -d)"
}

on_exit() {
  if [ -d "${tmpdir:-}" ] ; then
    rm -rf "${tmpdir}"
  fi
}

mktemp() {
  command mktemp -p "${tmpdir}" "$@"
}

generate_dashboard() {
  local json_file
  json_file="$1"

  jq '{metadata:{name:.uid},spec:.}' "${json_file}"
}

jq_dump() {
  jq -M -c . "$@"
}

jq_query_raw() {
  jq -M -e -r "$@"
}

curl_json_from_stdin() {
    curl --no-progress-meter --fail-with-body \
      -H 'Content-Type: application/json' -d @- "$@"
}

create_dashboard() {
  local json_file
  json_file="$1"

  generate_dashboard "${json_file}" | curl_json_from_stdin -X POST "${API}"
}

get_dashboard() {
  local uid
  uid="$1"

  curl -s -S "${API}/${uid}"
}

update_dashboard() {
  local uid json_file
  uid="$1"
  json_file="$2"

  generate_dashboard "${json_file}" | curl_json_from_stdin -X PUT "${API}/${uid}"
}

main() {
  setup_tmpdir
  trap on_exit EXIT

  local json_file
  json_file="$1"
  if [ ! -f "${json_file}" ] ; then
    exit 2
  fi

  local uid
  uid="$(jq_query_raw .uid "${json_file}")" || exit 2

  local -i rc

  # Try to create a new dashboard.
  # See https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/dashboard/#create-dashboard
  local tmpfile_create
  tmpfile_create="$(mktemp)" || exit 2
  rc=0
  create_dashboard "${json_file}" >|"${tmpfile_create}" || rc=$?
  jq_dump "${tmpfile_create}" >&2 || exit 2

  if [ $rc -eq 0 ] ; then
    # Created
    exit 1
  else
    # Check if we failed with 409 Conflict.
    local create_code
    create_code="$(jq_query_raw .code "${tmpfile_create}")" || exit 2
    if [ "${create_code}" -ne 409 ] ; then
      # Error other than 409
      exit 2
    fi
  fi
  # Now we failed with 409 Conflict

  # Get the current dashboard and compare it to our one.
  # See https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/dashboard/#get-dashboard
  local tmpfile_get
  tmpfile_get="$(mktemp)" || exit 2
  get_dashboard "${uid}" >|"${tmpfile_get}" || exit 2
  if
    diff -u \
      <(jq .spec "${tmpfile_get}") \
      <(jq 'del(.id,.uid,.version)' ${json_file}) >&2
  then
    # Inputs are the same; no need to update
    exit 0
  else
    rc=$?
    if [ $rc -ne 1 ] ; then
      # Error occurred when running diff
      exit 2
    fi
  fi
  # Now our dashboard is different from the current one

  # Update the dashboard.
  # See https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/dashboard/#update-dashboard
  local tmpfile_update
  tmpfile_update="$(mktemp)" || exit 2
  rc=0
  update_dashboard "${uid}" "${json_file}" >|"${tmpfile_update}" || rc=$?
  jq_dump "${tmpfile_update}" >&2 || exit 2

  if [ $rc -eq 0 ] ; then
    # Updated
    exit 1
  else
    # Error
    exit 2
  fi
}

main "$@"

# Fallback
exit 2
