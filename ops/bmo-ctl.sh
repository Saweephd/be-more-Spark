#!/bin/bash
# bmo-ctl.sh: operate and test the BMO agent on the Raspberry Pi.
# Version 1.0.1
#
# Changelog
#   1.0.0  2026-11-12  First version: status, deploy, rollback, service control,
#                      logs, and the remote test commands (ask, say, listen,
#                      selftest).
#   1.0.1  2026-11-12  logs: read the journal by unit field so it works over SSH.
#
# Runs as the normal user; nothing here needs root.  No secrets live in this file.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
UNIT="bmo-agent.service"
UNIT_SRC="$REPO/ops/$UNIT"
UNIT_DST="$HOME/.config/systemd/user/$UNIT"
PREV_FILE="$REPO/.git/bmo-prev"
FETCH_URL="https://github.com/Saweephd/be-more-Spark.git"
PY="$REPO/venv/bin/python"
[ -x "$PY" ] || PY="python3"

# systemctl --user needs these when called over SSH without a desktop login.
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"

usage() {
    cat <<USAGE
Usage: bmo-ctl.sh <command> [arguments]

  status                 Branch, commit, service state, Spark reachability, temperature
  deploy <branch>        Fetch <branch> from GitHub, switch to it, restart the agent
  rollback               Return to the commit that was running before the last deploy
  install-service        Install and enable the boot service (user service, no root)
  start | stop | restart Control the agent service
  logs [lines]           Show the agent's recent log (default 60 lines)
  ask "<question>"       Send text through the same route as a spoken question
  say "<text>"           Speak text through Piper and the speaker
  listen [seconds] [--transcribe]
                         Record from the microphone, report levels and what the
                         end-of-speech detector decided; optionally transcribe
  selftest [--audio]     Run the checks; --audio also plays a short phrase
  help                   This text
USAGE
}

sysd() { systemctl --user "$@"; }
service_installed() { [ -f "$UNIT_DST" ]; }
service_active() { [ "$(sysd is-active "$UNIT" 2>/dev/null)" = "active" ]; }
runpy() { ( cd "$REPO" && PYTHONPATH="$REPO" "$PY" "$@" ); }

cmd_status() {
    cd "$REPO" || exit 1
    echo "branch:   $(git branch --show-current 2>/dev/null || true) $(git rev-parse --short HEAD)"
    echo "commit:   $(git log -1 --format='%s (%cr)')"
    local dirty; dirty="$(git status --short --untracked-files=no | wc -l)"
    echo "changes:  $dirty uncommitted tracked file(s)"
    if service_installed; then
        echo "service:  $(sysd is-active "$UNIT" 2>/dev/null) / $(sysd is-enabled "$UNIT" 2>/dev/null)"
    else
        echo "service:  not installed"
    fi
    echo "agent:    $(pgrep -f 'python3? .*agent_hailo.py' >/dev/null && echo running || echo not running)"
    local url; url="$(runpy -c 'from core.config import LLM_URL, LLM_MODEL; print(LLM_URL.rsplit("/api/",1)[0], LLM_MODEL)' 2>/dev/null | tail -1)"
    local base="${url% *}" model="${url#* }"
    if curl -s -m 5 "$base/api/tags" | grep -q "\"$model\""; then
        echo "spark:    reachable, $model installed"
    else
        echo "spark:    NOT reachable or $model missing ($base)"
    fi
    command -v vcgencmd >/dev/null && echo "temp:     $(vcgencmd measure_temp | cut -d= -f2), throttled $(vcgencmd get_throttled | cut -d= -f2)"
    return 0
}

cmd_install_service() {
    mkdir -p "$(dirname "$UNIT_DST")"
    cp "$UNIT_SRC" "$UNIT_DST"
    sysd daemon-reload
    sysd enable "$UNIT"
    echo "installed and enabled $UNIT (starts at the next boot; 'bmo-ctl.sh start' starts it now)"
}

restart_if_installed() {
    if service_installed; then
        # Pick up a changed unit file before restarting.
        if ! cmp -s "$UNIT_SRC" "$UNIT_DST"; then
            cp "$UNIT_SRC" "$UNIT_DST"; sysd daemon-reload; echo "service unit updated"
        fi
        sysd restart "$UNIT"; sleep 4
    fi
}

