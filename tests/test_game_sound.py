"""Game sound: every effect and tune builds, games call real effect names, silence is safe."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from core.games import sound  # noqa: E402


class Recorder(sound.Silent):
    def __init__(self):
        self.played, self.tunes = [], []

    def play(self, name):
        assert name in sound._effects(), "unknown effect %s" % name
        self.played.append(name)

    def music(self, name):
        if name:
            assert name in sound.TUNES, "unknown tune %s" % name
            self.tunes.append(name)


class Building(unittest.TestCase):
    def test_notes(self):
        self.assertAlmostEqual(sound.note_freq("A4"), 440.0)
        self.assertAlmostEqual(sound.note_freq("A5"), 880.0)
        self.assertAlmostEqual(sound.note_freq("C4"), 261.63, places=1)
        self.assertAlmostEqual(sound.note_freq("Bb3"), sound.note_freq("A#3"))

    def test_every_effect(self):
        for name, make in sound._effects().items():
            w = make()
            self.assertGreater(len(w), 200, name)
            self.assertLessEqual(float(abs(w).max()), 1.0, name)

    def test_every_tune(self):
        for name in sound.TUNES:
            w = sound.render_tune(name)
            secs = len(w) / sound.RATE
            self.assertTrue(4 < secs < 50, (name, secs))
            self.assertLessEqual(float(abs(w).max()), 1.2, name)

    def test_silent_when_no_device(self):
        sound._player = None
        self.assertFalse(sound.get().enabled)
        sound.get().play("jump")
        sound.get().music("menu")


class GamesMakeSound(unittest.TestCase):
    def play(self, make, frames=2400, seed=3):
        import random
        from core.games import common as c
        game = make(seed=seed, scores_path=os.devnull)
        game.sound = Recorder()
        rng = random.Random(seed)
        inp = c.Input()
        inp.down("a")
        game.step(1 / 60, inp)
        inp.end_frame()
        inp.up("a")
        for _ in range(frames):
            for b in ("a", "b", "up", "down", "left", "right"):
                if rng.random() < 0.08:
                    (inp.down if b not in inp.held else inp.up)(b)
            game.step(1 / 60, inp)
            inp.end_frame()
            if game.state == "over":
                break
        return game.sound

    def test_each_game(self):
        from core.games import angry_poppa, bmo_catch, mazee_run
        for mod, expect in ((mazee_run, {"start", "jump"}), (bmo_catch, {"start"}), (angry_poppa, {"start", "swat", "jump"})):
            rec = self.play(mod.make)
            self.assertTrue(expect <= set(rec.played), (mod.__name__, set(rec.played)))
            self.assertEqual(rec.tunes[0], mod.make().music)


if __name__ == "__main__":
    unittest.main()
