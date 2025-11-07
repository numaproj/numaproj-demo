#!/bin/bash
set -euxo pipefail
export LC_ALL=C

target_screen=0
target_output=VGA-1
target_width=1920
target_height=1080

main() {
    # Validate screen size
    local -a max_line
    max_line=($(xrandr --screen "${target_screen}" | grep 'Screen 0' | xargs -n1 echo | grep -A3 maximum | xargs echo))
    (( "${#max_line[@]}" == 4)) || exit 2
    local max_width max_height
    max_width="${max_line[1]}"
    max_height="${max_line[3]}"
    (( "${target_width}" <= "${max_width}")) || exit 2
    (( "${target_height}" <= "${max_height}")) || exit 2

    # Validate output name
    local -a output_line
    output_line=($(xrandr --screen "${target_screen}" | grep -A1 'Screen 0' | tail -n1))
    local output_name
    output_name="${output_line[0]}"
    [[ "${target_output}" == "${output_name}" ]] || exit 2

    # Get modeline
    local -a modeline
    modeline=($(cvt "${target_width}" "${target_height}" | grep ^Modeline | sed 's/^Modeline\s*//'))
    local mode_name
    mode_name="$(echo "${modeline[0]}" | sed -r 's/^"|"$//g')"
    modeline[0]="${mode_name}"

    if xrandr | grep -F "${mode_name}" >&2 ; then
        :
    else
        xrandr --newmode "${modeline[@]}"
        xrandr --addmode "${target_output}" "${mode_name}"
    fi

    xrandr -s "${mode_name}"
}

main "$@"
exit 0
