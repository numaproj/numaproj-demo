#!/bin/bash
set -Ceuxo pipefail
export LC_ALL=C

wait_until() {
    local -i timeout=0

    OPTIND=1
    local optchr
    while getopts t: optchr ; do
        case "${optchr}" in
        t)
            timeout="$((OPTARG))"
            ;;
        esac
    done
    shift "$((OPTIND-1))"

    while (( "${timeout}" > 0 )) ; do
        if "$@" >&2 ; then
            return 0
        else
            local -i rc="$?"
            if (( "${rc}" != 1 )) ; then
                return "${rc}"
            fi
        fi
        sleep 1
        ((timeout--))
    done

    # The last chance
    "$@" >&2
}

x11vnc_started() {
    local greeter=no

    OPTIND=1
    local optchr
    while getopts g optchr ; do
        case "$optchr" in
        g)
            greeter=yes
            ;;
        esac
    done
    shift "$((OPTIND-1))"

    local -i pid port
    local outfile
    pid="$1"
    port="$2"
    outfile="$3"

    if [[ "${greeter}" == yes ]] ; then
        # Have a child (x11vnc) of given $pid (sudo) spawned?
        if pid="$(pgrep -P "${pid}")" ; then
            # Already spawned
            :
        else
            # Not spawned yet
            return "$?"
        fi
    fi

    # Have $pid (x11vnc) gone?
    if ! ps --pid "${pid}" -o user,pid,args >&2 ; then
        # Already gone
        return 2
    fi
    # Still remained

    # Does $outfile contain a line "PORT=$port" ?
    grep -x -F "PORT=${port}" "${outfile}" >&2
}

print_help_then_exit() {
    set +x

    echo "Usage:"
    echo "  $0 [-g|-u] PORT DISPLAY"
    echo "  $0 [-0|-1|-2]"
    echo "  $0 -h"
    echo "Arguments:"
    echo "  PORT"
    echo "    A port not used yet to which a new x11vnc server will listen,"
    echo "    such as '5900' or '5901'."
    echo "  DISPLAY"
    echo "    An existing X display to which a new x11vnc server will connect,"
    echo "    such as ':0' or ':1.0'"
    echo "Options:"
    echo "  -g"
    echo "    Greeter mode; uses the gdm's Xauthority instead of yours. This is"
    echo "    probably nessessary for you to have x11vnc connect to the display"
    echo "    ':0'. You should have sudo privilege for this option."
    echo "  -u"
    echo "    User mode (default); uses your Xauthority."
    echo "  -0"
    echo "    Implies '-g', and uses '5900' for PORT and ':0' for DISPLAY."
    echo "  -1"
    echo "    Implies '-u', and uses '5901' for PORT and ':1.0' for DISPLAY."
    echo "  -2"
    echo "    Implies '-u', and uses '5902' for PORT and ':1.1' for DISPLAY."
    echo "  -h"
    echo "    Shows this help then exits with 0."

    set -x
    exit "$1"
}

main() {
    if [[ "${USER}" == root || "${USER}" == gdm ]] ; then
        echo 'You should be neither root nor gdm' >&2
        exit 2
    fi

    local user="${USER}" preset=no display
    local -i port
    local -a sudo

    local optchr
    while getopts :ghu012 optchr ; do
        case "$optchr" in
        g)
            user=gdm
            sudo=(sudo -u gdm --)
            ;;
        h)
            print_help_then_exit 0
            ;;
        u)
            user="${USER}"
            sudo=()
            ;;
        0)
            preset=yes
            user=gdm
            sudo=(sudo -u gdm --)
            port=5900
            display=:0
            ;;
        1)
            preset=yes
            user="${USER}"
            sudo=()
            port=5901
            display=:1.0
            ;;
        2)
            preset=yes
            user="${USER}"
            sudo=()
            port=5902
            display=:1.1
            ;;
        *)
            exit 2
            ;;
        esac
    done
    shift "$((OPTIND-1))"

    if [[ "${preset}" == yes ]] ; then
        (( $# == 0 )) || print_help_then_exit 2
    else
        (( $# == 2 )) || print_help_then_exit 2
        [[ -n "${1:-}" ]] || print_help_then_exit 2
        [[ -n "${2:-}" ]] || print_help_then_exit 2
        port="$1"
        display="$2"
    fi

    local uid auth
    uid="$(id -u "${user}")"
    auth="/run/user/${uid}/gdm/Xauthority"

    local suffix
    suffix="$(echo "${display}" | sed 's/[^-_a-zA-Z0-9]/-/g')"

    local outfile
    outfile="$(mktemp)"
    trap "rm -f '${outfile}'" 0 1 2 3 15

    local dt logfile
    dt="$(date +%Y-%m-%d-%H-%M-%S)"
    logfile="x11vnc-${suffix}-${dt}.log"
    touch "${logfile}"

    # Start x11vnc server at $port, connecting to $display
    "${sudo[@]}" x11vnc -forever -nevershared -nopw -localhost -auth "${auth}" \
        -rfbport "${port}" -display "${display}" >|"${outfile}" 2>|"${logfile}" &
    local -i pid="$!"
    disown "${pid}"

    local -a opt_g
    if (( "${#sudo[@]}" != 0 )) ; then
        opt_g=(-g)
    fi

    # Wait until x11vnc server is ready
    wait_until -t 5 -- x11vnc_started "${opt_g[@]}" "${pid}" "${port}" "${outfile}"
}

main "$@"
exit 0
