"""The games run without a screen here (SDL dummy driver) and are driven frame by frame."""
import os
import random
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

try:
    import pygame
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((800, 480))
    from core.games import GAMES, angry_poppa, bmo_catch, common, launcher, mazee_run
    HAVE_PYGAME = True
except Exception:                                    # pygame missing on this machine
    HAVE_PYGAME = False

DT = 1 / 60


def press(game, inp, *buttons, frames=1):
    for _ in range(frames):
        for b in buttons:
            inp.down(b)
        game.step(DT, inp)
        inp.end_frame()
    for b in buttons:
        inp.up(b)


@unittest.skipUnless(HAVE_PYGAME, "pygame not installed")
class GameTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        os.unlink(self.tmp.name)
        self.scores = self.tmp.name
        self.canvas = pygame.Surface((common.W, common.H))

    def tearDown(self):
        if os.path.exists(self.scores):
            os.unlink(self.scores)

    def start(self, module, seed=1):
        game = module.make(seed=seed, scores_path=self.scores)
        inp = common.Input()
        self.assertEqual(game.state, "title")
        press(game, inp, "a")
        self.assertEqual(game.state, "play")
        return game, inp

    def test_every_game_survives_random_play_and_draws(self):
        rng = random.Random(7)
        for name in GAMES:
            module = __import__("core.games." + name, fromlist=["make"])
            game = module.make(seed=3, scores_path=self.scores)
            inp = common.Input()
            for frame in range(1500):
                for b in ("a", "b", "up", "down", "left", "right"):
                    if rng.random() < 0.08:
                        inp.down(b)
                    elif rng.random() < 0.2:
                        inp.up(b)
                game.step(DT, inp)
                if frame % 50 == 0:
                    game.render(self.canvas)
                inp.end_frame()
            res = game.result()
            self.assertEqual(res["game"], name)
            self.assertGreaterEqual(res["score"], 0)

    def test_scores_are_kept(self):
        self.assertEqual(common.save_score("x", 50, self.scores), (50, True))
        self.assertEqual(common.save_score("x", 20, self.scores), (50, False))
        self.assertEqual(common.save_score("x", 70, self.scores), (70, True))
        self.assertEqual(common.load_scores(self.scores), {"x": 70})
        self.assertEqual(common.load_scores("/nonexistent/scores.json"), {})

    def test_pause_and_resume(self):
        game, inp = self.start(mazee_run)
        press(game, inp, "start")
        self.assertEqual(game.state, "paused")
        dist = game.dist
        press(game, inp, frames=30)
        self.assertEqual(game.dist, dist)
        press(game, inp, "start")
        self.assertEqual(game.state, "play")

    # ----- Mazee Run -----
    def test_mazee_jump_clears_a_rock_and_standing_still_does_not(self):
        for jump in (True, False):
            game, inp = self.start(mazee_run)
            game.obstacles = [{"kind": "rock", "x": 150.0, "y": mazee_run.GROUND - 12, "w": 24, "h": 12}]
            game.next_spawn = 1e9
            game.next_bone = 1e9
            for _ in range(200):
                d = game.dog_rect()
                gap = game.obstacles[0]["x"] - d.right if game.obstacles else 999
                if jump and 0 < gap < 34 and game.on_ground:
                    inp.down("a")
                game.step(DT, inp)
                inp.end_frame()
                if game.state != "play":
                    break
            self.assertEqual(game.state, "play" if jump else "over", "jump=%s" % jump)

    def test_mazee_ducks_under_a_bird(self):
        game, inp = self.start(mazee_run)
        game.obstacles = [{"kind": "bird", "x": 150.0, "y": mazee_run.GROUND - 30, "w": 24, "h": 12}]
        game.next_spawn = 1e9
        game.next_bone = 1e9
        press(game, inp, "down", frames=120)
        self.assertEqual(game.state, "play")

    def test_mazee_treat_scores(self):
        game, inp = self.start(mazee_run)
        game.next_spawn = 1e9
        game.bones = [{"x": 100.0, "y": mazee_run.GROUND - 16}]
        press(game, inp, frames=60)
        self.assertEqual(game.treats, 1)
        self.assertGreaterEqual(game.score, 50)

    # ----- BMO Catch -----
    def test_catch_good_item_scores_and_spike_costs_a_life(self):
        game, inp = self.start(bmo_catch)
        game.spawn_in = 1e9
        game.items = [{"kind": "star", "x": game.x + 14, "y": bmo_catch.FLOOR - 60.0, "vy": 100.0}]
        press(game, inp, frames=60)
        self.assertEqual(game.score, 10)
        game.items = [{"kind": "spike", "x": game.x + 14, "y": bmo_catch.FLOOR - 60.0, "vy": 100.0}]
        press(game, inp, frames=60)
        self.assertEqual(game.lives, 2)
        self.assertEqual(game.score, 10)

    def test_catch_three_spikes_end_the_game(self):
        game, inp = self.start(bmo_catch)
        game.spawn_in = 1e9
        for _ in range(3):
            game.items = [{"kind": "spike", "x": game.x + 14, "y": bmo_catch.FLOOR - 40.0, "vy": 120.0}]
            press(game, inp, frames=40)
        self.assertEqual(game.state, "over")

    def test_catcher_stays_on_screen(self):
        game, inp = self.start(bmo_catch)
        game.spawn_in = 1e9
        press(game, inp, "left", frames=300)
        self.assertGreaterEqual(game.x, 0)
        press(game, inp, "right", frames=600)
        self.assertLessEqual(game.x + 52, common.W)

    # ----- Angry Poppa -----
    def quiet_poppa(self, stage=0):
        game, inp = self.start(angry_poppa)
        if stage:
            game.level_index = stage
            game.load_level()
        game.gnats = []
        for p in game.pots:
            p["timer"] = 1e9
        return game, inp

    def still_gnat(self, game, dx, dy, kind="gnat"):
        g = game.new_gnat(game.x + dx, game.y + dy, kind=kind)
        g["speed"] = 0
        return g

    def test_swatter_kills_a_gnat_in_reach_only(self):
        game, inp = self.quiet_poppa()
        near, far = self.still_gnat(game, 20, -30), self.still_gnat(game, 130, -30)
        game.gnats = [near, far]
        press(game, inp, "a")
        self.assertNotIn(near, game.gnats)
        self.assertIn(far, game.gnats)
        self.assertEqual(game.score, 10)

    def test_fat_gnat_takes_two_swats(self):
        game, inp = self.quiet_poppa()
        fat = self.still_gnat(game, 20, -30, kind="fat")
        game.gnats = [fat]
        press(game, inp, "a")
        self.assertIn(fat, game.gnats)
        press(game, inp, frames=25)
        press(game, inp, "a")
        self.assertNotIn(fat, game.gnats)
        self.assertEqual(game.score, 30)

    def test_spray_uses_pressure_and_pump_restores_it(self):
        game, inp = self.quiet_poppa()
        full = game.pressure
        press(game, inp, "b")
        self.assertEqual(game.pressure, full - 1)
        self.assertTrue(game.puffs)
        press(game, inp, frames=2)
        press(game, inp, "down")
        self.assertEqual(game.pressure, full)
        for _ in range(full + 2):
            press(game, inp, "b")
            press(game, inp, frames=2)
        self.assertEqual(game.pressure, 0)

    def test_spray_reaches_a_distant_gnat(self):
        game, inp = self.quiet_poppa()
        g = self.still_gnat(game, 70, -36)
        game.gnats = [g]
        press(game, inp, "b")
        press(game, inp, frames=40)
        self.assertNotIn(g, game.gnats)

    def test_gnat_touch_costs_a_heart(self):
        game, inp = self.quiet_poppa()
        game.gnats = [self.still_gnat(game, 0, -20)]
        press(game, inp, frames=3)
        self.assertEqual(game.hearts, 3)
        self.assertGreater(game.invuln, 0)

    def test_pickups(self):
        game, inp = self.quiet_poppa()
        game.hearts = 2
        game.pickups = [{"kind": "donut", "x": game.x, "y": game.y, "vy": 0.0}]
        press(game, inp, frames=2)
        self.assertEqual(game.hearts, 3)
        game.pickups = [{"kind": "soda", "x": game.x, "y": game.y, "vy": 0.0}]
        press(game, inp, frames=2)
        self.assertGreater(game.boost, 0)
        game.pickups = [{"kind": "printer", "x": game.x, "y": game.y, "vy": 0.0}]
        press(game, inp, frames=2)
        self.assertEqual(sum(game.up.values()), 1)

    def test_clearing_every_pot_opens_the_stairs_to_the_next_floor(self):
        game, inp = self.quiet_poppa()
        game.x = game.level["door"]
        press(game, inp, frames=2)
        self.assertEqual(game.level_index, 0, "stairs must stay shut while pots remain")
        for p in game.pots:
            game.hurt_pot(p, 9)
        press(game, inp, frames=2)
        self.assertEqual(game.level_index, 1)
        self.assertEqual(game.state, "play")
        self.assertEqual(game.level["name"], "Second floor")
        self.assertEqual(game.hearts, 5)

    def test_last_stage_needs_the_queen_beaten_too(self):
        game, inp = self.quiet_poppa(stage=len(angry_poppa.STAGES) - 1)
        self.assertIsNotNone(game.queen)
        game.queen["spawn"] = 1e9
        for p in game.pots:
            game.hurt_pot(p, 9)
        game.x = game.level["start"]
        press(game, inp, frames=2)
        self.assertFalse(game.cleared)
        game.hurt_queen(999)
        press(game, inp, frames=2)
        self.assertTrue(game.cleared)
        game.x = game.level["door"]
        press(game, inp, frames=2)
        self.assertEqual(game.state, "over")
        self.assertTrue(game.win)

    def test_every_stage_builds_and_gets_harder(self):
        last = None
        for i, st in enumerate(angry_poppa.STAGES):
            lv = angry_poppa.build_stage(i)
            self.assertEqual(len(lv["pots"]), st["pots"])
            self.assertGreater(lv["width"], 1200)
            self.assertGreaterEqual(len(lv["rooms"]), 4)
            for x, y in lv["pots"]:
                self.assertTrue(0 < x < lv["width"])
                self.assertGreater(abs(x - lv["start"]), 100)
                self.assertTrue(y == angry_poppa.FLOOR or any(px <= x <= px + pw and py == y for px, py, pw in lv["platforms"]))
            self.assertEqual(angry_poppa.build_stage(i)["pots"], lv["pots"], "stage layout must be the same every time")
            if last:
                self.assertGreater(st["speed"], last["speed"])
                self.assertGreaterEqual(st["pot_hp"], last["pot_hp"])
            last = st
        self.assertEqual([s["direction"] for s in angry_poppa.STAGES], [1, 1, 1, -1, -1])

    def test_can_stand_on_furniture(self):
        game, inp = self.quiet_poppa()
        px, py, pw = game.level["platforms"][0]
        game.x, game.y, game.vy = px + pw / 2, py - 30.0, 0.0
        press(game, inp, frames=40)
        self.assertEqual(game.y, py)
        self.assertTrue(game.on_ground)

    # ----- menu -----
    def test_menu_lists_and_picks(self):
        menu = launcher.Menu(scores_path=self.scores)
        self.assertEqual([n for n, _ in menu.games], list(GAMES))
        inp = common.Input()
        inp.down("down")
        menu.step(DT, inp)
        inp.end_frame()
        inp.up("down")
        inp.down("a")
        menu.step(DT, inp)
        self.assertEqual(menu.choice, "bmo_catch")
        menu.render(self.canvas)

    def test_run_loop_returns_a_result(self):
        screen = pygame.display.get_surface()
        res = common.run(mazee_run.make(seed=1, scores_path=self.scores), screen=screen, max_frames=5)
        self.assertEqual(res["game"], "mazee_run")
        self.assertFalse(res["played"])


if __name__ == "__main__":
    unittest.main()
