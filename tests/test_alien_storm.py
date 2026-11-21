"""Alien Storm: Tom Cat Alley. Flight rules, the exact lines, the cutscenes and the landing."""
import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("BMO_GAME_SOUND", "0")

try:
    import pygame
    from core.games import common, sound
    from core.games.alien_storm import game as G, lines, scenes
    from core import extras
    OK = True
except ImportError:  # pragma: no cover
    OK = False


def new(scenes_on=False, stage=0, mode=1):
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((800, 480))
    g = G.AlienStorm(seed=3, scores_path=os.path.join(tempfile.mkdtemp(), "s.json"))
    g.scenes = scenes_on
    g.unlocked, g.level_choice, g.mode = 4, stage, mode
    inp = common.Input()
    inp.pressed = {"a"}
    g.step(1 / 60, inp)
    inp.pressed = set()
    return g, inp


def run(g, inp, seconds):
    for _ in range(int(seconds * 60)):
        g.step(1 / 60, inp)
        inp.pressed = set()


@unittest.skipUnless(OK, "pygame not installed")
class Flight(unittest.TestCase):
    def test_exact_lines(self):
        self.assertEqual(lines.HIT_KJ, "Come on man, do some of that pilot ish!")
        self.assertEqual(lines.FLEX_ALEX, "I make this ish look good.")
        self.assertEqual(lines.FLEX_KJ, "That's some cap, twin.")

    def test_every_hit_gets_kjs_line(self):
        g, inp = new()
        j = g.jets[0]
        for _ in range(3):
            g.talk.clear()
            j.safe = 0
            g.hurt(j, 5)
            self.assertEqual(g.talk[0][:3], ["kj", "alarm", lines.HIT_KJ])
        g.say("kj", "grin", "Nothing but net!")          # a quip never replaces it
        self.assertEqual(g.talk[0][2], lines.HIT_KJ)

    def test_guns_fire_by_themselves(self):
        g, inp = new()
        g.spawn("bomber", 200, 60)
        run(g, inp, 0.5)
        self.assertTrue(g.shots)

    def test_tap_fires_heat_seeker_and_pylon_empties(self):
        g, inp = new()
        g.spawn("bomber", 200, 60)
        j = g.jets[0]
        before = j.heat
        inp.held = {"a"}
        run(g, inp, 0.1)
        inp.held = set()
        run(g, inp, 0.05)
        self.assertEqual(j.heat, before - 1)
        self.assertEqual(g.rockets[0]["kind"], "heat")

    def test_hold_locks_up_to_four_then_launches(self):
        g, inp = new()
        g.waves = []
        for i in range(6):
            g.spawn("bomber", 60 + i * 50, 40)
        inp.held = {"a"}
        run(g, inp, 1.6)
        self.assertEqual(len(g.jets[0].locks), G.MAX_LOCKS)
        inp.held = set()
        run(g, inp, 0.05)
        self.assertEqual(len([m for m in g.rockets if m["kind"] == "radar"]), 4)
        self.assertGreater(g.jets[0].reload, 0)

    def test_loop_makes_the_jet_untouchable(self):
        g, inp = new()
        j = g.jets[0]
        j.safe = 0
        inp.pressed = {"b"}
        run(g, inp, 0.1)
        self.assertTrue(j.looping)
        hp = j.hp
        g.hurt(j, 50)
        self.assertEqual(j.hp, hp)

    def test_second_pad_brings_the_second_crew(self):
        g, inp = new()
        inp.p2 = common.Input()
        inp.p2.pressed = {"a"}
        run(g, inp, 0.1)
        self.assertEqual(len(g.jets), 2)
        self.assertEqual(g.jets[1].crew["pilot"], "stephen")
        g.jets[1].safe = 0
        g.hurt(g.jets[1], 5)
        self.assertEqual(g.talk[1][0], "heather")

    def test_each_stage_reaches_its_boss_and_draws(self):
        canvas = pygame.Surface((400, 240))
        for stage in range(4):
            g, inp = new(stage=stage)
            g.waves, g.t = [], G.STAGE_LEN + 1
            run(g, inp, 5)
            self.assertEqual(g.phase, "boss")
            self.assertEqual(g.boss["kind"], G.STAGES[stage]["boss"])
            for j in g.jets:
                j.safe = 99
            for _ in range(600):
                g.step(1 / 60, inp)
                g.render(canvas)
            g.damage(g.boss, 99999)
            self.assertEqual(g.phase, "clear")
            run(g, inp, 4)
            self.assertTrue(g.stage == stage + 1 or g.state == "over")

    def test_win_after_the_last_stage(self):
        g, inp = new(stage=3)
        g.kill_boss() if g.boss else None
        g.phase, g.phase_t, g.bx, g.by = "clear", 0.0, 200, 60
        run(g, inp, 4)
        self.assertEqual(g.state, "over")
        self.assertTrue(g.win)

    def test_voice_names(self):
        for said in ("play alien storm", "play tom cat alley", "play tomcat alley", "let's play the jet game"):
            self.assertEqual(extras.match_game(said), "alien_storm", said)

    def test_sounds_and_music_build(self):
        fx = sound._effects()
        for name in ("as_vulcan", "as_heat", "as_radar", "as_lock", "as_boom", "as_boom_big", "as_broadside", "as_catapult", "as_wire"):
            w = fx[name]()
            self.assertLessEqual(float(abs(w).max()), 1.0, name)
        for tune in ("as_anthem", "as_fleet", "as_stage1", "as_stage2", "as_stage3", "as_stage4", "as_boss"):
            w = sound.render_tune(tune)
            self.assertLessEqual(float(abs(w).max()), 1.0, tune)


