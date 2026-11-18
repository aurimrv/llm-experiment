#!/bin/bash
# Paths are set here so a bind-mounted /work is visible when the container starts.
export PROTEUMIMHOME="${PROTEUMIMHOME:-/work/tools/ProteumIM64/bin}"
export PATH="${PROTEUMIMHOME}:/opt/venv/bin:${PATH}"

if [ "$#" -eq 0 ]; then
    set -- bash
fi

if [ "$1" = "proteumim" ]; then
    shift
    if [ -z "${DISPLAY:-}" ]; then
        echo "DISPLAY is empty. Run this from a graphical session so the container can open the ProteumIM window." >&2
        exit 1
    fi
    exec wish -f /usr/local/lib/proteumim-wrap.tcl -- "$@"
fi

exec "$@"