cmd_deploy() {
    local branch="${1:-}" force="${2:-}"
    [ -n "$branch" ] || { echo "deploy: which branch?"; exit 2; }
    cd "$REPO" || exit 1
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo "deploy refused: uncommitted changes to tracked files. Commit or stash them first."
        git status --short --untracked-files=no
        exit 1
    fi
    # Read from GitHub over HTTPS (public repository, no key needed); pushes keep using SSH.
    local push_url; push_url="$(git remote get-url --push origin)"
    git remote set-url origin "$FETCH_URL"
    git remote set-url --push origin "$push_url"
    git fetch --quiet origin "$branch" || { echo "deploy failed: could not fetch '$branch'"; exit 1; }
    local target; target="$(git rev-parse FETCH_HEAD)"
    if git show-ref --verify --quiet "refs/heads/$branch"; then
        local ahead; ahead="$(git rev-list --count "$target..refs/heads/$branch")"
        if [ "$ahead" != "0" ] && [ "$force" != "--force" ]; then
            echo "deploy refused: local '$branch' has $ahead commit(s) that are not on GitHub. Push them, or add --force."
            exit 1
        fi
    fi
    git rev-parse HEAD > "$PREV_FILE"
    git checkout --quiet -B "$branch" "$target" || { echo "deploy failed at checkout"; exit 1; }
    chmod +x "$REPO"/*.sh "$REPO"/ops/*.sh 2>/dev/null
    echo "deployed $branch at $(git rev-parse --short HEAD) (was $(cut -c1-7 "$PREV_FILE"))"
    restart_if_installed
    cmd_status
}

cmd_rollback() {
    cd "$REPO" || exit 1
    [ -f "$PREV_FILE" ] || { echo "rollback: no earlier deploy recorded"; exit 1; }
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo "rollback refused: uncommitted changes to tracked files."; exit 1
    fi
    local prev now; prev="$(cat "$PREV_FILE")"; now="$(git rev-parse HEAD)"
    git checkout --quiet --detach "$prev" || { echo "rollback failed at checkout"; exit 1; }
    echo "$now" > "$PREV_FILE"
    echo "rolled back to $(git rev-parse --short HEAD) (was $(echo "$now" | cut -c1-7))"
    restart_if_installed
    cmd_status
}

cmd_logs() {
    local n="${1:-60}"
    case "$n" in ''|*[!0-9]*) echo "logs: line count must be a number"; exit 2;; esac
    # Matching on the unit field works over SSH; "journalctl --user -u" returns nothing there.
    journalctl _SYSTEMD_USER_UNIT="$UNIT" -n "$n" --no-pager -o cat | grep -v "onnxruntime:Default, device_discovery"
}

cmd_listen() {
    local secs=5 transcribe=""
    for a in "$@"; do
        case "$a" in
            --transcribe) transcribe="--transcribe";;
            ''|*[!0-9]*) echo "listen: '$a' is not a number of seconds"; exit 2;;
            *) secs="$a";;
        esac
    done
    [ "$secs" -ge 1 ] && [ "$secs" -le 30 ] || { echo "listen: seconds must be 1 to 30"; exit 2; }
    # The microphone can only be opened by one program, so pause the agent.
    local was_active=0
    if service_active; then was_active=1; sysd stop "$UNIT"; sleep 1; fi
    runpy ops/bmo_listen.py "$secs" $transcribe; local rc=$?
    [ "$was_active" = 1 ] && sysd start "$UNIT"
    return $rc
}

cmd_selftest() {
    local audio=0; [ "${1:-}" = "--audio" ] && audio=1
    local fails=0
    check() { # name, command...
        local name="$1"; shift
        local out; out="$("$@" 2>&1)"; local rc=$?
        if [ $rc -eq 0 ]; then echo "PASS  $name  ${out##*$'\n'}"; else echo "FAIL  $name  ${out##*$'\n'}"; fails=$((fails+1)); fi
    }
    check "voice model file"   test -f "$REPO/piper/bmo.onnx"
    check "piper binary"       test -x "$REPO/piper/piper"
    check "whisper binary"     test -x "$REPO/whisper.cpp/build/bin/whisper-cli"
    check "whisper model"      test -f "$REPO/models/ggml-base.en.bin"
    check "wake word model"    test -f "$REPO/wakeword.onnx"
    check "microphone found"   sh -c "arecord -l | grep -q '^card'"
    check "speaker found"      sh -c "aplay -l | grep -q UACDemo"
    check "camera found"       sh -c "rpicam-hello --list-cameras 2>&1 | grep -q '^0 :'"
    check "hailo device"       test -e /dev/hailo0
    check "capture logic"      runpy -m unittest -q tests.test_audio_capture tests.test_edge_route
    check "ask: edge route"    runpy ops/bmo_ask.py --expect edge "what time is it"
    check "ask: spark route"   runpy ops/bmo_ask.py --expect spark "what is the capital of Peru"
    if [ $audio = 1 ]; then
        check "say (listen for it)" runpy ops/bmo_say.py "BMO self test. Can you hear me?"
    else
        echo "SKIP  say  (add --audio to play a phrase)"
    fi
    if service_installed; then
        check "service enabled" sh -c "[ \"\$(systemctl --user is-enabled $UNIT)\" = enabled ]"
    else
        echo "SKIP  service  (not installed)"
    fi
    echo "selftest: $fails failure(s)"
    [ $fails -eq 0 ]
}

main() {
    local cmd="${1:-help}"; [ $# -gt 0 ] && shift
    case "$cmd" in
        status)          cmd_status;;
        deploy)          cmd_deploy "$@";;
        rollback)        cmd_rollback;;
        install-service) cmd_install_service;;
        start|stop|restart)
            service_installed || { echo "$cmd: service not installed (run install-service)"; exit 1; }
            sysd "$cmd" "$UNIT"; sleep 3; echo "service: $(sysd is-active "$UNIT")";;
        logs)            cmd_logs "$@";;
        ask)             [ -n "${1:-}" ] || { echo 'ask: give a question in quotes'; exit 2; }; runpy ops/bmo_ask.py "$*";;
        say)             [ -n "${1:-}" ] || { echo 'say: give text in quotes'; exit 2; }; runpy ops/bmo_say.py "$*";;
        listen)          cmd_listen "$@";;
        selftest)        cmd_selftest "$@";;
        help|-h|--help)  usage;;
        *)               echo "unknown command: $cmd"; usage; exit 2;;
    esac
}
main "$@"
