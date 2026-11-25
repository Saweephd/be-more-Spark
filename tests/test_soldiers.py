"""Soldiers vs Spies: selection, orders, drop, fighting, bosses, unlocks, co-op; plus gamepad input."""
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
    from core.games import common, soldiers_vs_spies as sv
    from core import extras
    HAVE_PYGAME = True
except Exception:
    HAVE_PYGAME = False

DT = 1 / 60


@unittest.skipUnless(HAVE_PYGAME, "pygame not installed")
class SoldiersTests(unittest.TestCase):
    def setUp(self):
        fd, self.scores = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(self.scores)
        self.canvas = pygame.Surface((common.W, common.H))

    def tearDown(self):
        if os.path.exists(self.scores):
            os.unlink(self.scores)

    def frames(self, g, inp, n, *held):
        for b in held:
            inp.down(b)
        for _ in range(n):
            g.step(DT, inp)
            g.render(self.canvas)
            inp.end_frame()
            if inp.p2 is not None:
                inp.p2.end_frame()
        for b in held:
            inp.up(b)

    def to_level(self, two=False, choose_felix=False):
        g = sv.make(seed=1, scores_path=self.scores)
        inp = common.Input()
        if two:
            inp.p2 = common.Input()
        self.frames(g, inp, 1, "a")                      # title -> select
        self.assertEqual(g.phase, "select")
        if choose_felix:
            self.frames(g, inp, 1, "right")
        if two:
            inp.p2.down("a"); g.step(DT, inp); inp.p2.end_frame(); inp.p2.up("a"); inp.end_frame()
        self.frames(g, inp, 30)
        self.frames(g, inp, 1, "a")
        self.assertEqual(g.phase, "briefing")
        self.frames(g, inp, 70)
        self.frames(g, inp, 1, "a")
        self.assertEqual(g.phase, "plane")
        self.frames(g, inp, 220)
        self.assertIn(g.phase, ("drop", "play"))
        self.frames(g, inp, 60 * 6)
        self.assertEqual(g.phase, "play")
        return g, inp

    def test_full_opening_and_landing(self):
        g, inp = self.to_level()
        p = g.players[0]
        self.assertEqual(p["who"], "miles")
        self.assertFalse(p["chute"])
        self.assertTrue(p["on"])

    def test_choose_felix_and_two_players(self):
        g, inp = self.to_level(two=True, choose_felix=True)
        self.assertEqual([p["who"] for p in g.players], ["felix", "miles"])
        self.assertGreater(g.players[0]["hero"]["height"], 0)
        self.assertGreater(sv.HEROES["miles"]["height"], sv.HEROES["felix"]["height"])

    def test_run_jump_and_fire(self):
        g, inp = self.to_level()
        p = g.players[0]
        x0 = p["x"]
        self.frames(g, inp, 30, "right")
        self.assertGreater(p["x"], x0)
        self.frames(g, inp, 1, "a")
        self.assertFalse(p["on"])
        self.frames(g, inp, 60)
        self.assertTrue(p["on"])
        self.frames(g, inp, 1, "b")
        self.assertTrue(g.bullets)
        self.frames(g, inp, 20)
        g.bullets = []
        self.frames(g, inp, 1, "b", "up")
        self.assertLess(g.bullets[-1]["vy"], 0)

    def test_shooting_an_enemy_scores(self):
        g, inp = self.to_level()
        p = g.players[0]
        g.add_enemy("shooter", p["x"] + 60, sv.GROUND)
        g.enemies[-1]["cool"] = 99
        before = g.score
        for _ in range(40):
            self.frames(g, inp, 1, "b")
            self.frames(g, inp, 1)
        self.assertGreater(g.score, before)

    def test_spread_shot_pickup(self):
        g, inp = self.to_level()
        p = g.players[0]
        g.pickups.append({"x": p["x"] + 10, "y": p["y"] - 12, "kind": "S", "t": 0.0})
        self.frames(g, inp, 10, "right")
        self.assertEqual(p["weapon"], "S")
        g.bullets = []
        self.frames(g, inp, 1, "b")
        self.assertEqual(len(g.bullets), 5)

    def test_getting_hit_costs_a_life_and_respawns_by_chute(self):
        g, inp = self.to_level()
        p = g.players[0]
        p["inv"] = 0
        g.kill_player(p)
        self.assertEqual(p["lives"], 2)
        self.frames(g, inp, 100)
        self.assertTrue(p["chute"] or p["on"])
        self.assertGreater(p["inv"], 0)

    def test_respawn_is_fair(self):
        g, inp = self.to_level()
        p = g.players[0]
        p["inv"] = 0
        g.add_enemy("runner", p["x"] + 60, sv.GROUND)
        g.ebullets.append({"x": p["x"] + 30, "y": p["y"] - 12, "vx": -50.0, "vy": 0.0, "g": 0.0})
        g.kill_player(p)
        self.assertEqual(g.ebullets, [])                       # enemy fire cleared
        self.assertFalse([e for e in g.enemies if e["kind"] == "runner" and e["hp"] > 0 and abs(e["x"] - p["x"]) < 140])
        g.add_enemy("shooter", p["x"] + 80, sv.GROUND)
        g.enemies[-1]["cool"] = 0
        self.frames(g, inp, 90)                                # dead, then parachuting
        self.assertTrue(p["chute"])
        self.assertEqual(g.ebullets, [])                       # nobody shoots at a parachute
        self.frames(g, inp, 150)
        self.assertTrue(p["on"])
        self.assertGreater(p["inv"], 1.0)                      # safe time starts on landing
        g.add_enemy("runner", p["x"] + 150, sv.GROUND)
        e = g.enemies[-1]
        g.update_enemies(DT)
        face = e["face"]
        p["x"] = e["x"] + 40 * face                            # jump past him: he keeps going
        g.update_enemies(DT)
        self.assertEqual(e["face"], face)

    def test_game_over_when_everyone_is_out(self):
        g, inp = self.to_level()
        p = g.players[0]
        for _ in range(3):
            p["inv"] = 0
            g.kill_player(p)
            self.frames(g, inp, 100)
        self.assertEqual(g.state, "over")

    def test_boss_fight_clears_and_unlocks_next_mission(self):
        g, inp = self.to_level()
        g.cam = g.length - common.W
        g.players[0]["x"] = g.cam + 100
        self.frames(g, inp, 2)
        self.assertIsNotNone(g.boss)
        self.assertEqual(g.music, "soldiers_boss")
        g.boss["hp"] = 0
        g.check_boss_dead()
        self.assertEqual(g.phase, "clear")
        self.assertEqual(common.load_scores(self.scores)[sv.UNLOCK_KEY], 2)
        self.frames(g, inp, 60 * 4)
        self.assertEqual(g.phase, "plane")
        self.assertEqual(g.level, 1)

    def test_every_boss_can_be_beaten_and_last_one_wins(self):
        g, inp = self.to_level()
        for lvl in range(5):
            g.level = lvl
            g.begin_level()
            self.frames(g, inp, 60 * 6)
            g.cam = g.length - common.W
            g.players[0]["x"] = g.cam + 60
            g.players[0]["inv"] = 999
            self.frames(g, inp, 120)
            self.assertIsNotNone(g.boss, lvl)
            if g.boss["kind"] == "bunker":
                g.boss["ports"] = [0, 0, 0]
            g.boss["hp"] = 0
            g.check_boss_dead()
            self.frames(g, inp, 60 * 4)
        self.assertEqual(g.phase, "victory")
        self.frames(g, inp, 60 * 6)
        self.assertEqual(g.state, "over")
        self.assertTrue(g.win)

    def test_unlocked_missions_can_be_started(self):
        common.save_score(sv.UNLOCK_KEY, 3, self.scores)
        g = sv.make(seed=1, scores_path=self.scores)
        self.assertEqual(g.unlocked, 3)
        inp = common.Input()
        self.frames(g, inp, 1, "a")
        self.assertEqual(g.start_level, 1)                 # the first level is always the one offered
        self.frames(g, inp, 1, "up")
        self.frames(g, inp, 1, "up")
        self.assertEqual(g.start_level, 3)
        self.frames(g, inp, 1, "up")                       # but never past what has been reached
        self.assertEqual(g.start_level, 3)
        self.frames(g, inp, 1, "down")
        self.assertEqual(g.start_level, 2)

    def test_player_two_can_join_mid_mission(self):
        g, inp = self.to_level()
        inp.p2 = common.Input()
        inp.p2.down("a"); g.step(DT, inp); inp.p2.up("a"); inp.p2.end_frame(); inp.end_frame()
        self.assertEqual(len(g.players), 2)
        self.assertEqual(g.players[1]["who"], "felix")

    def test_special_enemies_appear(self):
        for lvl, kind in ((0, "drone"), (1, "jeep"), (3, "sled"), (4, "boat")):
            g = sv.make(seed=1, scores_path=self.scores)
            g.level = lvl
            g.players = [g.new_player("miles", 0)]
            g.begin_level()
            self.assertTrue(any(k == kind for _, k, _ in g.spawns), (lvl, kind))

    def test_voice(self):
        self.assertEqual(extras.match_game("play soldiers vs spies"), "soldiers_vs_spies")


