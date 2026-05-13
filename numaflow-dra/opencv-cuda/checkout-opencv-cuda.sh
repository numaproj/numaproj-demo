#!/bin/bash
export LC_ALL=C
set -xueo pipefail

main() {
    # Get the path to the directory that contains this script
    local bin
    bin="$(realpath "$(dirname "${BASH_SOURCE[0]}")")"

    # Inside /opencv-cuda -----------------------------------------------------
    cd "${bin}"

    # Load environment variables
    . ../repo.env

    # You cannot use `git clone -b` option if you want to checkout a commit ID
    if [ ! -d opencv ] ; then
        git clone "${OPENCV_GIT_URL}" opencv
    fi
    pushd opencv
    git checkout "${OPENCV_GIT_VERSION}"
    popd

    if [ ! -d opencv_contrib ] ; then
        git clone "${OPENCV_CONTRIB_GIT_URL}" opencv_contrib
    fi
    pushd opencv_contrib
    git checkout "${OPENCV_CONTRIB_GIT_VERSION}"
    popd
}

main "$@"
