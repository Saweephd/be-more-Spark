"""Uncle T's Big Adventure: intro, steering, traffic, cops, rage and the mall."""
import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

try:
    import pygame
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((800, 480))
    from core.games import common, uncle_t as ut
    from core import extras
    HAVE_PYGAME = True
except Exception:
    HAVE_PYGAME = False

DT = 1 / 60


@unittest.skipUnless(HAVE_PYGAME, "pygame not installed")
class UncleTTests(unittest.TestCase):
    def setUp(self):
        fd, self.scores = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(self.scores)
        self.canvas = pygame.Surface((common.W, common.H))

    def tearDown(self):
        if os.path.exists(self.scores):
            os.unlink(self.scores)

    def frames(self, game, inp, n, *held):
        for b in held:
            inp.down(b)
        for _ in range(n):
            game.step(DT, inp)
            game.render(self.canvas)
            inp.end_frame()
        for b in held:
            inp.up(b)

    def started(self):
        game = ut.make(seed=1, scores_path=self.scores)
        inp = common.Input()
        inp.down("a"); game.step(DT, inp); inp.end_frame(); inp.up("a")
        return game, inp

    def test_intro_plays_then_drive(self):
        game, inp = self.started()
        self.assertEqual(game.phase, "intro")
        self.assertEqual(game.music, "hottub")
        self.frames(game, inp, int(ut.INTRO_LEN * 60) + 5)
        self.assertEqual(game.phase, "drive")
        self.assertEqual(game.music, "uncle_t")
        self.assertTrue({"ring", "curse", "rev"} <= game.cue)

    def test_uncle_t_rambles_while_he_drives(self):
        for line in ("I had the first copy of Windows 95.", "I drove tanks in the Army.", "The Army could use guys like you.",
                     "This is all the fault of Bill Gates.", "Man, that Zuckerberg..."):
            self.assertIn(line, ut.RAMBLES)
        game, inp = self.started()
        self.frames(game, inp, int(ut.INTRO_LEN * 60) + 5)
        game.invuln = 9999.0
        heard = set()
        for _ in range(60 * 60):
            game.invuln = 9999.0
            game.step(DT, inp)
            if game.state != "play":
                break
            if game.ramble_t > 0:
                heard.add(game.ramble)
                self.assertIn(game.ramble, ut.RAMBLES)
        self.assertGreaterEqual(len(heard), 3)
        game.render(self.canvas)

    def test_intro_skips_and_replay_skips_it(self):
        game, inp = self.started()
        self.frames(game, inp, 30)
        self.frames(game, inp, 1, "a")
        self.assertEqual(game.phase, "drive")
        game.hits = ut.MAX_HITS - 1
        game.hit("cop")
        self.assertEqual(game.state, "over")
        self.assertEqual(game.end_reason, "BUSTED!")
        game.time += 2
        self.frames(game, inp, 1, "a")
        self.assertEqual((game.state, game.phase), ("play", "drive"))

    def drive(self):
        game, inp = self.started()
        game.begin_drive()
        game.cop_t = 999
        game.spawn_t = 999
        return game, inp

    def test_steering_speed_and_road_edges(self):
        game, inp = self.drive()
        x0 = game.px
        self.frames(game, inp, 20, "right")
        self.assertGreater(game.px, x0)
        self.frames(game, inp, 300, "left")
        self.assertGreaterEqual(game.px, ut.ROAD_L + 3)
        self.frames(game, inp, 120, "up")
        fast = game.speed
        self.frames(game, inp, 60, "down")
        self.assertLess(game.speed, fast)
        d0 = game.dist
        self.frames(game, inp, 60)
        self.assertGreater(game.dist, d0)

    def test_turbo_and_cooldown(self):
        game, inp = self.drive()
        self.frames(game, inp, 1, "a")
        self.assertGreater(game.turbo, 0)
        cool = game.turbo_cool
        self.frames(game, inp, 1, "a")
        self.assertLessEqual(game.turbo_cool, cool)

    def test_turbo_outruns_the_cops(self):
        game, inp = self.drive()
        lane = game.px + ut.CAR_W / 2
        game.cops.append({"x": game.px, "y": ut.H + 20, "w": ut.CAR_W, "h": ut.CAR_H, "crash": 0.0,
                          "spin": 0.0, "back": 0.0, "smart": 0.0, "v": ut.cop_speed(0)})
        game.cops[0]["x"] = lane - ut.CAR_W / 2 + 30   # beside, not behind, so he can't ram
        self.frames(game, inp, 20)                      # at cruise the cop gains
        self.assertLess(game.cops[0]["y"], ut.H + 20)
        self.frames(game, inp, 1, "a")
        self.frames(game, inp, int(ut.TURBO_LEN * 60) - 5, "up")
        self.assertEqual(game.cops, [])                 # left behind
        self.assertEqual(game.shaken, 1)

    def truck_ahead(self, game, kind="semi", lane=None):
        surf = game.semis[0] if kind == "semi" else game.traffic_cars[0]
        w, h = surf.get_size()
        lane = lane if lane is not None else game.px + ut.CAR_W / 2
        v = {"kind": kind, "surf": surf, "x": lane - w / 2, "y": ut.PLAYER_Y - h - 4, "w": w, "h": h, "v": 20, "shift": 0.0}
        game.traffic.append(v)
        return v

    def test_traffic_hit_costs_a_heart_then_invulnerable(self):
        game, inp = self.drive()
        self.truck_ahead(game)
        self.frames(game, inp, 30)
        self.assertEqual(game.hits, 1)
        self.assertGreater(game.invuln, 0)

    def test_horn_moves_a_car_over(self):
        game, inp = self.drive()
        v = self.truck_ahead(game, "car")
        v["y"] = ut.PLAYER_Y - 90
        self.frames(game, inp, 1, "b")
        self.assertNotEqual(v["shift"], 0)

    def cop(self, game, x, y):
        cp = {"x": x, "y": y, "w": ut.CAR_W, "h": ut.CAR_H, "crash": 0.0, "spin": 0.0, "back": 0.0, "smart": 0.0, "v": ut.cop_speed(0)}
        game.cops.append(cp)
        return cp

    def test_cop_crashes_into_traffic_and_he_taunts(self):
        game, inp = self.drive()
        cp = self.cop(game, 200 - ut.CAR_W / 2, 120)
        game.traffic.append({"kind": "semi", "surf": game.semis[0], "x": 188, "y": 60, "w": 24, "h": 82, "v": 0, "shift": 0.0})
        game.px = 110
        self.frames(game, inp, 3)
        self.assertTrue(cp["crash"] > 0)
        self.assertEqual(game.crashed, 1)
        self.assertGreater(game.taunt, 0)
        self.assertGreaterEqual(game.score, 250)

    def test_brake_check_crashes_the_cop(self):
        game, inp = self.drive()
        cp = self.cop(game, game.px, ut.PLAYER_Y + 20)
        self.frames(game, inp, 2, "down")
        self.assertTrue(cp["crash"] > 0)
        self.assertEqual(game.hits, 0)

    def test_cop_ram_hurts(self):
        game, inp = self.drive()
        self.cop(game, game.px + 4, ut.PLAYER_Y + 2)
        self.frames(game, inp, 2)
        self.assertEqual(game.hits, 1)

    def test_more_cops_and_rage_further_on(self):
        game, inp = self.drive()
        self.assertLess(game.rage, 0.1)
        game.dist = ut.TOTAL * 0.8
        self.assertGreater(game.rage, 0.7)
        game.cop_t = 0
        game.spawn_t = 999
        for _ in range(600):
            game.cop_t = min(game.cop_t, 0.0)
            self.frames(game, inp, 1)
        live = [c for c in game.cops if not c["crash"]]
        self.assertGreater(len(game.cops), 2)
        self.assertLessEqual(len(live), 6)

    def test_never_blocks_every_lane(self):
        game, inp = self.drive()
        game.spawn_t = 0
        for _ in range(3000):
            game.spawn_t = min(game.spawn_t, 0.05)
            game.invuln = 5
            game.step(DT, inp)
            band = [v for v in game.traffic if -60 < v["y"] < 40]
            lanes = {min(ut.LANES, key=lambda ln: abs(ln - (v["x"] + v["w"] / 2))) for v in band}
            self.assertLess(len(lanes), 4)

    def test_reaching_the_mall_wins(self):
        game, inp = self.drive()
        game.dist = ut.TOTAL - 1
        self.frames(game, inp, 2)
        self.assertEqual(game.phase, "arrive")
        self.frames(game, inp, 6 * 60 + 5)
        self.assertEqual(game.state, "over")
        self.assertTrue(game.win)
        self.assertGreater(game.last_score, 5000)

    def test_voices_fall_back_without_piper(self):
        voices = ut.build_voices()
        self.assertGreater(len(voices["curse"]), 2000)
        self.assertGreater(len(voices["taunt"]), 1000)

    def test_voice_request(self):
        for said in ("play uncle t", "play Uncle T's big adventure", "let's play the driving game"):
            self.assertEqual(extras.match_game(said), "uncle_t", said)


if __name__ == "__main__":
    unittest.main()
