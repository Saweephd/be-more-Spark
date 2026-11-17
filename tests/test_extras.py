"""Game requests, spoken shutdown and night clock hours (core/extras.py)."""
import datetime
import unittest

from core import extras


class GameRequests(unittest.TestCase):
    def test_named_games(self):
        cases = {
            "play Mazee Run": "mazee_run", "Play Maisie run.": "mazee_run", "let's play mazy run": "mazee_run",
            "Can we play the dog game?": "mazee_run", "play BMO catch": "bmo_catch", "Play Beemo Cash": "bmo_catch",
            "start angry poppa": "angry_poppa", "I want to play Angry Papa.": "angry_poppa",
            "play the gnat game": "angry_poppa", "Angry Poppa": "angry_poppa",
        }
        for said, want in cases.items():
            self.assertEqual(extras.match_game(said), want, said)

    def test_menu(self):
        for said in ("what games do you have", "let's play a game", "show me the games", "play a video game"):
            self.assertEqual(extras.match_game(said), "menu", said)

    def test_not_games(self):
        for said in ("who is Mazee", "play some music", "what time is it", "tell me about the dog",
                     "did you catch the news about the angry customer", "how do I catch a cold", ""):
            self.assertIsNone(extras.match_game(said), said)


class Shutdown(unittest.TestCase):
    def test_shutdown_phrases(self):
        for said in ("shut down", "Hey, shut down please.", "power off", "turn yourself off", "go to sleep for the night"):
            self.assertTrue(extras.match_shutdown(said), said)

    def test_not_shutdown(self):
        for said in ("how do I shut down my computer", "turn off the lights", "why did the tv shut down",
                     "go to sleep", "good night", "turn off the music"):
            self.assertFalse(extras.match_shutdown(said), said)

    def test_yes_no(self):
        self.assertTrue(extras.match_yes("Yes."))
        self.assertTrue(extras.match_yes("yeah go ahead"))
        self.assertFalse(extras.match_yes("what is the weather"))
        self.assertTrue(extras.match_no("no, don't"))
        self.assertTrue(extras.match_no("never mind"))


class NightClock(unittest.TestCase):
    def at(self, hour, minute=0):
        return datetime.datetime(2026, 11, 16, hour, minute)

    def test_default_hours(self):
        for hour, want in ((21, False), (22, True), (23, True), (0, True), (6, True), (7, False), (12, False)):
            self.assertEqual(extras.night_clock_active(self.at(hour)), want, hour)

    def test_other_ranges(self):
        self.assertTrue(extras.night_clock_active(self.at(2), 1, 5))
        self.assertFalse(extras.night_clock_active(self.at(6), 1, 5))
        self.assertFalse(extras.night_clock_active(self.at(3), 4, 4))

    def test_clock_text(self):
        self.assertEqual(extras.clock_text(self.at(22, 5)), ("10:05", "Mon 16 Nov"))
        self.assertEqual(extras.clock_text(self.at(0, 30)), ("12:30", "Mon 16 Nov"))
        self.assertEqual(extras.clock_text(self.at(22, 5), twelve_hour=False)[0], "22:05")
        self.assertEqual(extras.clock_text(datetime.datetime(2026, 12, 5, 9, 0))[1], "Sat 5 Dec")


class SpokenResult(unittest.TestCase):
    def test_lines(self):
        self.assertIn("another time", extras.spoken_result({"played": False}))
        self.assertIn("another time", extras.spoken_result(None))
        self.assertIn("new best", extras.spoken_result({"played": True, "title": "Mazee Run", "score": 120, "best": 120, "new_best": True}))
        line = extras.spoken_result({"played": True, "title": "BMO Catch", "score": 40, "best": 90, "new_best": False})
        self.assertIn("40", line)
        self.assertIn("90", line)


if __name__ == "__main__":
    unittest.main()


class VoicePath(unittest.TestCase):
    """The same checks through Brain.stream_think, which is what the agent calls."""

    @classmethod
    def setUpClass(cls):
        import sys
        import types
        for name in ("ddgs", "duckduckgo_search"):          # the search library is only on BMO
            if name not in sys.modules:
                try:
                    __import__(name)
                except Exception:
                    stub = types.ModuleType(name)
                    stub.DDGS = object
                    sys.modules[name] = stub
        from core.llm import Brain
        cls.Brain = Brain

    def say(self, brain, text):
        return list(brain.stream_think(text))

    def test_game_request_becomes_an_action(self):
        out = self.say(self.Brain(), "Play Mazee Run")
        self.assertEqual(len(out), 2)
        self.assertIn('"play_game"', out[1])
        self.assertIn('"mazee_run"', out[1])
        out = self.say(self.Brain(), "what games do you have")
        self.assertIn('"menu"', out[1])

    def test_shutdown_needs_a_yes(self):
        brain = self.Brain()
        out = self.say(brain, "shut down")
        self.assertEqual(len(out), 2)
        self.assertNotIn("action", out[0])
        self.assertIn('"listen"', out[1])
        out = self.say(brain, "yes")
        self.assertIn('"shutdown"', out[-1])

    def test_shutdown_cancelled_by_no_or_by_anything_else(self):
        brain = self.Brain()
        self.say(brain, "power off")
        out = self.say(brain, "no thanks")
        self.assertEqual(len(out), 1)
        self.assertIn("stay awake", out[0])
        self.assertFalse(brain._shutdown_pending)

    def test_stale_confirmation_is_ignored(self):
        brain = self.Brain()
        self.say(brain, "shut down")
        brain._shutdown_pending -= 600                         # asked ten minutes ago
        out = self.say(brain, "play bmo catch")
        self.assertIn('"bmo_catch"', out[-1])
