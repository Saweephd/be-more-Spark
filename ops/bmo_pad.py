"""Bluetooth game controllers, for bmo-ctl.sh.

  list            Controllers BMO can see right now
  log [seconds]   Record every button and D-pad press to /tmp/pad_events.log (default 300 seconds),
                  to learn which button is which on a new controller
  show            Print the recording, one line per press
"""
import select
import sys
import time

import evdev
from evdev import ecodes as e

LOG = "/tmp/pad_events.log"
SKIP = ("virtualhid", "ft5x06", "pwr_button", "hdmi", "feather", "sound device", "uacdemo", "consumer control")


def pads():
    out = []
    for path in evdev.list_devices():
        d = evdev.InputDevice(path)
        if not any(s in d.name.lower() for s in SKIP):
            out.append(d)
    return out


def name_of(ev):
    if ev.type == e.EV_KEY:
        n = e.BTN.get(ev.code) or e.KEY.get(ev.code) or ev.code
        return "button %s (%d)" % (n[0] if isinstance(n, (list, tuple)) else n, ev.code)
    n = e.ABS.get(ev.code, ev.code)
    return "axis %s (%d) = %d" % (n, ev.code, ev.value)


def log(seconds):
    devs = pads()
    with open(LOG, "w") as f:
        f.write("watching: %s\n" % ", ".join("%s [%s]" % (d.name, d.path) for d in devs))
        f.flush()
        rest = {}
        t0 = time.time()
        while time.time() - t0 < seconds:
            ready, _, _ = select.select(devs, [], [], 1.0)
            for d in ready:
                try:
                    events = list(d.read())
                except OSError:
                    f.write("%.1f %s went away\n" % (time.time() - t0, d.name))
                    devs.remove(d)
                    continue
                for ev in events:
                    if ev.type == e.EV_KEY and ev.value == 1:
                        f.write("%.1f %s: %s\n" % (time.time() - t0, d.name, name_of(ev)))
                    elif ev.type == e.EV_ABS:
                        info = d.absinfo(ev.code)
                        mid = (info.min + info.max) / 2
                        span = max(1, info.max - info.min)
                        far = abs(ev.value - mid) > span * 0.3
                        if far and not rest.get((d.path, ev.code)):
                            f.write("%.1f %s: %s (range %d to %d)\n" % (time.time() - t0, d.name, name_of(ev), info.min, info.max))
                        rest[(d.path, ev.code)] = far
                f.flush()
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "log":
        sys.exit(log(float(sys.argv[2]) if len(sys.argv) > 2 else 300))
    if cmd == "show":
        try:
            print(open(LOG).read().rstrip() or "(nothing recorded)")
        except OSError:
            print("(no recording yet)")
        sys.exit(0)
    for d in pads():
        print("%s  %s" % (d.path, d.name))
