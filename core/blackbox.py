"""A flight recorder for BMO. The system log lives in memory and is lost when BMO loses power or locks up,
which is exactly when it is wanted. Every 20 seconds this writes one line of vital signs to a small file on
the card, flushed at once, so after a crash the last line says what BMO was doing and how its power looked."""
import os
import subprocess
import time

PATH = os.path.expanduser("~/bmo-blackbox.log")
KEEP = 4000                      # lines: a little under a day at one line every 20 seconds


def _run(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=3).stdout.strip()
    except Exception:
        return "?"


def vitals():
    """Supply voltage at the Pi, the under-voltage flags, temperature, load and free memory, as one string."""
    volts = _run(["vcgencmd", "pmic_read_adc", "EXT5V_V"]).split("=")[-1].replace("V", "")[:5]
    flags = _run(["vcgencmd", "get_throttled"]).split("=")[-1]
    temp = _run(["vcgencmd", "measure_temp"]).split("=")[-1].replace("'C", "")
    try:
        load = open("/proc/loadavg").read().split()[0]
        free = next(int(l.split()[1]) // 1024 for l in open("/proc/meminfo") if l.startswith("MemAvailable"))
    except Exception:
        load, free = "?", "?"
    return "supply=%sV flags=%s temp=%sC load=%s free=%sMB" % (volts, flags, temp, load, free)


def line(state="", game="", battery="", tv=""):
    return "%s state=%s game=%s battery=%s tv=%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), state or "-", game or "-",
                                                        battery or "-", tv or "-", vitals())


def write(text, path=None):
    """Append one line and force it onto the card. Trims the file now and then so it never grows large."""
    path = path or PATH
    try:
        with open(path, "a") as fh:
            fh.write(text.rstrip("\n") + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        if os.path.getsize(path) > KEEP * 160:
            rows = open(path).read().splitlines()[-KEEP // 2:]
            with open(path + ".tmp", "w") as fh:
                fh.write("\n".join(rows) + "\n")
            os.replace(path + ".tmp", path)
    except OSError:
        pass


def last(n=12, path=None):
    try:
        return open(path or PATH).read().splitlines()[-n:]
    except OSError:
        return []
