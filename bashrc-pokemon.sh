ART="$HOME/.config/pokemon-terminal/terminal-art/venusaur.txt"

if [[ -f "$ART" ]] && [[ $- == *i* ]]; then
    LEFT="$(cat "$ART")"

    if command -v fastfetch >/dev/null 2>&1; then
        RIGHT="$(fastfetch --logo none 2>/dev/null)"
    elif command -v neofetch >/dev/null 2>&1; then
        RIGHT="$(neofetch --stdout 2>/dev/null)"
    else
        RIGHT=""
    fi

    LFILE=$(mktemp)
    RFILE=$(mktemp)

    printf "%s\n" "$LEFT" > "$LFILE"
    printf "%s\n" "$RIGHT" > "$RFILE"

    LINES_L=$(wc -l < "$LFILE")
    LINES_R=$(wc -l < "$RFILE")

    if [ "$LINES_R" -lt "$LINES_L" ]; then
        for _ in $(seq $LINES_R $LINES_L); do echo >> "$RFILE"; done
    fi

    paste -d ' ' "$LFILE" "$RFILE"

    rm -f "$LFILE" "$RFILE"
    printf "\n"
fi
