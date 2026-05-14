#!/bin/bash
export LC_ALL=C
set -Cxueo pipefail

VIDEO_FILE=../../video-streaming-server/mediamtx/poc_movie_test.mp4
VIDEO_URL='https://www.pexels.com/download/video/6896028/?fps=30.0&h=2160&w=3840'

declare bin
bin="$(dirname "${BASH_SOURCE[0]}")"

declare tmpdir
on_exit() {
    if [[ -d "${tmpdir:-}" ]] ; then
        rm -rf "${tmpdir}"
    fi
}

main() {
    # Remove tmpdir on non-signal exit
    trap on_exit EXIT
    tmpdir="$(mktemp -d -p /tmp)"

    # Fast exit if the transcoded video file already exists
    pushd "${bin}" >&2
    if [[ -f "${VIDEO_FILE}" ]] ; then
        exit 0
    fi

    local tmpfile1 tmpfile2
    tmpfile1="$(mktemp -p "${tmpdir}")"
    # ffmpeg requires a file extension for output file
    tmpfile2="$(mktemp -p "${tmpdir}" tmp.XXXXXXXXXX.mp4)"

    # Download a video and transcode it to 15fps
    curl -s -S -L -o "${tmpfile1}" "${VIDEO_URL}"
    ffmpeg -y -i "${tmpfile1}" -r 15 "${tmpfile2}"
    mv "${tmpfile2}" "${VIDEO_FILE}"

    popd >&2
}

main "$@"
exit 0
