"""Streaming BMO's games to the TV without turning BMO's own screen upside down.

BMO's panel is mounted upside down and turned in software. The stream (Sunshine) grabs the picture
before that turn, so the old way was to undo the turn while streaming, which flipped BMO's own screen.
This adds a second, invisible screen called BMOTV. While a stream is running, games open there and the
TV shows that screen; BMO's panel keeps its face, the right way up.

The stream must always work, so the old way is kept as the fallback: if BMOTV cannot be made, the
stream grabs the real screen exactly as before.

  up       Make the BMOTV screen, point Sunshine at it and start Sunshine
  down     Stop Sunshine and remove the BMOTV screen
  status   What is running, and which way a stream would go
  begin    (run by Sunshine when a stream starts)
  end      (run by Sunshine when a stream stops)
"""
import json
import os
import re
import signal
import subprocess
import sys
import time

HOME = os.path.expanduser("~")
RC = os.path.join(HOME, ".config", "labwc", "rc.xml")
CONF = os.path.join(HOME, ".config", "sunshine", "sunshine.conf")
APPS = os.path.join(HOME, ".config", "sunshine", "apps.json")
FLAG = "/tmp/bmo_streaming"                 # games look for this and open on the second screen
PANEL, TV = "DSI-2", "BMOTV"
SIZE = "800x480"
UNIT = "bmo-sunshine"
ENV = dict(os.environ, WAYLAND_DISPLAY=os.environ.get("WAYLAND_DISPLAY", "wayland-0"),
           XDG_RUNTIME_DIR=os.environ.get("XDG_RUNTIME_DIR", "/run/user/%d" % os.getuid()))
BINDS = '''\t<keyboard>
\t\t<default/>
\t\t<keybind key="C-A-W-F9"><action name="VirtualOutputAdd" output_name="%s"/></keybind>
\t\t<keybind key="C-A-W-F10"><action name="VirtualOutputRemove" output_name="%s"/></keybind>
\t</keyboard>
''' % (TV, TV)


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, env=ENV, **kw)


def outputs():
    """Screen names in the order the desktop lists them."""
    return re.findall(r"^(\S+) \"", sh(["wlr-randr"]).stdout, re.M)


def ensure_binds():
    """The desktop can only add a screen from a key press, so give it two private key combinations."""
    text = open(RC).read()
    if "VirtualOutputAdd" in text:
        return False
    if not os.path.exists(RC + ".before-stream"):
        open(RC + ".before-stream", "w").write(text)
    open(RC, "w").write(text.replace("</openbox_config>", BINDS + "</openbox_config>"))
    pid = sh(["pgrep", "-x", "labwc"]).stdout.split()
    if pid:
        os.kill(int(pid[0]), signal.SIGHUP)          # reread the settings; nothing restarts
        time.sleep(1.0)
    return True


def press(fkey):
    """Press Ctrl+Alt+Super+F9 or F10 on a pretend keyboard."""
    from evdev import UInput, ecodes as e
    keys = [e.KEY_LEFTCTRL, e.KEY_LEFTALT, e.KEY_LEFTMETA, fkey]
    ui = UInput({e.EV_KEY: keys}, name="bmo-stream-keys")
    time.sleep(0.6)                                  # the desktop needs a moment to notice a new keyboard
    for k in keys:
        ui.write(e.EV_KEY, k, 1)
        ui.syn()
        time.sleep(0.03)
    time.sleep(0.1)
    for k in reversed(keys):
        ui.write(e.EV_KEY, k, 0)
        ui.syn()
        time.sleep(0.03)
    time.sleep(0.3)
    ui.close()


def make_screen():
    if TV in outputs():
        return True
    try:
        from evdev import ecodes as e
        ensure_binds()
        press(e.KEY_F9)
    except Exception as err:                        # no pretend keyboard: fall back to the old way
        print("could not press the key: %s" % err)
        return False
    for _ in range(20):
        if TV in outputs():
            break
        time.sleep(0.2)
    else:
        return False
    sh(["wlr-randr", "--output", TV, "--custom-mode", SIZE, "--pos", "800,0"])
    sh(["wlr-randr", "--output", PANEL, "--pos", "0,0", "--transform", "180"])
    return True


def drop_screen():
    if TV not in outputs():
        return
    try:
        from evdev import ecodes as e
        press(e.KEY_F10)
    except Exception as err:
        print("could not press the key: %s" % err)


def set_conf(index):
    lines = [ln for ln in open(CONF).read().splitlines() if not ln.startswith("output_name")]
    if index is not None:
        lines.append("output_name = %d" % index)
    open(CONF, "w").write("\n".join(lines) + "\n")
    me = "%s %s" % (sys.executable, os.path.abspath(__file__))
    apps = json.load(open(APPS))
    for app in apps.get("apps", []):
        app["prep-cmd"] = [{"do": me + " begin", "undo": me + " end"}]
    json.dump(apps, open(APPS, "w"))


def up():
    sh(["systemctl", "--user", "stop", UNIT])
    sh(["systemctl", "--user", "reset-failed", UNIT])
    ok = make_screen()
    names = outputs()
    set_conf(names.index(TV) if ok else None)
    r = sh(["systemd-run", "--user", "--unit=" + UNIT, "--setenv=WAYLAND_DISPLAY=" + ENV["WAYLAND_DISPLAY"],
            "--setenv=DISPLAY=:0", "/usr/bin/sunshine"])
    print("second screen: %s" % ("ready, BMO's own screen will stay upright" if ok else "NOT available, streams will use the old way"))
    print("sunshine: %s" % ("started" if r.returncode == 0 else r.stderr.strip()))
    return 0 if r.returncode == 0 else 1


def down():
    sh(["systemctl", "--user", "stop", UNIT])
    end()
    drop_screen()
    print("stopped")
    return 0


def begin():
    if TV in outputs():
        open(FLAG, "w").write("1")
    else:
        sh(["wlr-randr", "--output", PANEL, "--transform", "normal"])
    return 0


def end():
    if os.path.exists(FLAG):
        os.remove(FLAG)
    sh(["wlr-randr", "--output", PANEL, "--transform", "180"])
    return 0


def status():
    names = outputs()
    print("screens: %s" % ", ".join(names))
    print("sunshine: %s" % sh(["systemctl", "--user", "is-active", UNIT]).stdout.strip())
    print("a stream would use: %s" % ("the second screen (BMO stays upright)" if TV in names else "the real screen (old way, BMO flips)"))
    print("streaming now: %s" % ("yes" if os.path.exists(FLAG) else "no"))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    sys.exit({"up": up, "down": down, "begin": begin, "end": end, "status": status}.get(cmd, status)())
