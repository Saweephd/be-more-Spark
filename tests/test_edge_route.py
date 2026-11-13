"""Route selection and bmo-ctl.sh argument handling.  No network needed.

Run: python -m unittest tests.test_edge_route
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from core.edge.bmo_skills import BMOSkillRouter

REPO = Path(__file__).resolve().parent.parent
CTL = str(REPO / "ops" / "bmo-ctl.sh")


class RouteTests(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp(prefix="bmo-test-"))
        # Throwaway config and memory, so the real household memory is never read.
        self.router = BMOSkillRouter(config_path=tmp / "config.json", memory_path=tmp / "memory.json")

    def test_time_is_answered_locally(self):
        reply = self.router.try_handle("what time is it")
        self.assertIsInstance(reply, str)
        self.assertTrue(reply)

    def test_general_knowledge_goes_to_the_model(self):
        self.assertIsNone(self.router.try_handle("what is the capital of Peru"))

    def test_math_is_local_and_safe(self):
        self.assertIn("4", self.router.try_handle("calculate 2 + 2"))
        # Not evaluated as Python.
        reply = self.router.try_handle("calculate __import__('os').system('true')")
        self.assertNotIn("0", reply[:1])


class MemoryMatchTests(unittest.TestCase):
    MEMORY = {
        "aliases": {"Rexy": ["rexie", "wrecksy", "rexi"], "BMO": ["bimo", "beemo"]},
        "quick_answers": {
            "rose": "ROSE", "work": "WORK", "van": "VAN", "dog": "DOG",
            "wifi password": "WIFI", "team size": "TEAM",
        },
        "facts": [
            {"keywords": ["hurt finn", "if someone tries"], "answer": "SIGNATURE"},
            {"keywords": ["maldives"], "answer": "MALDIVES"},
        ],
    }

    def look(self, text):
        from core.edge.bmo_skills import Skills
        return Skills.memory_lookup(text, self.MEMORY)

    def test_direct_questions_match_single_word_keys(self):
        for q in ("Who is Rose?", "who's rose", "Hey BMO, tell me about Rose.", "Rose",
                  "What about the van?", "tell me about my dog"):
            self.assertIsNotNone(self.look(q), q)

    def test_single_word_keys_do_not_hijack_other_questions(self):
        for q in ("How does a microwave work?", "What should I get Rose for her birthday?",
                  "Can we advance the clock?", "Is a hot dog a sandwich?",
                  "Write a line of prose about the sea", "What is the capital of Peru?"):
            self.assertIsNone(self.look(q), q)

    def test_multi_word_keys_match_anywhere_on_word_boundaries(self):
        self.assertEqual(self.look("what's the wifi password again"), "WIFI")
        self.assertEqual(self.look("What would you do if someone tries to hurt Finn?"), "SIGNATURE")
        self.assertIsNone(self.look("the wifi passwords are long"))

    def test_fact_single_word_needs_a_direct_ask(self):
        self.assertEqual(self.look("Tell me about the Maldives"), "MALDIVES")
        self.assertIsNone(self.look("How deep is the ocean around the Maldives?"))

    def test_aliases_fix_speech_to_text_spellings(self):
        from core.edge.bmo_skills import apply_aliases
        a = self.MEMORY["aliases"]
        self.assertEqual(apply_aliases("What if someone hurt Rexie?", a), "What if someone hurt Rexy?")
        self.assertEqual(apply_aliases("hey bimo, where is WRECKSY", a), "hey BMO, where is Rexy")
        self.assertEqual(apply_aliases("the rexies are out", a), "the rexies are out")
        self.assertEqual(apply_aliases("no names here", None), "no names here")

    def test_household_notes_reach_the_system_prompt_only_when_present(self):
        from unittest import mock
        import core.config as config
        with mock.patch.object(config, "HOUSEHOLD_FILE", "/nonexistent/notes.md"):
            self.assertNotIn("HOUSEHOLD NOTES", config.get_system_prompt())
        path = tempfile.mktemp(suffix=".md")
        with open(path, "w") as f:
            f.write("The dog is called Testdog.")
        with mock.patch.object(config, "HOUSEHOLD_FILE", path):
            prompt = config.get_system_prompt()
        self.assertIn("HOUSEHOLD NOTES", prompt)
        self.assertIn("Testdog", prompt)
        self.assertTrue(prompt.startswith("You are BMO"))


class LocalPronunciationTests(unittest.TestCase):
    def test_device_only_pronunciations_are_applied(self):
        import json
        from unittest import mock
        import core.tts as tts
        path = tempfile.mktemp(suffix=".json")
        with open(path, "w") as f:
            json.dump({"Testdog": "tess dawg"}, f)
        with mock.patch.object(tts, "LOCAL_PRONUNCIATION_FILE", path), \
             mock.patch.object(tts, "load_pronunciations", return_value={}):
            self.assertEqual(tts.clean_text_for_speech("Where is Testdog today"), "Where is tess dawg today")
        with mock.patch.object(tts, "LOCAL_PRONUNCIATION_FILE", "/nonexistent.json"), \
             mock.patch.object(tts, "load_pronunciations", return_value={}):
            self.assertEqual(tts.clean_text_for_speech("Where is Testdog"), "Where is Testdog")


class WeatherTests(unittest.TestCase):
    DATA = {
        "current": {"temperature_2m": 41.2, "apparent_temperature": 35.0, "weather_code": 3},
        "daily": {"weather_code": [61, 0], "temperature_2m_max": [47.6, 55.1],
                  "temperature_2m_min": [33.9, 38.2], "precipitation_probability_max": [70, 5]},
    }

    def test_today(self):
        from core.edge.bmo_skills import Skills
        line = Skills.describe_weather(self.DATA)
        self.assertEqual(line, "Right now it is 41 degrees, feels like 35 and cloudy. "
                               "Today: light rain, high 48, low 34, with a 70 percent chance of rain or snow.")

    def test_tomorrow(self):
        from core.edge.bmo_skills import Skills
        self.assertEqual(Skills.describe_weather(self.DATA, tomorrow=True),
                         "Tomorrow looks clear, with a high of 55 and a low of 38 degrees.")

    def test_unconfigured_location_falls_through_to_the_model(self):
        from core.edge.bmo_skills import Skills
        self.assertIsNone(Skills.weather({"weather_lat": "", "weather_lon": ""}))

    def test_small_talk_is_not_a_status_request(self):
        from core.edge.bmo_skills import IntentClassifier
        self.assertIsNone(IntentClassifier.classify("how are you doing today"))
        self.assertNotEqual(IntentClassifier.classify("who is outside"), "weather")
        self.assertEqual(IntentClassifier.classify("what's the weather today"), "weather")


class CtlArgumentTests(unittest.TestCase):
    def run_ctl(self, *args):
        env = dict(os.environ, XDG_RUNTIME_DIR=tempfile.mkdtemp())
        return subprocess.run(["bash", CTL, *args], capture_output=True, text=True, env=env, timeout=30)

    def test_help(self):
        r = self.run_ctl("help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("deploy <branch>", r.stdout)

    def test_no_arguments_shows_help(self):
        self.assertEqual(self.run_ctl().returncode, 0)

    def test_unknown_command(self):
        r = self.run_ctl("frobnicate")
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown command", r.stdout)

    def test_deploy_needs_a_branch(self):
        self.assertEqual(self.run_ctl("deploy").returncode, 2)

    def test_ask_and_say_need_text(self):
        self.assertEqual(self.run_ctl("ask").returncode, 2)
        self.assertEqual(self.run_ctl("say").returncode, 2)

    def test_listen_rejects_bad_seconds(self):
        self.assertEqual(self.run_ctl("listen", "abc").returncode, 2)
        self.assertEqual(self.run_ctl("listen", "99").returncode, 2)

    def test_logs_rejects_non_number(self):
        self.assertEqual(self.run_ctl("logs", "x; rm -rf /").returncode, 2)


if __name__ == "__main__":
    unittest.main()
