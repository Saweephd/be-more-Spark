"""Battery: gauge decoding, warn and shutdown decisions, spoken answers."""
import unittest

from core import battery as b


def st(pct, volts=3.7, wall=False):
    return {"percent": pct, "volts": volts, "wall": wall}


def feed(m, readings, step=30):
    out = []
    for i, r in enumerate(readings):
        out.append(m.update(r, now=1000 + i * step))
    return out


class Decisions(unittest.TestCase):
    def test_decode(self):
        self.assertEqual(b.decode(bytes([0xD0, 0x00]), bytes([87, 128])), (4.16, 87.5))

    def test_warn_once_while_draining(self):
        m = b.Monitor()
        out = feed(m, [st(18 - i * 0.5, 3.65 - i * 0.005) for i in range(14)])
        self.assertEqual(out.count("warn"), 1)
        self.assertNotIn("shutdown", out)

    def test_shutdown_needs_two_low_readings_while_draining(self):
        m = b.Monitor()
        out = feed(m, [st(9 - i, 3.55 - i * 0.01) for i in range(9)])
        self.assertIn("shutdown", out)
        first = out.index("shutdown")
        self.assertTrue(all(x != "shutdown" for x in out[:first]))

    def test_never_on_wall_power(self):
        m = b.Monitor()
        out = feed(m, [st(3, 3.5, wall=True) for _ in range(20)])
        self.assertEqual(set(out), {None})

    def test_pi_port_power_does_not_shut_down(self):
        """Low percent but steady: BMO is on the Pi's own port, not really on battery."""
        m = b.Monitor()
        out = feed(m, [st(5.1, 3.54) for _ in range(20)])
        self.assertEqual(set(out), {None})
        self.assertFalse(m.draining())

    def test_nearly_empty_cell_shuts_down_even_without_a_trend(self):
        m = b.Monitor()
        out = feed(m, [st(2, 3.35), st(2, 3.35)])
        self.assertEqual(out[-1], "shutdown")

    def test_warning_rearms_after_charging(self):
        m = b.Monitor()
        feed(m, [st(14 - i * 0.5, 3.6 - i * 0.01) for i in range(10)])
        self.assertTrue(m.warned)
        m.update(st(30, 3.9, wall=True), now=5000)
        self.assertFalse(m.warned)

    def test_rising_on_wall_power(self):
        m = b.Monitor()
        feed(m, [st(20 + i, 3.9, wall=True) for i in range(10)])
        self.assertTrue(m.rising())


class Speech(unittest.TestCase):
    def test_questions(self):
        for said in ("how's your battery", "BMO, are you charging?", "what is your battery level", "how much charge do you have"):
            self.assertTrue(b.match_question(said), said)
        for said in ("my phone battery is dead", "what time is it", "play mazee run", "charge my car battery"):
            self.assertFalse(b.match_question(said), said)

    def test_answers(self):
        self.assertIn("charging", b.spoken_status(st(40, wall=True)))
        self.assertIn("full", b.spoken_status(st(100, wall=True)))
        self.assertIn("not charging", b.spoken_status(st(40, wall=True), rising=False))
        self.assertIn("low", b.spoken_status(st(9), draining=True))
        self.assertIn("Raspberry Pi's own port", b.spoken_status(st(5), draining=False))
        self.assertIn("on battery, at 60", b.spoken_status(st(60), draining=True))


if __name__ == "__main__":
    unittest.main()
