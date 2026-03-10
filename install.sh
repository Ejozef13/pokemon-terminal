#!/usr/bin/env bash

set -e

CONFIG_DIR="$HOME/.config/pokemon-terminal"
ART_DIR="$CONFIG_DIR/terminal-art"
BASHRC_LINE='[ -f ~/.config/pokemon-terminal/bashrc-pokemon.sh ] && source ~/.config/pokemon-terminal/bashrc-pokemon.sh'

mkdir -p "$ART_DIR"

cp terminal-art/venusaur.txt "$ART_DIR/venusaur.txt"
cp bashrc-pokemon.sh "$CONFIG_DIR/bashrc-pokemon.sh"

if ! command -v fastfetch >/dev/null 2>&1 && ! command -v neofetch >/dev/null 2>&1; then
    echo "Installing neofetch..."
    sudo apt update
    sudo apt install -y neofetch
fi

if ! grep -Fxq "$BASHRC_LINE" "$HOME/.bashrc"; then
    echo "" >> "$HOME/.bashrc"
    echo "# Pokemon terminal startup" >> "$HOME/.bashrc"
    echo "$BASHRC_LINE" >> "$HOME/.bashrc"
fi

echo "Done. Restart terminal or run: source ~/.bashrc"