@unittest.skipUnless(HAVE_PYGAME, "pygame not installed")
class PadTests(unittest.TestCase):
    class FakeJoy:
        def __init__(self, iid):
            self.iid = iid

        def init(self):
            pass

        def get_instance_id(self):
            return self.iid

    def pads(self):
        pads = common.Pads({"a": [0], "b": [1], "start": [7]})
        for iid in (10, 11):
            pads.sticks[iid] = (len(pads.sticks), self.FakeJoy(iid))
        return pads

    def ev(self, kind, **kw):
        return pygame.event.Event(kind, kw)

    def test_buttons_hat_and_stick(self):
        pads = self.pads()
        p1, p2 = common.Input(), common.Input()
        route = lambda slot: [p1] if slot == 0 else [p2]
        pads.handle(self.ev(pygame.JOYBUTTONDOWN, instance_id=10, button=0), route)
        self.assertIn("a", p1.held)
        pads.handle(self.ev(pygame.JOYBUTTONUP, instance_id=10, button=0), route)
        self.assertNotIn("a", p1.held)
        pads.handle(self.ev(pygame.JOYHATMOTION, instance_id=11, hat=0, value=(-1, 1)), route)
        self.assertEqual(p2.held, {"left", "up"})
        pads.handle(self.ev(pygame.JOYHATMOTION, instance_id=11, hat=0, value=(0, 0)), route)
        self.assertEqual(p2.held, set())
        pads.handle(self.ev(pygame.JOYAXISMOTION, instance_id=10, axis=0, value=0.9), route)
        self.assertIn("right", p1.held)
        pads.handle(self.ev(pygame.JOYAXISMOTION, instance_id=10, axis=0, value=0.45), route)
        self.assertIn("right", p1.held)            # hysteresis: still held
        pads.handle(self.ev(pygame.JOYAXISMOTION, instance_id=10, axis=0, value=0.1), route)
        self.assertNotIn("right", p1.held)
        pads.handle(self.ev(pygame.JOYBUTTONDOWN, instance_id=11, button=7), route)
        self.assertIn("start", p2.held)

    def test_pad_map_file(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.write(fd, b'{"a": [3], "b": [4], "start": [9]}')
        os.close(fd)
        try:
            self.assertEqual(common.load_pad_map(path)["a"], [3])
        finally:
            os.unlink(path)
        self.assertEqual(common.load_pad_map("/nonexistent.json"), common.DEFAULT_PAD)

    def test_level_shots_reach_the_bunker_slits(self):
        """The slits sit at rifle height, so a hero standing or running on the ground can hit them."""
        from core.games import soldiers_art as art
        g = sv.make(seed=1, scores_path=os.path.join(tempfile.mkdtemp(), "s.json"))
        g.unlocked, g.level_choice = 5, 3
        inp = common.Input()
        inp.down("a"); g.step(1 / 60, inp); inp.end_frame(); inp.up("a")
        g.reset()
        g.level = next(i for i, lv in enumerate(sv.LEVELS) if lv["boss"] == "bunker")
        g.length = sv.LEVELS[g.level]["length"]
        g.start_boss()
        port = g.port_rects()[0]
        for who in ("miles", "felix"):
            for pose in ("stand", "run0", "run1"):
                _, height = art.muzzle_offset(who, pose, "fwd", 1)
                self.assertTrue(port.top <= sv.GROUND - height < port.bottom, (who, pose))
        before = g.boss["hp"]
        self.assertTrue(g.hit_boss({"x": port.centerx, "y": sv.GROUND - 22}))
        self.assertEqual(g.boss["hp"], before - 1)

    def test_a_real_shot_from_across_the_screen_hurts_the_bunker(self):
        """A bullet flown frame by frame from a hero standing well back must get through a slit."""
        g = sv.make(seed=1, scores_path=os.path.join(tempfile.mkdtemp(), "s.json"))
        g.reset()
        g.level = next(i for i, lv in enumerate(sv.LEVELS) if lv["boss"] == "bunker")
        g.length = sv.LEVELS[g.level]["length"]
        g.start_boss()
        r = g.boss_rect()
        for height in (22, 17):                                   # Miles's rifle, then Felix's
            before = g.boss["hp"]
            bullet = {"x": r.x - 200.0, "y": float(sv.GROUND - height)}
            for _ in range(200):
                bullet["x"] += 5.3                                   # a bullet's step each frame
                if g.hit_boss(bullet):
                    break
            self.assertEqual(g.boss["hp"], before - 1, height)
        self.assertTrue(g.hit_boss({"x": r.x + 3.0, "y": float(r.y + 10)}))      # the wall above the slits stops shots
        self.assertEqual(g.boss["hp"], before - 1)

    def test_the_sniper_tower_fires_falls_and_is_manned_again(self):
        g = sv.make(seed=1, scores_path=os.path.join(tempfile.mkdtemp(), "s.json"))
        inp = common.Input()
        g.reset()
        g.phase = "play"
        g.players = [g.new_player("miles", 0)]
        g.players[0].update(chute=False, y=float(sv.GROUND))
        g.level = next(i for i, lv in enumerate(sv.LEVELS) if lv["boss"] == "bunker")
        g.length = sv.LEVELS[g.level]["length"]
        g.cam = float(g.length - common.W)
        g.players[0]["x"] = g.cam + 60
        g.start_boss()
        tw = g.boss["tower"]
        self.assertEqual(tw["state"], "manned")
        for _ in range(60 * 4):
            g.update_tower(1 / 60)
        self.assertTrue(any(b.get("missile") for b in g.ebullets))
        gun = g.gunner_rect()
        for _ in range(sv.TOWER_HP):
            self.assertTrue(g.hit_boss({"x": gun.centerx, "y": gun.centery}))
        self.assertEqual(tw["state"], "empty")
        self.assertFalse(g.hit_boss({"x": gun.centerx, "y": gun.centery}))       # nobody there to hit
        g.ebullets = []
        for _ in range(int(60 * (sv.TOWER_EMPTY_S + 0.2))):
            g.update_tower(1 / 60)
        self.assertEqual(tw["state"], "climb")
        self.assertEqual(g.ebullets, [])                                         # he cannot fire from the ladder
        for _ in range(int(60 * (sv.TOWER_CLIMB_S + 0.2))):
            g.update_tower(1 / 60)
        self.assertEqual((tw["state"], tw["hp"]), ("manned", sv.TOWER_HP))
        canvas = pygame.Surface((common.W, common.H))
        g.draw_boss(canvas, g.cam)

    def test_a_player_who_is_out_gets_one_life_at_the_next_mission(self):
        g = sv.make(seed=1, scores_path=os.path.join(tempfile.mkdtemp(), "s.json"))
        g.reset()
        g.players = [g.new_player("miles", 0), g.new_player("felix", 1)]
        g.players[0]["lives"] = 2
        g.players[1].update(out=True, lives=0)
        g.level = 1
        g.begin_level()
        self.assertEqual([(p["out"], p["lives"]) for p in g.players], [(False, 2), (False, 1)])
        self.assertTrue(g.players[1]["chute"])                    # he parachutes back in with everyone else


if __name__ == "__main__":
    unittest.main()
