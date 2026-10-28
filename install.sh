#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/pokemon-terminal"
ART_DIR="$CONFIG_DIR/terminal-art"
BASHRC_LINE='[ -f "${XDG_CONFIG_HOME:-$HOME/.config}/pokemon-terminal/bashrc-pokemon.sh" ] && source "${XDG_CONFIG_HOME:-$HOME/.config}/pokemon-terminal/bashrc-pokemon.sh"'
LEGACY_LINE='[ -f ~/.config/pokemon-terminal/bashrc-pokemon.sh ] && source ~/.config/pokemon-terminal/bashrc-pokemon.sh'
if (($# > 1)) || [[ ${1:-} == --help ]]; then
    printf 'Usage: %s [image.png|image.jpg|image.gif|art.txt]\n' "$0"
    (($# <= 1)) && exit 0
    exit 2
fi
mkdir -p "$ART_DIR"
TEMP=$(mktemp "$ART_DIR/.venusaur.XXXXXX")
trap 'rm -f -- "$TEMP"' EXIT
if (($#)); then
    [[ -r $1 ]] || { printf 'Cannot read: %s\n' "$1" >&2; exit 1; }
    case $1 in
        *.txt) cp -- "$1" "$TEMP" ;;
        *) python3 "$ROOT/image-to-art.py" "$1" --width "${POKEMON_WIDTH:-48}" > "$TEMP" ;;
    esac
elif [[ -f $ART_DIR/venusaur.txt ]]; then
    cp -- "$ART_DIR/venusaur.txt" "$TEMP"
else
    cp -- "$ROOT/terminal-art/venusaur.txt" "$TEMP"
fi
mv -- "$TEMP" "$ART_DIR/venusaur.txt"
cp -- "$ROOT/bashrc-pokemon.sh" "$CONFIG_DIR/bashrc-pokemon.sh"
touch "$HOME/.bashrc"
python3 - "$HOME/.bashrc" "$LEGACY_LINE" "$BASHRC_LINE" <<'PY'
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
old, new = sys.argv[2:]
lines = path.read_text().splitlines(keepends=True)
lines = [line for line in lines if line.rstrip('\r\n') not in (old, new)]
text = ''.join(lines)
if text and not text.endswith('\n'):
    text += '\n'
path.write_text(text + new + '\n')
PY
printf 'Installed. Open a new Bash terminal to display Venusaur.\n'
if ! command -v fastfetch >/dev/null 2>&1 && ! command -v neofetch >/dev/null 2>&1; then
    printf 'Optional: install fastfetch or neofetch to show system information.\n'
fi
