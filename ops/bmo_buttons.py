"""Button board test: shows each press as BMO's Raspberry Pi sees it.

  python ops/bmo_buttons.py [seconds]     (default 20)

The Feather board shows up as a Universal Serial Bus (USB) keyboard. This reads
that keyboard directly, so it works while BMO's face is running.
"""
import glob
import os
import select
import struct
import sys
import time

NAMES = {103: "Up", 106: "Right", 108: "Down", 105: "Left",
         42: "Triangle (back)", 28: "Small circle (menu)", 57: "Big circle (talk / jump)"}
EVENT = struct.Struct("llHHi")
EV_KEY = 1


def find_board():
    for pattern in ("*Adafruit*event-kbd", "*Feather*event-kbd", "*Arduino*event-kbd"):
        hits = sorted(glob.glob("/dev/input/by-id/" + pattern))
        if hits:
            return hits[0]
    return None


def summary(seen):
    missing = [name for code, name in NAMES.items() if code not in seen]
    if not missing:
        return "buttons: all 7 seen"
    return "buttons: %d of 7 seen; not seen: %s" % (len(NAMES) - len(missing), ", ".join(missing))


def main(argv):
    seconds = float(argv[0]) if argv else 20.0
    path = find_board()
    if not path:
        print("buttons: the button board is not connected. Plug the Feather's USB cable into the Pi.")
        return 1
    print("buttons: reading %s for %d seconds. Press each button once." % (os.path.basename(path), seconds))
    seen = set()
    end = time.time() + seconds
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        while time.time() < end and len(seen) < len(NAMES):
            ready, _, _ = select.select([fd], [], [], 0.25)
            if not ready:
                continue
            data = os.read(fd, EVENT.size * 32)
            for i in range(0, len(data) - EVENT.size + 1, EVENT.size):
                _s, _u, kind, code, value = EVENT.unpack_from(data, i)
                if kind == EV_KEY and value == 1:
                    print("  pressed: %s" % NAMES.get(code, "unknown key %d" % code), flush=True)
                    if code in NAMES:
                        seen.add(code)
    finally:
        os.close(fd)
    print(summary(seen))
    return 0 if len(seen) == len(NAMES) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
