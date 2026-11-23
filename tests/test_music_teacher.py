"""Music Teacher's Pet: the lessons add up, right notes earn checks, wrong ones bring the ruler."""
import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("BMO_GAME_SOUND", "0")

try:
    import pygame
    from core import extras
    from core.games import GAMES, common, sound
    from core.games.music_teacher import game as G, songs
    OK = True
except ImportError:  # pragma: no cover
    OK = False


def new(mode=0, lesson=0):
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((800, 480))
    g = G.MusicTeacher(seed=2, scores_path=os.path.join(tempfile.mkdtemp(), "s.json"))
    g.unlocked, g.level_choice, g.mode = 4, lesson, mode
    inp = common.Input()
    for _ in range(2):                       # off the title, then past the lesson card
        inp.pressed = {"a"}
        g.step(0.5, inp)
    inp.pressed = set()
    return g, inp


def play(g, inp, seconds, skip=()):
    """Play every note on time, except the numbered ones in `skip`."""
    count = 0
    for _ in range(int(seconds * 60)):
        inp.pressed = set()
        for n in g.notes:
            if n["state"] is None and 0 <= g.clock - n["t"] < 0.03 and not n.get("left"):
                count += 1
                if count in skip:
                    n["left"] = True
                else:
                    inp.pressed.add(G.BUTTONS[n["lane"]])
        g.step(1 / 60, inp)
        if g.phase != "song":
            break
    inp.pressed = set()


@unittest.skipUnless(OK, "pygame not installed")
class TestMusicTeacher(unittest.TestCase):
    def test_every_bar_adds_up_and_hands_match(self):
        self.assertEqual(len(songs.SONGS), 4)
        for s in songs.SONGS:
            self.assertEqual(len(s["rh"]), len(s["lh"]), s["key"])
            rh, lh = songs.hands(s)                       # raises if any bar is the wrong length
            self.assertTrue(rh and lh)
            self.assertTrue(25 < songs.length(s) < 95, s["key"])

    def test_lessons_start_with_the_right_notes(self):
        first = lambda i, n: [max(m) for _, m, _ in songs.hands(songs.SONGS[i])[0][:n]]
        self.assertEqual(first(0, 4), [songs.midi(x) for x in ("F5", "Db5", "Ab4", "Bb4")])
        self.assertEqual(first(1, 6), [songs.midi(x) for x in ("E5", "D#5", "E5", "D#5", "E5", "B4")])
        self.assertEqual(first(2, 5), [songs.midi(x) for x in ("B4", "A4", "G#4", "A4", "C5")])
        self.assertEqual(first(3, 4), [songs.midi(x) for x in ("G#4", "A4", "G#4", "G4")])

    def test_charts_fit_the_lanes_and_harder_levels_ask_for_more(self):
        for s in songs.SONGS:
            rh, _ = songs.hands(s)
            counts = []
            for lanes, gap, _, _, _ in G.MODES:
                notes, auto = G.chart(rh, lanes, gap)
                self.assertEqual(len(notes) + len(auto), len(rh))
                self.assertTrue(all(0 <= n["lane"] < lanes for n in notes))
                gaps = [b["t"] - a["t"] for a, b in zip(notes, notes[1:])]
                self.assertTrue(min(gaps) >= gap - 1e-6)
                counts.append(len(notes))
            self.assertTrue(counts[0] <= counts[1] <= counts[2])
            self.assertEqual(counts[2], len(rh))

    def test_a_perfect_lesson_makes_you_teachers_pet(self):
        g, inp = new()
        self.assertEqual(g.phase, "song")
        play(g, inp, 120)
        self.assertEqual(g.phase, "report")
        self.assertEqual((g.percent(), g.misses, g.slips), (100, 0, 0))
        self.assertEqual(g.grade, "Teacher's Pet")
        self.assertEqual(g.hits, len(g.notes))
        self.assertEqual(len(g.checks) + g.boards * G.CHECK_COLS * G.CHECK_ROWS, g.hits)
        inp.pressed = {"a"}
        g.step(1.1, inp); g.step(0.1, inp)
        self.assertEqual((g.lesson, g.phase), (1, "intro"))

    def test_wrong_and_missed_notes_bring_the_ruler(self):
        g, inp = new(mode=1)
        while g.clock < 0:
            g.step(1 / 60, inp)
        inp.pressed = {"b"} if g.lanes > 5 else {G.BUTTONS[(g.notes[0]["lane"] + 2) % g.lanes]}
        g.step(1 / 60, inp)
        self.assertEqual((g.slips, g.pose, g.combo), (1, "strike", 0))
        self.assertGreater(g.shake, 0)
        play(g, inp, 20, skip=(3,))
        self.assertGreaterEqual(g.misses, 1)
        self.assertLess(g.percent(), 100)

    def test_a_failed_recital_is_taken_again_but_practice_always_moves_on(self):
        g, inp = new(mode=1)
        for _ in range(int(100 * 30)):
            g.step(1 / 30, inp)
            if g.phase == "report":
                break
        self.assertEqual((g.phase, g.passed, g.grade), ("report", False, "See me after class"))
        inp.pressed = {"a"}
        g.step(1.1, inp); g.step(0.1, inp)
        self.assertEqual((g.lesson, g.phase, g.score), (0, "intro", 0))
        self.assertEqual(G.grade_for(100), "Teacher's Pet")
        self.assertEqual(G.grade_for(96), "A+")
        self.assertEqual(G.grade_for(59), "See me after class")

    def test_finishing_the_last_lesson_wins(self):
        g, inp = new(mode=0, lesson=3)
        play(g, inp, 60)
        self.assertEqual(g.phase, "report")
        inp.pressed = {"a"}
        g.step(1.1, inp); g.step(0.1, inp)
        self.assertEqual((g.state, g.win), ("over", True))
        self.assertGreater(g.result()["score"], 0)

    def test_draws_in_every_state_and_runs_in_the_real_loop(self):
        g = G.MusicTeacher(seed=1, scores_path=os.path.join(tempfile.mkdtemp(), "s.json"))
        screen = pygame.display.set_mode((800, 480))
        res = common.run(g, screen=screen, max_frames=20)        # the title, as the menu starts it
        self.assertEqual(res["game"], "music_teacher")
        g, inp = new(mode=2)
        canvas = pygame.Surface((common.W, common.H))
        for _ in range(240):
            g.step(1 / 60, inp)
            g.render(canvas); g.render_hd(screen)
        g.finish_lesson()
        g.render(canvas); g.render_hd(screen)

    def test_piano_voice_and_registration(self):
        wave = sound.piano(440.0, 0.5, 0.6)
        self.assertEqual(len(wave), int(0.5 * sound.RATE))
        self.assertLess(float(abs(wave).max()), 1.0)
        self.assertGreater(float(abs(wave[:2000]).max()), 3 * float(abs(wave[-2000:]).max()))
        self.assertIn("music_teacher", GAMES)
        for said in ("play music teacher's pet", "play teachers pet", "let's play the piano game", "start heather's game"):
            self.assertEqual(extras.match_game(said), "music_teacher", said)
        self.assertEqual(extras.match_game("play alien storm"), "alien_storm")


if __name__ == "__main__":
    unittest.main()
