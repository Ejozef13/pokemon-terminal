"""One-time migration of previous Pokemon startup calls; not installed at runtime."""
import re
import shutil
import time

TAG = '# pokemon-terminal animated: disabled original: '
SUPPRESSED = 'true # pokemon-terminal animated: suppressed startup'
BASH_START = '# >>> pokemon-terminal animated >>>'
BASH_END = '# <<< pokemon-terminal animated <<<'
FISH_NAME = 'pokemon-terminal-animated.fish'


def strip_block(text):
    lines, inside = [], False
    for line in text.splitlines(keepends=True):
        if line.rstrip() == BASH_START:
            inside = True
        elif line.rstrip() == BASH_END:
            inside = False
        elif not inside:
            lines.append(line)
    if inside:
        raise ValueError('Incomplete animated startup block; restore its backup first')
    return ''.join(lines)


def migrate(text, disable=False):
    text = strip_block(text)
    result = []
    for line in text.splitlines(keepends=True):
        if disable:
            # Disabling animation must never resurrect retired static artwork.
            result.append(line)
        elif line.startswith(TAG) or line.lstrip().startswith('#'):
            result.append(line)
        elif ('bashrc-pokemon.sh' in line or
              re.match(r'^\s*(?:command\s+)?(?:fastfetch|neofetch|venusaur|pokemon-terminal|pokemon_terminal)(?:\s|$)', line) or
              (re.match(r'^\s*(?:command\s+)?(?:cat|chafa|viu|jp2a|source|\.)(?:\s|$)', line)
               and re.search(r'venusaur|pokemon-terminal|terminal-art', line, re.I))):
            # Keep an if/function body syntactically valid when its only
            # command was the old startup invocation.
            if line.rstrip().endswith('\\'):
                result.append(line)  # Multi-line custom commands need manual review.
            else:
                result.append(TAG + line.rstrip('\n') + '\n' + SUPPRESSED + '\n')
        else:
            result.append(line)
    return ''.join(result)


def write_config(path, text, backups):
    if path.is_file() and path.read_text() == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = backups / (path.name + '.' + str(time.time_ns()))
        backups.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
        print(f'Backup: {backup}')
    path.write_text(text)

