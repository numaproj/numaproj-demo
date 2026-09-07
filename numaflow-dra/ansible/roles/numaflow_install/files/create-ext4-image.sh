#!/bin/bash
#
# create-ext4-image.sh -- Create such an image file for loopback mount
#
# Synopsys
# ========
# ./create-ext4-image.sh size_mib path_image
#
# Options
# =======
# None
#
# Parameters
# ==========
# size_mib
#   Size of the image file being created, in MiB
# path_image
#   Path to the image file being created
#
# Exit code
# =========
# 0 -- OK
#   There is already an expected image file so nothing need to be created.
# 1 -- Changed
#   A new image file created successfully.
# 2 -- Failed
#   An existing "entry" is something unexpected (is not a file, is a file
#   but has an unexpected size, or is not ext4 type); or failed to create
#   a new image file.
#
export LANG=C LC_ALL=C
set -xuo pipefail

declare path_image
cleanup_on_error() {
  if [ -f "${path_image:-}" ] ; then
    rm -f "${path_image}"
  fi
}

main() {
  # There should be exactly 2 arguments
  if [ $# -ne 2 ] ; then
    exit 2
  fi

  local -i size_mib
  size_mib="${1:-}"
  path_image="${2:-}"

  # Every argument should not be empty
  if [ -z "${size_mib:-}" ] || [ -z "${path_image:-}" ] ; then
    exit 2
  # size_mib should be a positive number
  elif [ "${size_mib}" -le 0 ] ; then
    exit 2
  # Check if there is already something at path_image
  elif [ -e "${path_image}" ] ; then
    # Fail if that thing is NOT a regular file
    [ -f "${path_image}" ] || exit 2

    # If it is a regular file, check its (1) size and (2) type
    # (1) Check if that file size is expected
    local -i stat_size_bytes
    stat_size_bytes="$(stat -c %s "${path_image}")" || exit 2
    (( size_mib*1024*1024 == stat_size_bytes )) || exit 2

    # (2) Check if that file type is ext4
    file -s "${path_image}" | grep ext4 >&2 || exit 2

    exit 0
  fi

  # Register an at-exit function for cleanup on error
  trap cleanup_on_error EXIT
  # Allocate a new empty image
  fallocate -l "${size_mib}M" "${path_image}" || exit 2
  # Make a new ext4 filesystem on the image
  mkfs.ext4 "${path_image}" >&2 || exit 2
  # Done! Unregister the at-exit function
  trap - EXIT

  exit 1
}

main "$@"

# Fallback to error
exit 2
