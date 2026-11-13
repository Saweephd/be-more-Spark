#!/bin/bash
# Starts the on-device BMO agent (face, wake word, speech in and out).
#
# Changelog
#   2026-11-12  Spark fork clean-up: no longer reinstalls Python packages on
#               every start (run ./install.sh or `pip install -r requirements.txt`
#               after changing requirements), and no longer starts hailo-ollama
#               by default, because chat goes to the DGX Spark and that server
#               can hold the Hailo device the vision model needs.
#               Set BMO_START_HAILO_OLLAMA=1 to get the old behaviour.
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

if [ -d "venv" ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

if [ "${BMO_START_HAILO_OLLAMA:-0}" = "1" ] && command -v hailo-ollama >/dev/null 2>&1; then
    if ! lsof -i :8000 >/dev/null 2>&1; then
        echo "Starting hailo-ollama server on port 8000..."
        OLLAMA_HOST=0.0.0.0:8000 nohup hailo-ollama serve > /tmp/ollama.log 2>&1 &
        sleep 5
    fi
fi

# The face is a Tk window; it needs the desktop's display.
export DISPLAY="${DISPLAY:-:0}"
export PYTHONUNBUFFERED=1

exec python3 agent_hailo.py "$@"
