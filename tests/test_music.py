"""Song names, stop and list phrases, pictures, and the helper tools."""
import json
import os
import tempfile
import unittest

from core import music_library as ml
from ops import bmo_battery, bmo_buttons, bmo_music, bmo_saver


def library(*files, names=None):
    folder = tempfile.mkdtemp()
    for f in files:
        open(os.path.join(folder, f), "wb").close()
    names_file = os.path.join(folder, "library.json")
    if names:
        with open(names_file, "w") as fh:
            json.dump(names, fh)
    return ml.tracks(folder, names_file)


class Names(unittest.TestCase):
    def setUp(self):
        self.lib = library(
            "bmo_jam.wav", "bmo_adventure.wav", "robot_march.wav", "starry_night.wav", "victory_fanfare.wav",
            "adventure_time_theme.wav", "bacon_pancakes.wav", "notes.txt",
            names={"adventure_time_theme.wav": {"title": "Adventure Time Theme Song", "aliases": ["the theme song", "adventure time"]},
                   "bacon_pancakes": {"title": "Making Bacon Pancakes", "aliases": ["bacon pancakes", "the pancake song"]}})

    def pick(self, said):
        hit = ml.match_track(said, self.lib)
        return hit["file"] if hit else None

    def test_titles(self):
        titles = {t["file"]: t["title"] for t in self.lib}
        self.assertEqual(len(self.lib), 7)
        self.assertEqual(titles["bmo_jam.wav"], "BMO Jam")
        self.assertEqual(titles["bacon_pancakes.wav"], "Making Bacon Pancakes")

    def test_asked_by_name(self):
        cases = {
            "Play the Adventure Time theme song.": "adventure_time_theme.wav",
            "play adventure time": "adventure_time_theme.wav",
            "Hey can you play making bacon pancakes": "bacon_pancakes.wav",
            "sing bacon pancakes": "bacon_pancakes.wav",
            "play the pancake song please": "bacon_pancakes.wav",
            "play robot march": "robot_march.wav",
            "put on starry night": "starry_night.wav",
            "play the victory fanfare": "victory_fanfare.wav",
            "play BMO jam": "bmo_jam.wav",
        }
        for said, want in cases.items():
            self.assertEqual(self.pick(said), want, said)

    def test_no_song_named(self):
        for said in ("play some music", "play a song", "sing me a song", "what time is it", "play mazee run",
                     "tell me about pancakes", "I love adventure time", ""):
            self.assertIsNone(self.pick(said), said)

    def test_stop_and_list(self):
        for said in ("stop the music", "Stop music.", "turn off the music", "stop playing", "stop the song", "stop singing"):
            self.assertTrue(ml.match_stop(said), said)
        for said in ("stop", "play music", "what stops a train", "shut down"):
            self.assertFalse(ml.match_stop(said), said)
        for said in ("what songs do you know", "which songs can you play", "list your songs", "what can you sing"):
            self.assertTrue(ml.match_list(said), said)
        self.assertFalse(ml.match_list("play a song"))
        self.assertIn("7 songs", ml.spoken_list(self.lib))
        self.assertIn("no songs", ml.spoken_list([]))


class Pictures(unittest.TestCase):
    def test_own_folder_wins(self):
        slides = tempfile.mkdtemp()
        for f in ("a.jpg", "b.PNG", "readme.txt", ".hidden.jpg"):
            open(os.path.join(slides, f), "wb").close()
        os.mkdir(os.path.join(slides, "bacon_pancakes"))
        open(os.path.join(slides, "bacon_pancakes", "p.jpg"), "wb").close()
        self.assertEqual(len(ml.slides_for(None, slides)), 2)
        self.assertEqual(len(ml.slides_for({"file": "robot_march.wav"}, slides)), 2)
        own = ml.slides_for({"file": "bacon_pancakes.wav"}, slides)
        self.assertEqual([os.path.basename(p) for p in own], ["p.jpg"])
        self.assertEqual(ml.slides_for(None, os.path.join(slides, "missing")), [])


class Screensaver(unittest.TestCase):
    def test_import_shrinks_pictures_to_the_screen(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as dst:
            os.makedirs(os.path.join(src, "Land of Ooo"))
            Image.new("RGB", (3840, 2160), (40, 120, 200)).save(os.path.join(src, "Land of Ooo", "Tree Fort.png"))
            Image.new("RGB", (600, 900), (200, 60, 40)).save(os.path.join(src, "candy.jpg"))
            open(os.path.join(src, "notes.txt"), "w").write("not a picture")
            self.assertEqual(bmo_saver.cmd_import(src, dst), 2)
            pics = ml.screensaver_pictures(dst)
            self.assertEqual([os.path.basename(p) for p in pics], ["candy.jpg", "land_of_ooo_tree_fort.jpg"])
            for p in pics:
                self.assertEqual(Image.open(p).size, (800, 480))

    def test_no_folder_means_no_pictures(self):
        self.assertEqual(ml.screensaver_pictures("/nonexistent/folder"), [])


class Tools(unittest.TestCase):
    def test_safe_name(self):
        self.assertEqual(bmo_music.safe_name("/x/Making Bacon Pancakes (Full).mp3"), "making_bacon_pancakes_full")

    def test_battery_decode(self):
        volts, percent = bmo_battery.decode(bytes([0xD0, 0x00]), bytes([87, 128]))
        self.assertAlmostEqual(volts, 4.16, places=2)
        self.assertEqual(percent, 87.5)

    def test_button_summary(self):
        self.assertEqual(bmo_buttons.summary(set(bmo_buttons.NAMES)), "buttons: all 7 seen")
        self.assertIn("6 of 7", bmo_buttons.summary(set(bmo_buttons.NAMES) - {57}))
        self.assertEqual(len(bmo_buttons.NAMES), 7)


class VoicePath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        import types
        for name in ("ddgs", "duckduckgo_search"):
            if name not in sys.modules:
                try:
                    __import__(name)
                except Exception:
                    stub = types.ModuleType(name)
                    stub.DDGS = object
                    sys.modules[name] = stub
        from core.llm import Brain
        cls.Brain = Brain

    def test_song_and_stop(self):
        folder = tempfile.mkdtemp()
        open(os.path.join(folder, "robot_march.wav"), "wb").close()
        old = ml.MUSIC_DIR
        ml.MUSIC_DIR = folder
        try:
            out = list(self.Brain().stream_think("play robot march"))
            self.assertEqual(json.loads(out[-1]), {"action": "play_music", "file": "robot_march.wav"})
            out = list(self.Brain().stream_think("stop the music"))
            self.assertEqual(json.loads(out[-1]), {"action": "stop_music"})
            out = list(self.Brain().stream_think("what songs do you know"))
            self.assertIn("Robot March", out[0])
            out = list(self.Brain().stream_think("play some music"))
            self.assertEqual(json.loads(out[-1]), {"action": "play_music"})
        finally:
            ml.MUSIC_DIR = old


if __name__ == "__main__":
    unittest.main()
