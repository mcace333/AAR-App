#!/bin/bash
# SM2 Tool Launcher

export DISPLAY=:0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# If not running inside a terminal, relaunch in konsole
if [ ! -t 1 ]; then
    konsole --noclose -e bash "$(realpath "$0")" "$@"
    exit
fi

cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "Erstelle virtuelles Environment..."
    python3 -m venv --system-site-packages .venv
    echo "Installiere Abhängigkeiten..."
    .venv/bin/pip install -r requirements.txt
fi

.venv/bin/python3 sm2_tool.py "$@"
