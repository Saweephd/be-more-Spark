"""TV mode: whether BMO's games should play on the TV.

Two things must both be true for a game to open on the TV's screen:
  - TV mode is on. Connecting from the TV turns it on by itself and disconnecting turns it off; it can
    also be said out loud or switched in the games menu, for instance to pull a game back onto BMO
    while the TV stays connected.
  - a stream from the TV is connected (Moonlight on the TV, picked "BMO"); ops/bmo_stream.py marks that.
With TV mode on and no stream yet, games stay on BMO and the menu says what to do on the TV.
"""
import os

MODE = "/tmp/bmo_tv_mode"
STREAM = "/tmp/bmo_streaming"


def on():
    return os.path.exists(MODE)


def connected():
    return os.path.exists(STREAM)


def use_tv():
    return on() and connected()


def set_mode(want):
    if want:
        open(MODE, "w").write("1")
    elif os.path.exists(MODE):
        os.remove(MODE)
    return want


def line(want=None):
    """What BMO says after the switch (or about the way things stand)."""
    want = on() if want is None else want
    if not want:
        return "TV mode is off. Games will play right here on BMO."
    if connected():
        return "TV mode is on. Games will play on the TV."
    return "TV mode is on. Now open Moonlight on the TV and pick BMO."


def hint():
    """The short version for the games menu."""
    if not on():
        return ""
    return "Playing on the TV" if connected() else "On the TV: open Moonlight, pick BMO"
