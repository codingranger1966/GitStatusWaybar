#!/bin/bash
# One-shot git status wrapper for Waybar

VENV_PATH="$HOME/Projects/GitStatusWaybar/venv"
SCRIPT_PATH="$HOME/.config/waybar/scripts/git-status-oneshot.py"

# Suppress all stderr
exec 2>/dev/null

if [ ! -d "$VENV_PATH" ]; then
    echo '{"text": "✗", "class": "error", "tooltip": "Virtual environment not found"}'
    exit 1
fi

if [ ! -f "$SCRIPT_PATH" ]; then
    echo '{"text": "✗", "class": "error", "tooltip": "Git status script not found"}'
    exit 1
fi

source "$VENV_PATH/bin/activate"
python "$SCRIPT_PATH"