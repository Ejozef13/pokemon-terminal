# Sourced by interactive Bash; isolate variables from the caller.
_pokemon_terminal() {
    [[ $- == *i* && ${TERM:-dumb} != dumb ]] || return 0
    local art="${XDG_CONFIG_HOME:-$HOME/.config}/pokemon-terminal/terminal-art/venusaur.txt"
    [[ -r $art ]] || return 0
    local -a left=() right=()
    local line plain info='' width=0 columns=${COLUMNS:-80} i count
    local ansi=$'\e''\[[0-?]*[ -/]*[@-~]'
    mapfile -t left < "$art"
    if command -v fastfetch >/dev/null 2>&1; then
        info=$(fastfetch --logo none 2>/dev/null) || info=''
    elif command -v neofetch >/dev/null 2>&1; then
        info=$(neofetch --stdout 2>/dev/null) || info=''
    fi
    [[ -z $info ]] || mapfile -t right <<< "$info"
    for line in "${left[@]}"; do
        plain=$line
        while [[ $plain =~ $ansi ]]; do plain=${plain/"${BASH_REMATCH[0]}"/}; done
        (("${#plain}" <= width)) || width=${#plain}
    done
    if ((columns < width + 42)) || (("${#right[@]}" == 0)); then
        printf '%s\n' "${left[@]}"
        (("${#right[@]}" == 0)) || printf '\n%s\n' "$info"
    else
        count=${#left[@]}
        (("${#right[@]}" <= count)) || count=${#right[@]}
        for ((i=0; i<count; i++)); do
            line=${left[i]-}
            plain=$line
            while [[ $plain =~ $ansi ]]; do plain=${plain/"${BASH_REMATCH[0]}"/}; done
            printf '%s%*s%s\n' "$line" "$((width - ${#plain} + 2))" '' "${right[i]-}"
        done
    fi
    printf '\e[0m\e[?25h\n'
    return 0
}
_pokemon_terminal
unset -f _pokemon_terminal
