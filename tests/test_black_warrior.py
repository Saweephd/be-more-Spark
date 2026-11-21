"""Black Warrior: story, mask, combos, jump, specials, grabs, weapons, guests, set pieces, bosses, katana, reforms, levels."""
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
    from core.games import common, black_warrior as bw, bw_art, bw_bosses, bw_levels
    from core import extras
    HAVE_PYGAME = True
except Exception:
    HAVE_PYGAME = False

DT = 1 / 60


@unittest.skipUnless(HAVE_PYGAME, "pygame not installed")
class BlackWarriorTests(unittest.TestCase):
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
        for b in held:
            inp.up(b)

    def tap(self, g, inp, *btns):
        self.frames(g, inp, 1, *btns)
        self.frames(g, inp, 4)

    def start(self, level=0):
        g = bw.make(seed=2, scores_path=self.scores)
        inp = common.Input()
        self.frames(g, inp, 1, "a")
        if level:
            g.start_level(level)
        self.assertEqual(g.phase, "intro")
        for _ in range(12):
            self.frames(g, inp, 20)
            self.tap(g, inp, "a")
            if g.phase != "intro":
                break
        self.assertEqual(g.phase, "walk")
        self.assertFalse(g.p.masked)
        return g, inp

    def to_fight(self, level=0):
        g, inp = self.start(level)
        for _ in range(400):
            self.frames(g, inp, 1, "right")
            if g.phase in ("mask_on", "fight"):
                break
        self.frames(g, inp, 40)
        self.assertEqual(g.phase, "fight")
        self.assertTrue(g.p.masked)
        return g, inp

    def lone_enemy(self, g, kind="valet", dx=20):
        p = g.p
        e = bw.Enemy(kind, p.x + dx, p.y)
        e.cool = 99
        g.enemies = [e]
        p.face = 1
        return e

    # ---------------------------------------------------------------- Quick
    def test_opening_story_then_walk_unmasked(self):
        g, inp = self.start()
        self.assertEqual(g.scene, "tower_street")

    def test_fight_zone_masks_up_and_locks_camera(self):
        g, inp = self.to_fight()
        cam = g.cam
        self.frames(g, inp, 60, "right")
        self.assertEqual(g.cam, cam)
        self.assertLessEqual(g.p.x, cam + common.W - 10)

    def test_punch_combo_ends_in_knockdown(self):
        g, inp = self.to_fight()
        e = self.lone_enemy(g)
        e.hp = 99
        for _ in range(3):
            self.tap(g, inp, "b")
            self.frames(g, inp, 14)
        self.assertIn(e.state, ("fly", "down", "getup"))
        self.assertLess(e.hp, 99)

    def test_kick_combo_hits(self):
        g, inp = self.to_fight()
        e = self.lone_enemy(g, dx=26)
        self.tap(g, inp, "a")
        self.frames(g, inp, 12)
        self.assertLess(e.hp, e.max_hp)

    def test_jump_and_flying_kick(self):
        g, inp = self.to_fight()
        g.enemies = []
        self.frames(g, inp, 1, "a", "b")
        self.frames(g, inp, 2)
        self.assertEqual(g.p.state, "jump")
        e = self.lone_enemy(g, dx=20)
        self.tap(g, inp, "a")
        self.assertEqual(g.p.air, "kick")
        self.frames(g, inp, 60)
        self.assertEqual(g.p.state, "idle")
        self.assertLess(e.hp, e.max_hp)

    def test_special_needs_meter_and_spends_it(self):
        g, inp = self.to_fight()
        e = self.lone_enemy(g, dx=-30)
        g.p.meter = 1.5
        self.frames(g, inp, 32, "a", "b")
        self.assertAlmostEqual(g.p.meter, 0.5, delta=0.15)
        self.frames(g, inp, 40)
        self.assertLess(e.hp, e.max_hp)

    def test_full_meter_unleashes_nine_lives(self):
        g, inp = self.to_fight()
        e = self.lone_enemy(g, dx=120)
        g.p.meter = 3.0
        self.frames(g, inp, 30, "a", "b")
        self.assertEqual(g.p.state, "flurry")
        self.frames(g, inp, 100)
        self.assertEqual(g.p.meter, 0.0)
        self.assertLess(e.hp, e.max_hp)

    def test_dodge_slides_and_is_invulnerable(self):
        g, inp = self.to_fight()
        g.enemies = []
        x0 = g.p.x
        self.tap(g, inp, "left")
        self.frames(g, inp, 1, "left")
        self.assertEqual(g.p.state, "dodge")
        self.assertGreater(g.p.inv, 0)
        self.frames(g, inp, 10)
        self.assertLess(g.p.x, x0 - 20)

    def test_daze_grab_knee_and_throw(self):
        g, inp = self.to_fight()
        e = self.lone_enemy(g, dx=18)
        e.hp = 200
        for _ in range(3):
            g.damage_enemy(e, 1, False, 1)
        self.assertEqual(e.state, "dazed")
        self.frames(g, inp, 3, "right")
        self.assertEqual(g.p.state, "grab")
        self.tap(g, inp, "b")
        self.frames(g, inp, 14)
        self.assertEqual(g.p.state, "grab")
        other = bw.Enemy("valet", g.p.x - 60, g.p.y)
        other.cool = 99
        g.enemies.append(other)
        inp.down("left")
        self.tap(g, inp, "a")
        inp.up("left")
        self.assertEqual(e.state, "fly")
        self.frames(g, inp, 40)
        self.assertLess(other.hp, other.max_hp)

    def test_back_elbow(self):
        g, inp = self.to_fight()
        e = self.lone_enemy(g, dx=-18)
        inp.down("left")
        g.p.face = 1
        self.frames(g, inp, 1, "b")
        inp.up("left")
        self.frames(g, inp, 20)
        self.assertLess(e.hp, e.max_hp)

    def test_weapon_pickup_swing_and_throw(self):
        g, inp = self.to_fight()
        g.enemies = []
        g.weapons = [{"x": g.p.x + 4, "y": g.p.y, "kind": "bat"}]
        self.tap(g, inp, "b")
        self.assertIsNotNone(g.p.weapon)
        e = self.lone_enemy(g, dx=34)
        self.tap(g, inp, "b")
        self.frames(g, inp, 20)
        self.assertLess(e.hp, e.max_hp)
        self.tap(g, inp, "a")
        self.assertIsNone(g.p.weapon)

    def test_enemies_fight_back(self):
        g, inp = self.to_fight()
        e = self.lone_enemy(g, dx=40)
        e.cool = 0
        g.p.inv = 0
        hp = g.p.hp
        self.frames(g, inp, 120)
        self.assertLess(g.p.hp, hp)

    def test_lose_all_lives_then_continue(self):
        g, inp = self.to_fight()
        g.enemies = []
        for _ in range(3):
            g.p.hp = 1
            g.p.inv = 0
            g.hurt_player(10, g.p.x - 5)
            self.frames(g, inp, 120)
        self.assertEqual(g.phase, "continue")
        self.frames(g, inp, 40)
        self.tap(g, inp, "a")
        self.assertEqual(g.phase, "fight")
        self.assertEqual(g.p.lives, 3)

    # ---------------------------------------------------------------- guests
    def test_mazee_token_assist_and_farewell(self):
        g, inp = self.start()
        g.zones[0]["done"] = True
        g.p.x, g.p.y = g.token["x"] - 30, g.token["y"]
        g.cam = 300
        self.frames(g, inp, 30, "right")
        self.assertIsNotNone(g.guest)
        self.assertTrue(any("Hey Mazee" in b[0] for b in g.bubbles))
        e = g.spawn("valet", g.p.x + 80, g.p.y)
        e.cool = 99
        g.phase = "fight"
        g.zone = {"at": g.cam, "waves": [["valet"]], "wave": 0, "done": False}
        self.frames(g, inp, 90)
        self.assertLess(e.hp, e.max_hp)
        g.guest.t = 0.05
        self.frames(g, inp, 10)
        self.assertTrue(any("Thanks for the assist, Mazee" in b[0] for b in g.bubbles))

    def test_every_guest_team_attack(self):
        for kind in bw_levels.GUEST_ORDER:
            g, inp = self.start()
            g.phase = "fight"
            g.zone = {"at": g.cam, "waves": [["valet"]], "wave": 0, "done": False}
            g.summon(kind)
            self.assertTrue(any(bw_levels.GUESTS[kind]["greet"] in b[0] for b in g.bubbles), kind)
            self.frames(g, inp, 90)
            self.assertEqual(g.guest.state, "fight", kind)
            foes = [g.spawn("valet", g.p.x + 40 + i * 30, g.p.y) for i in range(2)]
            for e in foes:
                e.cool, e.hp = 99, 200
            score = g.score
            self.frames(g, inp, 64, "b")
            self.frames(g, inp, 120)
            self.assertTrue(any(e.hp < 190 for e in foes), kind)
            self.assertGreater(g.score, score, kind)

    def test_crate_hides_a_guest_we_have_met(self):
        g, inp = self.start(level=2)
        self.assertIsNotNone(g.crate)
        g.zones = []
        g.cam = g.crate["x"] - 200
        g.p.x, g.p.y, g.p.face = g.crate["x"] - 24, g.crate["y"], 1
        for _ in range(3):
            self.tap(g, inp, "a")
            self.frames(g, inp, 20)
        self.assertIsNone(g.crate)
        self.assertIn(g.token["guest"], ("mazee", "uncle_t"))

    # ---------------------------------------------------------------- levels
    def test_whole_first_level_into_level_two(self):
        g, inp = self.start()
        g.load_scene(1)
        for z in g.zones:
            z["done"] = True
        g.p.x = g.length - 30
        g.cam = g.length - common.W
        g.set_phase("walk")
        self.frames(g, inp, 60, "right")
        self.assertEqual(g.scene, "elevator")
        self.frames(g, inp, 60)
        self.assertEqual(g.phase, "ride")
        for _ in range(80):
            g.p.inv = 99
            for e in g.enemies:
                if e.alive:
                    e.hp = 0
                    e.state, e.st = "out", 0.0
            self.frames(g, inp, 30)
            if g.phase != "ride":
                break
        self.assertEqual(g.scene, "penthouse")
        self.assertEqual(g.phase, "boss_intro")
        for _ in range(10):
            self.frames(g, inp, 120)
            self.tap(g, inp, "a")
            if g.phase == "boss":
                break
        self.assertEqual(g.music, "bw_boss")
        g.p.inv = 99
        self.frames(g, inp, 200)
        g.boss.hp = 0
        self.frames(g, inp, 2)
        self.assertEqual(g.phase, "katana")
        self.frames(g, inp, int(9.6 * 60))
        self.assertEqual(g.phase, "reform")
        self.assertTrue(g.boss.gag)
        self.assertFalse(g.p.masked)
        self.assertEqual(common.load_scores(self.scores)[bw.SEEN_KEY % 1], 1)
        self.frames(g, inp, 12 * 60)
        self.frames(g, inp, 4 * 60)
        self.assertEqual(g.L["n"], 2)
        self.assertEqual(g.phase, "intro")
        self.assertEqual(common.load_scores(self.scores)[bw.UNLOCK_KEY], 2)

    def test_every_level_runs_scene_by_scene(self):
        for li, L in enumerate(bw_levels.LEVELS):
            g = bw.make(seed=li, scores_path=self.scores)
            inp = common.Input()
            self.frames(g, inp, 1, "a")
            g.start_level(li)
            self.frames(g, inp, 10)
            for si, sc in enumerate(L["scenes"]):
                if sc["kind"] == "walk":
                    for z in g.zones:
                        z["done"] = True
                    g.set_phase("walk")
                    g.p.x = g.length - 30
                    g.cam = g.length - common.W
                    self.frames(g, inp, 40, "right")
                elif sc["kind"] == "ride":
                    self.assertEqual(g.scene, sc["stage"])
                    for _ in range(80):
                        g.p.inv = 99
                        for e in g.enemies:
                            if e.alive:
                                e.hp, e.state, e.st = 0, "out", 0.0
                        if g.boss is not None:
                            g.boss.hp = 0
                        self.frames(g, inp, 30)
                        if g.sc is not sc:
                            break
                else:
                    self.assertEqual(g.phase, "boss_intro", (li, si))
                    self.assertEqual(g.boss.name, L["boss_name"])
            self.assertEqual(g.scene, L["scenes"][-1]["stage"])

    def test_every_boss_fights_back_and_can_be_finished(self):
        for li, L in enumerate(bw_levels.LEVELS):
            g, inp = self.start()
            g.start_level(li)
            g.load_scene(len(L["scenes"]) - 1)
            g.boss = bw_bosses.make(L["boss"])
            g.set_phase("boss")
            g.p.inv = 0
            hp = g.p.hp
            for _ in range(20):
                g.p.inv = 0
                self.frames(g, inp, 60)
                if g.p.hp < hp:
                    break
            self.assertLess(g.p.hp, hp, L["boss"])
            g.p.inv = 99
            g.boss.hp = 0
            self.frames(g, inp, 2)
            self.assertEqual(g.phase, "katana", L["boss"])
            self.frames(g, inp, int(9.6 * 60))
            self.assertEqual(g.phase, "reform", L["boss"])

    def test_boss_weak_spots(self):
        heir = bw_bosses.make("heir")
        self.assertFalse(heir.take(10, False))
        self.assertTrue(heir.take(10, True))
        heir.z = 6
        self.assertTrue(heir.take(10, False))
        ev = bw_bosses.make("eviction")
        self.assertFalse(ev.take(10, True))
        ev.state = "ground"
        self.assertTrue(ev.take(10, False))
        smog = bw_bosses.make("smog")
        smog.armor = 0.5
        smog.take(20, False)
        self.assertEqual(smog.hp, smog.max - 10)
        lie = bw_bosses.make("biglie")
        lie.state = "shield"
        self.assertFalse(lie.take(10, True))

    def test_city_hall_rematches(self):
        g, inp = self.start(level=5)
        g.load_scene(1)
        g.set_phase("ride")
        seen = set()
        for _ in range(120):
            g.p.inv = 99
            if g.boss is not None:
                seen.add(g.boss.name)
                self.assertTrue(g.boss.mini)
                g.boss.hp = 0
            self.frames(g, inp, 30)
            if g.phase != "ride":
                break
        self.assertEqual(len(seen), 5)
        self.assertEqual(g.phase, "boss_intro")

    def test_fake_news_scrambles_controls(self):
        g, inp = self.to_fight(level=5)
        g.enemies = []
        g.p.inv = 0
        g.projs.append({"kind": "static", "x": g.p.x + 5, "y": g.p.y, "z": 22.0, "vx": -10.0, "vz": 0.0, "g": 0.0,
                        "dmg": 5, "owner": "enemy", "scramble": True})
        self.frames(g, inp, 2)
        self.assertGreater(g.scramble, 0)
        self.frames(g, inp, 30)
        x = g.p.x
        self.frames(g, inp, 20, "right")
        self.assertLess(g.p.x, x)

    def test_conveyor_belt_carries_quick(self):
        g, inp = self.start(level=2)
        g.load_scene(1)
        g.set_phase("ride")
        g.prog = 5
        x = g.p.x
        self.frames(g, inp, 30)
        self.assertNotEqual(round(g.p.x), round(x))

    def test_level_select_after_unlocking(self):
        common.save_score(bw.UNLOCK_KEY, 4, self.scores)
        g = bw.make(seed=1, scores_path=self.scores)
        inp = common.Input()
        self.frames(g, inp, 1, "a")
        self.assertEqual(g.phase, "select")
        self.assertEqual(g.choice, 4)
        self.frames(g, inp, 30)
        self.tap(g, inp, "up")
        self.tap(g, inp, "a")
        self.assertEqual(g.L["n"], 3)
        self.assertEqual(g.phase, "intro")

    def test_finale_ends_the_game_with_a_win(self):
        common.save_score(bw.SEEN_KEY % 6, 1, self.scores)
        g, inp = self.start(level=5)
        g.load_scene(len(g.L["scenes"]) - 1)
        g.boss = bw_bosses.make("biglie")
        g.set_phase("boss")
        g.boss.hp = 0
        self.frames(g, inp, 2)
        self.frames(g, inp, int(9.6 * 60))
        self.frames(g, inp, 12 * 60)
        self.assertEqual(g.phase, "ending")
        self.frames(g, inp, 23 * 60)
        self.assertEqual(g.state, "over")
        self.assertTrue(g.win)

    def test_seen_cutscene_can_be_skipped(self):
        common.save_score(bw.SEEN_KEY % 1, 1, self.scores)
        g = bw.make(seed=2, scores_path=self.scores)
        inp = common.Input()
        self.frames(g, inp, 1, "a")
        g.load_scene(3)
        g.boss = bw_bosses.make("heir")
        g.begin_katana()
        self.frames(g, inp, 30)
        self.frames(g, inp, 1, "start")
        self.assertEqual(g.phase, "reform")
        self.assertEqual(g.state, "play")

    def test_drawn_portraits(self):
        for masked in (False, True):
            self.assertEqual(bw_art.portrait(masked).get_size(), (96, 96))

    def test_voice(self):
        self.assertEqual(extras.match_game("play black warrior"), "black_warrior")


if __name__ == "__main__":
    unittest.main()
