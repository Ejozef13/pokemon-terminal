# Fish owns all drawing. The background timer only sends USR1 notifications.
function _pokemon_prompt_stop
    set -g _pokemon_active 0
    if set -q _pokemon_cache; and test -d "$_pokemon_cache"
        "$_pokemon_python" "$_pokemon_base/prompt.py" stop "$_pokemon_cache" 2>/dev/null
    end
end

function _pokemon_prompt_preexec --on-event fish_preexec
    _pokemon_prompt_stop
end

function _pokemon_prompt_exit --on-event fish_exit
    _pokemon_prompt_stop
end

function _pokemon_prompt_resize --on-signal WINCH
    # Saved header coordinates are no longer valid after a resize.
    _pokemon_prompt_stop
end

function _pokemon_prompt_tick --on-signal USR1
    if not set -q _pokemon_active; or test "$_pokemon_active" != 1
        return
    end
    # Freeze before multiline/long input could scroll the fixed header.
    set -l buffer_length (commandline | string length)
    if test (count (commandline)) -gt 1; or test "$buffer_length[1]" -ge "$COLUMNS"
        _pokemon_prompt_stop
        return
    end
    set -l frame
    if not read -l frame < "$_pokemon_cache/index"
        _pokemon_prompt_stop
        return
    end
    if test "$frame" = -1
        _pokemon_prompt_stop
        return
    end
    if string match -qr '^[0-9]+$' -- "$frame"
        # Signal handlers run in Fish's main thread, serialized with editing.
        # Restore the exact cursor position without changing the command buffer.
        read -z -l frame_data < "$_pokemon_cache/$frame.ansi"
        printf '\e7%s\e8' "$frame_data"
    end
end

function _pokemon_prompt_first --on-event fish_prompt
    if set -q _pokemon_started
        # A new prompt (including an empty Enter) may scroll the header.
        _pokemon_prompt_stop
        return
    end
    set -g _pokemon_started 1
    set -l prepared ("$_pokemon_python" "$_pokemon_base/prompt.py" prepare "$_pokemon_base" "$COLUMNS" "$LINES")
    if test (count $prepared) != 2
        return
    end
    set -g _pokemon_cache "$prepared[1]"
    set -l rows "$prepared[2]"
    # Run after config.fish and fish_greeting, removing any previous startup art.
    read -z -l initial_frame < "$_pokemon_cache/0.ansi"
    printf '\e[H\e[2J%s\e[%s;1H' "$initial_frame" (math "$rows + 2")
    set -g _pokemon_active 1
    # Ctrl-L freezes first, then performs the normal reader clear operation.
    bind --preset \cl '_pokemon_prompt_stop; commandline -f clear-screen'
    bind --preset \cc '_pokemon_prompt_stop; commandline -f cancel-commandline'
    "$_pokemon_python" "$_pokemon_base/prompt.py" start "$_pokemon_cache" "$fish_pid"
end
