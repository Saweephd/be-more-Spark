"""Moving BMO between the home Wi-Fi and the phone hotspot, with a pretend NetworkManager."""
import unittest

from core import extras, wifi


class FakeNM:
    def __init__(self, saved=("CrownCorbi",), active="CrownCorbi", in_range=("CrownCorbi",), ssids=None, join_ok=True):
        self.saved, self.active, self.in_range, self.join_ok = list(saved), active, list(in_range), join_ok
        self.ssids = dict(ssids or {"CrownCorbi": "CrownCorbi", wifi.HOTSPOT: "Stan's iPhone"})
        self.calls = []

    def __call__(self, args, timeout=45):
        self.calls.append(list(args))
        a = [x for x in args if not x.startswith("-") and not x.isdigit()] if args[0] in ("-w",) else list(args)
        if "permissions" in args:
            return 0, "org.freedesktop.NetworkManager.network-control:yes", ""
        if args[:2] == ["-t", "-f"] and "--active" in args:
            return 0, ("%s:802-11-wireless:wlan0" % self.active.replace(":", "\\:")) if self.active else "lo:loopback:lo", ""
        if args[:2] == ["-t", "-f"] and args[2] == "NAME,TYPE":
            return 0, "\n".join("%s:802-11-wireless" % s for s in self.saved) + "\nlo:loopback", ""
        if args[0] == "-g":
            return 0, self.ssids.get(args[-1], ""), ""
        if "list" in args:
            return 0, "\n".join("%s:80" % s.replace(":", "\\:") for s in self.in_range), ""
        if "up" in a:
            name = a[-1]
            if self.ssids.get(name) in self.in_range and (self.join_ok or name != wifi.HOTSPOT):
                self.active = name
                return 0, "", ""
            return 4, "", "no network with that name"
        if "add" in args:
            name = args[args.index("con-name") + 1]
            self.saved.append(name)
            self.ssids[name] = args[args.index("ssid") + 1]
            return 0, "", ""
        if "delete" in args:
            if args[-1] in self.saved:
                self.saved.remove(args[-1])
                return 0, "", ""
            return 10, "", "unknown connection"
        return 0, "", ""


class Wifi(unittest.TestCase):
    def test_voice_phrases(self):
        for said in ("switch to my phone hotspot", "connect to my hotspot", "BMO shift to the hotspot",
                     "use my phone for internet", "connect to my phone's wifi", "go on my iphone hotspot please"):
            self.assertEqual(extras.match_wifi(said), "hotspot", said)
        for said in ("go back to the home wifi", "switch to the home network", "connect to the house wi-fi"):
            self.assertEqual(extras.match_wifi(said), "home", said)
        for said in ("what wifi are you on", "which network are you on BMO", "are you online"):
            self.assertEqual(extras.match_wifi(said), "status", said)
        for said in ("where is my phone", "play a game on my phone", "call my phone", "what is a hotspot",
                     "play bacon pancakes", "I am going home", "turn off the tv"):
            self.assertIsNone(extras.match_wifi(said), said)

    def test_not_set_up_yet(self):
        ok, line = wifi.switch("hotspot", run=FakeNM(), sleep=lambda s: None)
        self.assertFalse(ok)
        self.assertIn("set up", line)

    def test_save_then_switch_and_back(self):
        nm = FakeNM(in_range=("CrownCorbi", "Stan's iPhone"))
        self.assertTrue(wifi.save("Stan's iPhone", "secret", run=nm)[0])
        add = [c for c in nm.calls if "add" in c][0]
        self.assertEqual(add[add.index("connection.autoconnect-priority") + 1], "-10")   # home stays first choice
        self.assertEqual(wifi.switch("hotspot", run=nm, sleep=lambda s: None), (True, "BMO is on your phone hotspot now."))
        self.assertEqual(wifi.status_line(run=nm), "BMO is on your phone hotspot, Stan's iPhone.")
        self.assertEqual(wifi.switch("home", run=nm, sleep=lambda s: None), (True, "BMO is back on the home Wi-Fi."))
        self.assertEqual(nm.active, "CrownCorbi")

    def test_phone_off_falls_back_to_where_it_was(self):
        nm = FakeNM(saved=("CrownCorbi", wifi.HOTSPOT))
        ok, line = wifi.switch("hotspot", run=nm, sleep=lambda s: None)
        self.assertFalse(ok)
        self.assertIn("turned on", line)
        self.assertEqual(nm.active, "CrownCorbi")

    def test_wrong_password_is_reported(self):
        nm = FakeNM(saved=("CrownCorbi", wifi.HOTSPOT), in_range=("CrownCorbi", "Stan's iPhone"), join_ok=False)
        ok, line = wifi.switch("hotspot", run=nm, sleep=lambda s: None)
        self.assertFalse(ok)
        self.assertIn("password", line)
        self.assertEqual(nm.active, "CrownCorbi")

    def test_away_from_home_with_nothing_joined(self):
        nm = FakeNM(saved=("CrownCorbi", wifi.HOTSPOT), active=None, in_range=("Stan's iPhone",))
        self.assertEqual(wifi.status_line(run=nm), "BMO is not on any Wi-Fi right now.")
        self.assertTrue(wifi.switch("hotspot", run=nm, sleep=lambda s: None)[0])
        ok, line = wifi.switch("home", run=nm, sleep=lambda s: None)
        self.assertFalse(ok)
        self.assertEqual(nm.active, wifi.HOTSPOT)                                         # stays online

    def test_colons_in_names(self):
        self.assertEqual(wifi._split("My\\:Net:80"), ["My:Net", "80"])


if __name__ == "__main__":
    unittest.main()
