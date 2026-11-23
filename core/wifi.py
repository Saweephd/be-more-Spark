"""Moving BMO between the home Wi-Fi and a phone hotspot.

BMO's network is run by NetworkManager. The hotspot is saved once (ops/bmo_wifi.py setup) as a
connection named "bmo-hotspot". After that:
  - away from home BMO joins it by itself, because the home network is not in range;
  - "BMO, switch to my phone" makes the move at any time, with no network needed to hear it,
    since the command is matched on the Pi before anything is sent to the language model;
  - "BMO, go back to the home Wi-Fi" moves back.
"""
import subprocess
import time

HOTSPOT = "bmo-hotspot"
IFACE = "wlan0"


def _run(args, timeout=45):
    try:
        r = subprocess.run(["nmcli"] + list(args), capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def _split(line):
    """Split one line of nmcli -t output, where a colon inside a value is written as backslash colon."""
    out, cur, i = [], "", 0
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line):
            cur += line[i + 1]
            i += 2
        elif line[i] == ":":
            out.append(cur)
            cur = ""
            i += 1
        else:
            cur += line[i]
            i += 1
    out.append(cur)
    return out


def allowed(run=_run):
    """True when this process may change the network (BMO's own session may; a remote login may not)."""
    _, out, _ = run(["-t", "general", "permissions"])
    return "network-control:yes" in out


def connections(run=_run):
    """Saved Wi-Fi connections, as a list of names."""
    _, out, _ = run(["-t", "-f", "NAME,TYPE", "con", "show"])
    return [f[0] for f in map(_split, out.splitlines()) if len(f) >= 2 and f[1] == "802-11-wireless"]


def current(run=_run):
    """(connection name, network name) BMO is on now, or (None, None)."""
    _, out, _ = run(["-t", "-f", "NAME,TYPE,DEVICE", "con", "show", "--active"])
    for f in map(_split, out.splitlines()):
        if len(f) >= 2 and f[1] == "802-11-wireless":
            _, ssid, _ = run(["-g", "802-11-wireless.ssid", "con", "show", f[0]])
            return f[0], ssid or f[0]
    return None, None


def hotspot_name(run=_run):
    if HOTSPOT not in connections(run):
        return None
    _, ssid, _ = run(["-g", "802-11-wireless.ssid", "con", "show", HOTSPOT])
    return ssid or None


def scan(run=_run):
    """Networks in range, strongest first, each name once."""
    _, out, _ = run(["-t", "-f", "SSID,SIGNAL", "dev", "wifi", "list", "--rescan", "yes"])
    best = {}
    for f in map(_split, out.splitlines()):
        if len(f) >= 2 and f[0]:
            try:
                best[f[0]] = max(best.get(f[0], 0), int(f[1]))
            except ValueError:
                pass
    return sorted(best, key=lambda s: -best[s])


def save(ssid, password, run=_run):
    """Remember the phone hotspot. It joins by itself when home is out of range (lower priority than home)."""
    run(["con", "delete", HOTSPOT])
    args = ["con", "add", "type", "wifi", "ifname", IFACE, "con-name", HOTSPOT, "ssid", ssid,
            "connection.autoconnect", "yes", "connection.autoconnect-priority", "-10"]
    if password:
        args += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password]
    code, _, err = run(args)
    return code == 0, err


def forget(run=_run):
    return run(["con", "delete", HOTSPOT])[0] == 0


def switch(target, run=_run, sleep=time.sleep, tries=3):
    """Move to the phone hotspot or back home. Returns (worked, the line BMO should say)."""
    before, _ = current(run)
    if target == "hotspot":
        ssid = hotspot_name(run)
        if not ssid:
            return False, "BMO does not know your phone hotspot yet. It has to be set up one time first."
        if before == HOTSPOT:
            return True, "BMO is already on your phone hotspot."
        for attempt in range(tries):                 # a phone often takes a moment to show its hotspot
            if ssid in scan(run):
                code, _, err = run(["-w", "30", "con", "up", HOTSPOT], 50)
                if code == 0:
                    return True, "BMO is on your phone hotspot now."
            if attempt + 1 < tries:
                sleep(4)
        if before:
            run(["-w", "20", "con", "up", before], 40)
        if ssid in scan(run):
            return False, "BMO can see your phone, but could not join it. The password may have changed."
        return False, "BMO could not find your phone hotspot. Is it turned on?"
    homes = [c for c in connections(run) if c != HOTSPOT]
    if before and before != HOTSPOT:
        return True, "BMO is already on the home Wi-Fi."
    for name in homes:
        if run(["-w", "25", "con", "up", name], 45)[0] == 0:
            return True, "BMO is back on the home Wi-Fi."
    if before:
        run(["-w", "20", "con", "up", before], 40)
    return False, "BMO could not find the home Wi-Fi from here."


def status_line(run=_run):
    name, ssid = current(run)
    if not name:
        return "BMO is not on any Wi-Fi right now."
    if name == HOTSPOT:
        return "BMO is on your phone hotspot, %s." % ssid
    return "BMO is on the Wi-Fi called %s." % ssid
