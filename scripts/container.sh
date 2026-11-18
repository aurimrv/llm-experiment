#!/usr/bin/env bash
# Build (when needed) and run a command in the experiment container.
# The repository is mounted at /work. The host display is shared so
# `proteumim` can open its Tcl/Tk window.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

if ! docker info >/dev/null 2>&1; then
    echo "Docker is not available for this user." >&2
    exit 1
fi

build=0
if [ "${1:-}" = "--build" ]; then
    build=1
    shift
fi
if [ "$build" = 1 ] || ! docker image inspect llm-experiment >/dev/null 2>&1; then
    docker compose build
fi

if [ "${1:-}" = "proteumim" ]; then
    xhost +SI:localuser:"$(id -un)" >/dev/null 2>&1 || true
fi

tty_args=()
if [ -t 0 ] && [ -t 1 ]; then
    tty_args=(-it)
fi

exec docker compose run --rm \
    "${tty_args[@]}" \
    --user "$(id -u):$(id -g)" \
    experiment "$@"
