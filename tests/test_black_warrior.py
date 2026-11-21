"""Black Warrior, Level 1: story, mask, combos, jump, specials, grabs, weapons, Mazee, elevator, boss, katana, reform."""
import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["BW_PRIVATE_DIR"] = "/nonexistent-private-dir"

try:
    import pygame
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((800, 480))
    from core.games import common, black_warrior as bw, bw_art
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

    def start(self):
        g = bw.make(seed=2, scores_path=self.scores)
        inp = common.Input()
        self.frames(g, inp, 1, "a")                  # title
        self.assertEqual(g.phase, "intro")
        for _ in range(12):                          # read through the opening
            self.frames(g, inp, 20)
            self.tap(g, inp, "a")
            if g.phase != "intro":
                break
        self.assertEqual(g.phase, "walk")
        self.assertFalse(g.p.masked)
        return g, inp

    def to_fight(self):
        g, inp = self.start()
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
        g.enemies = [bw.Enemy(kind, p.x + dx, p.y)]
        e = g.enemies[0]
        e.cool = 99
        p.face = 1
        return e

    def test_opening_story_then_walk_unmasked(self):
        g, inp = self.start()
        self.assertEqual(g.scene, "street")

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
        before = e.hp
        self.tap(g, inp, "a")
        self.frames(g, inp, 12)
        self.assertLess(e.hp, before)

    def test_jump_and_flying_kick(self):
        g, inp = self.to_fight()
        g.enemies = []
        self.frames(g, inp, 1, "a", "b")
        self.frames(g, inp, 2)
        self.assertEqual(g.p.state, "jump")
        self.assertGreater(g.p.z, 0)
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
        self.assertIn(g.p.state, ("special", "idle"))
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
        for mv in ("jab", "jab", "jab"):
            g.damage_enemy(e, 1, False, 1)
        self.assertEqual(e.state, "dazed")
        self.frames(g, inp, 3, "right")
        self.assertEqual(g.p.state, "grab")
        self.assertIs(g.p.held, e)
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
        self.assertLess(e.vx, 0)
        self.frames(g, inp, 40)
        self.assertLess(other.hp, other.max_hp)

    def test_back_elbow(self):
        g, inp = self.to_fight()
        e = self.lone_enemy(g, dx=-18)
        g.p.face = 1
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

    def test_mazee_token_assist_and_farewell(self):
        g, inp = self.start()
        g.zones[0]["done"] = True
        g.p.x, g.p.y = g.token["x"] - 30, g.token["y"]
        g.cam = 300
        self.frames(g, inp, 30, "right")
        self.assertIsNotNone(g.mazee)
        self.assertTrue(any("Hey Mazee" in b[0] for b in g.bubbles))
        g.enemies = [bw.Enemy("valet", g.p.x + 80, g.p.y)]
        g.enemies[0].cool = 99
        g.phase = "fight"
        g.zone = {"at": g.cam, "waves": [["valet"]], "wave": 0, "done": False}
        self.frames(g, inp, 90)
        self.assertLess(g.enemies[0].hp, g.enemies[0].max_hp)
        g.mazee["t"] = 0.05
        self.frames(g, inp, 10)
        self.assertTrue(any("Thanks for the assist, Mazee" in b[0] for b in g.bubbles))

    def test_mazee_team_attack(self):
        g, inp = self.start()
        g.phase = "fight"
        g.zone = {"at": g.cam, "waves": [["valet"]], "wave": 0, "done": False}
        g.summon_mazee()
        g.mazee["state"] = "fight"
        e = bw.Enemy("valet", g.p.x + 90, g.p.y)
        e.cool, e.hp = 99, 200
        g.enemies = [e]
        self.frames(g, inp, 64, "b")
        self.frames(g, inp, 50)
        self.assertLess(e.hp, 190)
        self.assertGreater(g.score, 1000)

    def test_whole_level_elevator_boss_katana_reform(self):
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
        self.assertEqual(g.phase, "elevator")
        for _ in range(60):
            g.p.inv = 99
            for e in g.enemies:
                if e.alive:
                    e.hp = 0
                    e.state, e.st = "out", 0.0
            self.frames(g, inp, 30)
            if g.phase != "elevator":
                break
        self.assertEqual(g.scene, "penthouse")
        self.assertEqual(g.phase, "boss_intro")
        for _ in range(10):
            self.frames(g, inp, 120)
            self.tap(g, inp, "a")
            if g.phase == "boss":
                break
        self.assertEqual(g.phase, "boss")
        self.assertEqual(g.music, "bw_boss")
        g.p.inv = 99
        self.frames(g, inp, 200)
        g.boss["hp"] = 0
        self.frames(g, inp, 2)
        self.assertEqual(g.phase, "katana")
        self.frames(g, inp, int(9.6 * 60))
        self.assertEqual(g.phase, "reform")
        self.assertTrue(g.boss["hat"])
        self.assertFalse(g.p.masked)
        self.assertEqual(common.load_scores(self.scores)[bw.SEEN_KEY], 1)
        self.frames(g, inp, 12 * 60)
        self.frames(g, inp, 4 * 60)
        self.assertEqual(g.state, "over")
        self.assertTrue(g.win)

    def test_seen_cutscene_can_be_skipped(self):
        common.save_score(bw.SEEN_KEY, 1, self.scores)
        g = bw.make(seed=2, scores_path=self.scores)
        inp = common.Input()
        self.frames(g, inp, 1, "a")
        g.load_scene(3)
        g.boss = {"x": 300.0, "y": 190.0, "z": 0.0, "hp": 0, "max": 260, "state": "beaten", "st": 0.0,
                  "flash": 0.0, "summons": 2, "vx": 0.0, "cycle": 0, "hat": False}
        g.begin_katana()
        self.frames(g, inp, 30)
        self.frames(g, inp, 1, "start")
        self.assertEqual(g.phase, "reform")
        self.assertEqual(g.state, "play")

    def test_boss_only_hit_from_ground_when_low(self):
        g, inp = self.start()
        g.boss = {"x": 300.0, "y": 190.0, "z": 34.0, "hp": 260, "max": 260, "state": "float", "st": 0.0,
                  "flash": 0.0, "summons": 0, "vx": 0.0, "cycle": 0, "hat": False}
        self.assertFalse(g.boss_hit(10, False, 0, 0))
        self.assertTrue(g.boss_hit(10, True, 0, 0))
        g.boss["z"] = 6
        self.assertTrue(g.boss_hit(10, False, 0, 0))
        self.assertEqual(g.boss["hp"], 240)

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

    def test_enemies_fight_back(self):
        g, inp = self.to_fight()
        e = self.lone_enemy(g, dx=40)
        e.cool = 0
        g.p.inv = 0
        hp = g.p.hp
        self.frames(g, inp, 120)
        self.assertLess(g.p.hp, hp)

    def test_portrait_falls_back_without_private_files(self):
        img = bw_art.portrait(False)
        self.assertEqual(img.get_size(), (96, 96))

    def test_voice(self):
        self.assertEqual(extras.match_game("play black warrior"), "black_warrior")


if __name__ == "__main__":
    unittest.main()