@unittest.skipUnless(OK, "pygame not installed")
class Scenes(unittest.TestCase):
    def all_scenes(self, g):
        yield scenes.takeoff(g, first=True)
        yield scenes.takeoff(g)
        for s in range(4):
            yield scenes.set_piece(g, s)
        yield scenes.ending(g)

    def test_every_cutscene_has_the_exchange_and_draws(self):
        g, inp = new()
        screen = pygame.display.get_surface()
        for sc in self.all_scenes(g):
            said = [s[3] for shot in sc.shots for s in shot.get("say", ())]
            self.assertIn(lines.FLEX_ALEX, said)
            self.assertEqual(said[said.index(lines.FLEX_ALEX) + 1], lines.FLEX_KJ)
            for i, shot in enumerate(sc.shots):
                sc.i, t = i, 0.0
                while t < shot["dur"]:
                    sc.t = t
                    sc.draw(screen)
                    t += 0.5

    def test_requested_lines_are_all_spoken_somewhere(self):
        g, inp = new()
        said = " | ".join(s[3] for sc in self.all_scenes(g) for shot in sc.shots for s in shot.get("say", ()))
        for line in (lines.IMPROV_ALEX, lines.KILL_KJ[0], lines.KILL_KJ[1], lines.SCREEN_TIME_HEATHER,
                     lines.SCREEN_TIME_STEPHEN, lines.REEL_HEATHER, lines.OLD_MAN_STEPHEN):
            self.assertIn(line, said)

    def test_scenes_can_be_skipped(self):
        g, inp = new(scenes_on=True)
        self.assertIsNotNone(g.scene)
        inp.pressed = {"b"}
        g.step(1 / 60, inp)
        self.assertIsNone(g.scene)
        self.assertEqual(g.phase, "flight")

    def land(self, g, inp, skill):
        L = g.landing
        canvas = pygame.Surface((400, 240))
        for _ in range(60 * 60):
            inp.held = set()
            if L.state == "approach":
                off, ge = L.x - L.target_x(), L.alt - L.d + skill
                if off > 3:
                    inp.held.add("left")
                elif off < -3:
                    inp.held.add("right")
                inp.held.add("a" if ge < 0 else "b")
            if L.update(1 / 60, inp):
                return L
            L.draw(canvas)
            L.draw_hd(pygame.display.get_surface())
        self.fail("landing never finished")

    def test_a_good_approach_catches_the_three_wire(self):
        g, inp = new()
        g.landing = scenes.Landing(g)
        L = self.land(g, inp, 0.0)
        self.assertEqual(L.grade, 3)
        self.assertEqual(g.grades, [3])

    def test_a_low_approach_gets_shouted_at(self):
        g, inp = new()
        g.landing = scenes.Landing(g)
        L = self.land(g, inp, 0.12)
        self.assertIn(L.grade, (1, 2))

    def test_landing_leads_to_the_next_stage_and_then_the_ending(self):
        g, inp = new(scenes_on=True)
        g.scene = None
        g.landing = scenes.Landing(g)
        g.landing.after()
        self.assertEqual(g.stage, 1)
        self.assertIsNotNone(g.scene)
        g.stage = 3
        g.landing = scenes.Landing(g)
        g.landing.after()
        g.scene.after()
        self.assertTrue(g.win)
        self.assertEqual(g.state, "over")


if __name__ == "__main__":
    unittest.main()
