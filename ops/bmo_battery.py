"""Battery and wall power from the Geekworm X1203 power board, for bmo-ctl.sh battery.

Needs the I2C bus switched on once (sudo raspi-config nonint do_i2c 0).
"""
import os
import sys

from core.battery import BUS, decode, read  # noqa: F401  (decode kept for older callers)


def main():
    if not os.path.exists(BUS):
        print("battery: %s is missing. The I2C bus is switched off; turn it on once with: sudo raspi-config nonint do_i2c 0" % BUS)
        return 1
    try:
        s = read()
    except OSError as e:
        print("battery: no answer from the gauge at 0x36 (%s). Is the X1203 seated on the pins?" % e)
        return 1
    power = {True: "wall power to the power board (charging)", False: "running on battery",
             None: "wall power unknown"}[s["wall"]]
    state = "low" if s["percent"] < 15 else "ok"
    print("battery: %.2f V, %.0f%% (%s), %s" % (s["volts"], s["percent"], state, power))
    return 0


if __name__ == "__main__":
    sys.exit(main())
