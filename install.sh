#!/usr/bin/env bash
# Portable entry point. Runtime lives outside the checkout.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PYTHON_BIN="${POKEMON_PYTHON:-python3}"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/pokemon-terminal"
VENV="$DATA_DIR/venv"

if [[ ${1:-} == --disable ]]; then
    exec "$PYTHON_BIN" "$ROOT/animated/install.py" --disable
fi
if [[ ${1:-} == --diagnose ]]; then
    if [[ ! -x "$VENV/bin/python" || ! -f "${XDG_CONFIG_HOME:-$HOME/.config}/pokemon-terminal/animated/dashboard.py" ]]; then
        printf 'Install first: bash install.sh /path/to/pokemon-venusaur.gif\n' >&2
        exit 1
    fi
    exec "$VENV/bin/python" "${XDG_CONFIG_HOME:-$HOME/.config}/pokemon-terminal/animated/dashboard.py" --diagnose
fi
if [[ ${1:-} == --help ]]; then
    printf 'Usage: bash install.sh [animated.gif] [--width 48 --gap 8 --fps 8 --duration 0]\n'
    printf '       bash install.sh --disable | --diagnose\n'
    printf 'Without a GIF path, reuse the bundled/installed GIF or ~/Downloads/pokemon-venusaur.gif.\n'
    exit 0
fi
command -v "$PYTHON_BIN" >/dev/null || { printf 'Python 3 is required.\n' >&2; exit 1; }
"$PYTHON_BIN" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' || {
    printf 'Python 3.10 or newer is required.\n' >&2
    exit 1
}
command -v fish >/dev/null || { printf 'Fish is required. Install it before running setup.\n' >&2; exit 1; }
if (($# == 0)) && [[ ! -f "$ROOT/assets/venusaur.gif" && ! -f "${XDG_CONFIG_HOME:-$HOME/.config}/pokemon-terminal/animated/venusaur.gif" && ! -f "$HOME/Downloads/pokemon-venusaur.gif" ]]; then
    printf 'Animated GIF missing. Run: bash install.sh /path/to/pokemon-venusaur.gif\n' >&2
    exit 2
fi
mkdir -p "$DATA_DIR"
"$PYTHON_BIN" -m venv "$VENV"
"$VENV/bin/python" -m pip install --disable-pip-version-check -r "$ROOT/requirements.txt"
exec "$VENV/bin/python" "$ROOT/animated/install.py" "$@"
