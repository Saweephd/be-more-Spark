"""BMO and the phone hotspot, for bmo-ctl.sh.

  status      Which Wi-Fi BMO is on, and whether a hotspot is saved
  setup       Save the phone hotspot: pick it from the networks in range, then type its password
              (the password is typed here, hidden, and goes straight to NetworkManager)
  hotspot     Move to the phone hotspot now
  home        Move back to the home Wi-Fi
  forget      Remove the saved hotspot

By voice: "BMO, switch to my phone hotspot" and "BMO, go back to the home Wi-Fi".
"""
import getpass
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import wifi  # noqa: E402


def in_session(argv, payload=None):
    """A remote login may not change the network, BMO's own session may. Run this script again inside it.
    Anything private goes down a pipe, never on a command line."""
    cmd = ["systemd-run", "--user", "--quiet", "--wait", "--pipe", "--collect", sys.executable, os.path.abspath(__file__)] + argv
    r = subprocess.run(cmd, input=json.dumps(payload) if payload is not None else None, text=True)
    return r.returncode


def main(argv):
    cmd = argv[0] if argv else "status"
    if cmd == "status":
        print(wifi.status_line())
        ssid = wifi.hotspot_name()
        print("Saved phone hotspot: %s" % (ssid or "none yet (run: ops/bmo-ctl.sh wifi setup)"))
        return 0
    if cmd == "setup":
        seen = wifi.scan()
        if not seen:
            print("No Wi-Fi networks in range.")
        for i, s in enumerate(seen, 1):
            print("  %2d. %s" % (i, s))
        pick = input("Turn the phone hotspot on, then type its number above, or its exact name: ").strip()
        ssid = seen[int(pick) - 1] if pick.isdigit() and 0 < int(pick) <= len(seen) else pick
        if not ssid:
            print("Nothing chosen.")
            return 2
        password = getpass.getpass("Password for \"%s\" (hidden as you type): " % ssid)
        payload = {"ssid": ssid, "password": password}
        if wifi.allowed():
            return _save(payload)
        return in_session(["_save"], payload)
    if cmd == "_save":
        return _save(json.loads(sys.stdin.read()))
    if cmd in ("hotspot", "home", "forget") and not wifi.allowed():
        return in_session([cmd])
    if cmd in ("hotspot", "home"):
        ok, line = wifi.switch(cmd)
        print(line)
        return 0 if ok else 1
    if cmd == "forget":
        print("Forgotten." if wifi.forget() else "There was no saved hotspot.")
        return 0
    print(__doc__)
    return 2


def _save(payload):
    ok, err = wifi.save(payload["ssid"], payload.get("password", ""))
    if ok:
        print("Saved. BMO will join \"%s\" by itself when the home Wi-Fi is out of range," % payload["ssid"])
        print("or when you say: BMO, switch to my phone hotspot.")
        return 0
    print("Could not save it: %s" % err)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
