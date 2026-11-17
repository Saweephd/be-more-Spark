"""Read the battery gauge on the Geekworm X1203 power board.

The board carries a Maxim fuel gauge chip at address 0x36 on the Raspberry Pi's
Inter-Integrated Circuit (I2C) bus 1. This needs that bus switched on once
(sudo raspi-config nonint do_i2c 0). No extra Python packages are used.
"""
import fcntl
import os
import sys

I2C_SLAVE = 0x0703
BUS = "/dev/i2c-1"
ADDRESS = 0x36


def decode(vcell_bytes, soc_bytes):
    """Turn the two raw register readings into (volts, percent)."""
    raw = (vcell_bytes[0] << 8) | vcell_bytes[1]
    volts = raw * 78.125e-6
    percent = soc_bytes[0] + soc_bytes[1] / 256.0
    return round(volts, 3), round(min(percent, 100.0), 1)


def read(bus=BUS, address=ADDRESS):
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


def main():
    if not os.path.exists(BUS):
        print("battery: %s is missing. The I2C bus is switched off; turn it on once with: sudo raspi-config nonint do_i2c 0" % BUS)
        return 1
    try:
        volts, percent = read()
    except OSError as e:
        print("battery: no answer from the gauge at 0x36 (%s). Is the X1203 seated on the pins?" % e)
        return 1
    state = "low" if percent < 15 else "ok"
    print("battery: %.2f V, %.0f%% (%s)" % (volts, percent, state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
