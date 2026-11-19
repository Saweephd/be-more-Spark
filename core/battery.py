"""Battery and wall power for BMO's Geekworm X1203 power board.

The board has a fuel gauge chip at address 0x36 on the Raspberry Pi's
Inter-Integrated Circuit (I2C) bus 1, and it drives GPIO6 high while wall
power reaches the board's own inputs (its USB-C port, barrel jack or 5 V
socket). Power fed into the Raspberry Pi's own USB-C port runs BMO but does
not reach the board, so the signal stays low and the batteries do not charge.

The decision logic (Monitor) is plain code so it can be tested without hardware.
"""
import fcntl
import os
import re
import subprocess
import time

I2C_SLAVE = 0x0703
BUS = "/dev/i2c-1"
ADDRESS = 0x36

WARN_PERCENT = 15        # BMO says the battery is low
SHUTDOWN_PERCENT = 5     # BMO shuts down cleanly
REARM_PERCENT = 20       # the low warning can be given again above this


def decode(vcell_bytes, soc_bytes):
    """Turn the two raw register readings into (volts, percent)."""
    raw = (vcell_bytes[0] << 8) | vcell_bytes[1]
    volts = raw * 78.125e-6
    percent = soc_bytes[0] + soc_bytes[1] / 256.0
    return round(volts, 3), round(min(percent, 100.0), 1)


def read_gauge(bus=BUS, address=ADDRESS):
    fd = os.open(bus, os.O_RDWR)
    try:
        fcntl.ioctl(fd, I2C_SLAVE, address)
        os.write(fd, bytes([0x02]))
        vcell = os.read(fd, 2)
        os.write(fd, bytes([0x04]))
        soc = os.read(fd, 2)
    finally:
        os.close(fd)
    return decode(vcell, soc)


def wall_power():
    """True when the power board has wall power, False on battery, None if unknown."""
    try:
        out = subprocess.run(["gpioget", "-c", "gpiochip0", "--numeric", "GPIO6"],
                             capture_output=True, text=True, timeout=3).stdout.strip()
        return {"1": True, "0": False}.get(out)
    except Exception:
        return None


def read():
    """Everything at once: {"volts", "percent", "wall"}; raises OSError if the gauge is missing."""
    volts, percent = read_gauge()
    return {"volts": volts, "percent": percent, "wall": wall_power()}


STATUS_FILE = "/tmp/bmo_battery.json"


def spoken_status(status, rising=None, draining=None):
    """What BMO says when asked about its battery."""
    if not status:
        return "BMO cannot read its battery right now."
    pct = int(round(status["percent"]))
    if status.get("wall"):
        if pct >= 99:
            return "BMO is plugged in and the battery is full."
        if rising is False:
            return "BMO is plugged in, but the battery is not charging. It is at %d percent." % pct
        return "BMO is plugged in and charging. The battery is at %d percent." % pct
    if draining is False:
        return ("BMO's battery is at %d percent and holding steady, so BMO is probably plugged into the "
                "Raspberry Pi's own port. That port runs BMO but does not charge the battery." % pct)
    if pct <= WARN_PERCENT:
        return "BMO's battery is low, at %d percent. Please plug BMO in." % pct
    return "BMO is running on battery, at %d percent." % pct


def save_status(status, rising, draining, path=STATUS_FILE):
    import json
    try:
        with open(path + ".tmp", "w") as fh:
            json.dump({"time": time.time(), "status": status, "rising": rising, "draining": draining}, fh)
        os.replace(path + ".tmp", path)
    except OSError:
        pass


def current_report(path=STATUS_FILE, max_age=120):
    """The sentence for a spoken battery question: the agent's latest reading, else a fresh one."""
    import json
    try:
        with open(path) as fh:
            d = json.load(fh)
        if time.time() - d["time"] < max_age:
            return spoken_status(d["status"], d.get("rising"), d.get("draining"))
    except (OSError, ValueError, KeyError):
        pass
    try:
        return spoken_status(read())
    except OSError:
        return spoken_status(None)


_ASK = (r"\b(battery|batteries|charge level|charging|power level|how much (charge|power|juice))\b")
_NOT = r"\b(car|phone|laptop|tesla|aa|aaa|double a|watch)\b"


def match_question(text):
    t = re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower())
    return bool(re.search(_ASK, t)) and not re.search(_NOT, t)


class Monitor:
    """Decides when to warn and when to shut down. Feed it readings; it returns "warn", "shutdown" or None.

    The power board's wall power signal only covers its own inputs. If BMO is powered through the
    Raspberry Pi's USB-C port instead, the signal reads "battery" even though the battery is idle,
    so BMO only acts on a low battery that is actually going down (or is nearly empty).
    """

    def __init__(self, warn=WARN_PERCENT, shutdown=SHUTDOWN_PERCENT, rearm=REARM_PERCENT,
                 confirm=2, window_s=180, empty_volts=3.40):
        self.warn, self.shutdown, self.rearm, self.confirm = warn, shutdown, rearm, confirm
        self.window_s, self.empty_volts = window_s, empty_volts
        self.warned = False
        self.low_count = 0
        self.history = []          # (time, percent, volts, wall)

    def _span(self, now, wall_only=None):
        pts = [h for h in self.history if wall_only is None or bool(h[3]) == wall_only]
        if len(pts) < 2 or pts[-1][0] - pts[0][0] < self.window_s:
            return None
        return pts[0], pts[-1]

    def draining(self, now=None):
        span = self._span(now, wall_only=False)
        if not span:
            return None
        first, last = span
        return last[1] < first[1] - 0.2 or last[2] < first[2] - 0.015

    def rising(self, now=None):
        """True if charge went up over the last few minutes on wall power, False if not, None if too soon."""
        span = self._span(now, wall_only=True)
        if not span:
            return None
        return span[1][1] > span[0][1]

    def update(self, status, now=None):
        now = time.time() if now is None else now
        if not status:
            return None
        pct, volts, wall = status["percent"], status["volts"], status.get("wall")
        if self.history and bool(self.history[-1][3]) != bool(wall):
            self.history = []          # power source changed; start the trend again
        self.history = [h for h in self.history if now - h[0] < 900] + [(now, pct, volts, wall)]
        if wall or pct > self.rearm:
            self.warned = False
        if wall:
            self.low_count = 0
            return None
        empty = volts <= self.empty_volts
        draining = self.draining(now)
        if pct <= self.shutdown and (draining or empty):
            self.low_count += 1
            return "shutdown" if self.low_count >= self.confirm else None
        self.low_count = 0
        if pct <= self.warn and draining and not self.warned:
            self.warned = True
            return "warn"
        return None
