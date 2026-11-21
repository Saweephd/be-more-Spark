"""Show BMO's screen on a Chromecast TV (the den's Google TV).

  python3 ops/bmo_tv.py start [TV name]   cast until stopped (run as the bmo-tv user service)
  python3 ops/bmo_tv.py list              list the Chromecast TVs BMO can see

BMO's face is an X11 window under Xwayland, so the screen is captured per window:
the games window when a game is running, otherwise BMO's face. GStreamer encodes it
as H.264 in a streamable Matroska file, served over HTTP to the TV's default media
receiver. Expect a delay of a few seconds; this is for showing BMO, not for playing.
"""
import http.server
import os
import re
import socket
import socketserver
import subprocess
import sys
import threading
import time

PORT = int(os.environ.get("BMO_TV_PORT", "8765"))
DEFAULT_TV = os.environ.get("BMO_TV_NAME", "Downstairs TV")
FACE_TITLE = "Pi Assistant"
NOT_GAMES = {FACE_TITLE, "Network Displays", "GNOME Network Displays", "wlroots wm", "xsettingsd"}
ENV = dict(os.environ, DISPLAY=os.environ.get("DISPLAY", ":0"))


def windows():
    """(xid, title, width, height) for every titled X11 window."""
    out = subprocess.run(["xwininfo", "-root", "-tree"], capture_output=True, text=True, env=ENV).stdout
    found = []
    for m in re.finditer(r"(0x[0-9a-f]+) \"([^\"]+)\".*?(\d+)x(\d+)\+", out):
        found.append((m.group(1), m.group(2), int(m.group(3)), int(m.group(4))))
    return found


def target_window():
    """The window to show: a running game if there is one, else BMO's face."""
    wins = windows()
    for xid, title, w, h in wins:              # a game is any other big window (the games set their own title)
        if title not in NOT_GAMES and w >= 300 and h >= 200:
            return xid
    for xid, title, w, h in wins:
        if title == FACE_TITLE:
            return xid
    return None


def pipeline(xid):
    return ["gst-launch-1.0", "-q",
            "ximagesrc", "xid=%s" % xid, "use-damage=false", "show-pointer=false", "!",
            "video/x-raw,framerate=20/1", "!", "videoconvert", "!", "videoscale", "!",
            "video/x-raw,width=800,height=480,format=I420", "!",
            "x264enc", "tune=zerolatency", "speed-preset=ultrafast", "bitrate=2500", "key-int-max=40", "!",
            "video/x-h264,profile=baseline", "!", "h264parse", "!",
            "matroskamux", "streamable=true", "!", "fdsink", "fd=1"]


class Stream(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        xid = target_window()
        if not xid:
            self.send_error(503, "BMO's window is not up")
            return
        self.send_response(200)
        self.send_header("Content-Type", "video/x-matroska")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        proc = subprocess.Popen(pipeline(xid), stdout=subprocess.PIPE, env=ENV)
        self.server.current = (proc, xid)
        try:
            while True:
                chunk = proc.stdout.read(16384)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            proc.kill()


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    current = (None, None)


def my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.1.1", 9))
        return s.getsockname()[0]
    finally:
        s.close()


def find_tv(name, timeout=10):
    import pychromecast
    casts, browser = pychromecast.get_listed_chromecasts(friendly_names=[name], timeout=timeout)
    if not casts:
        browser.stop_discovery()
        return None, None
    cast = casts[0]
    cast.wait()
    return cast, browser


def start(name):
    server = Server(("", PORT), Stream)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    cast, browser = find_tv(name)
    if cast is None:
        print("TV %r not found" % name)
        return 1
    url = "http://%s:%d/stream.mkv" % (my_ip(), PORT)
    mc = cast.media_controller

    def play():
        mc.play_media(url, "video/x-matroska", stream_type="LIVE", title="BMO")
        mc.block_until_active(timeout=15)

    play()
    print("Casting BMO to %s from %s" % (name, url))
    shown = server.current[1]
    try:
        while True:
            time.sleep(3)
            want = target_window()
            proc, xid = server.current
            if want and xid and want != xid:          # a game opened or closed: restart on the new window
                play()
            elif proc is None or proc.poll() is not None:
                if mc.status is None or mc.status.player_state in ("IDLE", "UNKNOWN"):
                    play()                              # the TV dropped the stream: start it again
    except KeyboardInterrupt:
        pass
    finally:
        try:
            cast.quit_app()
        except Exception:
            pass
        browser.stop_discovery()
        server.shutdown()
    return 0


def main(argv):
    if argv and argv[0] == "list":
        import pychromecast
        casts, browser = pychromecast.get_chromecasts(timeout=8)
        for c in casts:
            print("%-24s %s" % (c.cast_info.friendly_name, c.cast_info.host))
        browser.stop_discovery()
        return 0
    if argv and argv[0] == "start":
        return start(" ".join(argv[1:]) or DEFAULT_TV)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
