"""The Big Move and Air Hockey, driven frame by frame without a screen."""
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
    from core.games import air_hockey as ah, big_move as bm, common
    HAVE_PYGAME = True
except Exception:
    HAVE_PYGAME = False

DT = 1 / 60


def lane_clear(g, key_y, h, x, hw, t0, t1):
    """Will the strip of road at key_y stay clear around x between t0 and t1 seconds from now?"""
    for v in g.vehicles:
        if v["y"] != key_y or v["h"] != h:
            continue
        for t in (t0, (t0 + t1) / 2, t1):
            vx = v["x"] + v["dir"] * v["v"] * t
            if vx - hw - 14 < x < vx + v["w"] + hw + 14:
                return False
    return True


def mover_bot(g, p):
    """A careful mover: waits on the curb, the median and the sidewalk for a gap, then goes. Returns buttons to hold."""
    hw = bm.ITEMS[p["carry"]][2] if p["carry"] else 4
    speed = bm.WALK * (bm.ITEMS[p["carry"]][1] if p["carry"] else 1.0)
    T = 27 / speed
    x, y = p["x"], p["y"]
    up = bool(p["carry"])
    if not up:
        for d in g.dropped:                           # tripped by a cat: pick it straight back up
            if abs(d["x"] - x) < 16 and abs(d["y"] - y) < 16:
                return {"a"}
            if abs(d["y"] - y) < 10:
                return {"right" if d["x"] > x else "left"}
        if not g.truck_items and not g.dropped:
            return set()
    r = [ry for ry, _, _ in bm.ROADS]
    by, bh = bm.BIKE_LANE

    def clear(strips):
        t = 0.0
        for sy, sh in strips:
            dur = (sh + 2) / speed
            if not lane_clear(g, sy, sh, x, hw, t, t + dur + 0.15):
                return False
            t += dur
        return True
    if up:
        if y > 200:                                   # on the curb: cross in the middle, where you can see both ways
            if abs(x - bm.DOOR_X) > 3:
                return {"right" if x < bm.DOOR_X else "left"}
            return {"up"} if clear([(r[3], 26), (r[2], 26)]) else set()
        if 148 <= y <= 200 or 70 <= y < 122 or by <= y < 70:
            return {"up"}                             # committed: keep going
        if 122 <= y < 148:                            # on the median
            if y > 126:
                return {"up"}
            return {"up"} if clear([(r[1], 26), (r[0], 26), (by, bh)]) else set()
        if abs(x - bm.DOOR_X) > 3:                    # on the sidewalk: walk to the door
            return {"right" if x < bm.DOOR_X else "left"}
        return {"up"}
    # heading back for the next thing
    target_x = bm.TRUCK.centerx - 10
    if y < by - 1:
        if y < by - 4:
            return {"down"}
        return {"down"} if clear([(by, bh), (r[0], 26), (r[1], 26)]) else set()
    if y < 124:
        return {"down"}
    if y < 146:
        if y < 142:
            return {"down"}
        return {"down"} if clear([(r[2], 26), (r[3], 26)]) else set()
    if y < 206:
        return {"down"}
    if abs(x - target_x) > 6:
        return {"left" if x > target_x else "right"}
    return {"a"}


@unittest.skipUnless(HAVE_PYGAME, "pygame not installed")
class BigMove(unittest.TestCase):
    def setUp(self):
        self.scores = tempfile.mktemp(suffix=".json")
        self.canvas = pygame.Surface((common.W, common.H))

    def tearDown(self):
        if os.path.exists(self.scores):
            os.unlink(self.scores)

    def game(self, load=0, seed=1):
        g = bm.make(seed=seed, scores_path=self.scores)
        inp = common.Input()
        inp.down("a"); g.step(DT, inp); inp.end_frame(); inp.up("a")
        self.assertEqual(g.phase, "intro")
        g.render(self.canvas)
        for _ in range(40):
            g.step(DT, inp); g.render(self.canvas); inp.end_frame()
        inp.down("a"); g.step(DT, inp); inp.end_frame(); inp.up("a")      # skip the opening scene
        self.assertEqual(g.phase, "play")
        if load:
            g.load_i = load
            g.start_load()
        return g, inp

    def quiet(self, g):
        g.vehicles, g.cats = [], []
        g.lane_t = {k: 1e9 for k in ("bike", "bike2", "road0", "road1", "road2", "road3")}
        g.cat_t = 1e9
        g.players[0]["inv"] = 0.0

    def hold(self, g, inp, frames, *buttons):
        for b in buttons:
            inp.down(b)
        for _ in range(frames):
            g.step(DT, inp)
            inp.end_frame()
        for b in buttons:
            inp.up(b)

    def test_carry_an_item_from_the_truck_to_the_door(self):
        g, inp = self.game()
        self.quiet(g)
        p = g.players[0]
        p["x"], p["y"] = float(bm.TRUCK.centerx), 224.0
        self.hold(g, inp, 1, "a")
        self.assertEqual(p["carry"], "box")
        self.assertEqual(g.truck_items, ["lamp", "table"])
        p["x"] = float(bm.DOOR_X)
        self.hold(g, inp, 60 * 4, "up")
        self.assertIsNone(p["carry"])
        self.assertEqual(g.delivered, ["box"])
        self.assertGreaterEqual(g.score, 100)

    def test_big_items_are_slower_and_a_helper_speeds_them_up(self):
        g, inp = self.game()
        self.quiet(g)
        p = g.players[0]

        def climb(kind, helper=False):
            g.players[:] = [p]
            p.update(x=300.0, y=220.0, carry=kind, stun=0.0)
            if helper:
                g.players.append(g.new_player("lucas", 1))
                g.players[1].update(x=314.0, y=220.0)
            self.hold(g, inp, 30, "up")
            return 220.0 - p["y"]
        self.assertGreater(climb("box"), climb("sofa") * 1.4)
        self.assertGreater(climb("sofa", helper=True), climb("sofa") * 1.3)

    def test_traffic_costs_a_life_and_the_item_goes_back(self):
        g, inp = self.game()
        self.quiet(g)
        p = g.players[0]
        p.update(x=200.0, y=190.0, carry="table")
        g.truck_items = ["lamp"]
        img = g.car_img("car", bm.CAR_COLORS[0], 1)
        g.vehicles.append({"kind": "car", "lane": "road3", "x": 185.0, "y": 174, "w": img.get_width(), "h": bm.LANE_H,
                           "dir": 1, "v": 10.0, "img": img, "rang": False})
        self.hold(g, inp, 2)
        self.assertEqual(g.lives, 2)
        self.assertEqual(g.truck_items, ["table", "lamp"])
        self.assertIsNone(p["carry"])
        self.assertGreater(p["y"], 200)

    def test_a_cat_trips_you_and_someone_asks_about_peno(self):
        g, inp = self.game()
        self.quiet(g)
        p = g.players[0]
        p.update(x=200.0, y=140.0, carry="lamp")
        g.cats.append({"x": 150.0, "y": 137.0, "dir": 1, "v": 60.0, "anim": 0.0, "dart": 0.0, "mood": 99.0, "said": 0.0})
        self.hold(g, inp, 5)
        self.assertEqual(p["say"], bm.PENO)
        self.hold(g, inp, 60)
        self.assertIsNone(p["carry"])
        self.assertEqual(g.lives, 3)                              # cats cost no lives
        self.assertEqual([d["kind"] for d in g.dropped], ["lamp"])
        g.cats = []
        self.hold(g, inp, 60)
        p["x"], p["y"] = g.dropped[0]["x"], g.dropped[0]["y"]
        self.hold(g, inp, 1, "a")
        self.assertEqual(p["carry"], "lamp")

    def test_second_controller_brings_the_other_mover(self):
        g, inp = self.game()
        inp.p2 = common.Input()
        inp.p2.down("a")
        g.step(DT, inp)
        self.assertEqual([p["who"] for p in g.players], ["whitney", "lucas"])

    def test_every_load_can_be_cleared_by_a_careful_mover(self):
        for load in range(len(bm.LOADS)):
            g, inp = self.game(load=load, seed=3 + load)
            held = set()
            for frame in range(60 * 420):
                if g.phase != "play" or g.state != "play":
                    break
                want = mover_bot(g, g.players[0]) if g.players[0]["stun"] <= 0 else set()
                for b in held - want:
                    inp.up(b)
                for b in want - held:
                    inp.down(b)
                held = want
                g.step(DT, inp)
                inp.end_frame()
                if frame % 240 == 0:
                    g.render(self.canvas)
            self.assertEqual(g.phase, "clear", "load %d: lives %d, left %s" % (load + 1, g.lives, g.truck_items))
            self.assertGreaterEqual(g.lives, 1)
            g.render(self.canvas)

    def test_finishing_the_last_load_wins(self):
        g, inp = self.game(load=4)
        g.truck_items, g.phase, g.pt = [], "clear", 0.0
        self.hold(g, inp, 200)
        self.assertEqual(g.state, "over")
        self.assertTrue(g.win)


@unittest.skipUnless(HAVE_PYGAME, "pygame not installed")
class AirHockey(unittest.TestCase):
    def setUp(self):
        self.scores = tempfile.mktemp(suffix=".json")
        self.canvas = pygame.Surface((common.W, common.H))

    def tearDown(self):
        if os.path.exists(self.scores):
            os.unlink(self.scores)

    def game(self, mode=1, seed=1):
        g = ah.make(seed=seed, scores_path=self.scores)
        g.mode = mode
        inp = common.Input()
        inp.down("a"); g.step(DT, inp); inp.end_frame(); inp.up("a")
        self.assertEqual(g.phase, "intro")
        for _ in range(30):
            g.step(DT, inp); g.render(self.canvas); inp.end_frame()
        inp.down("a"); g.step(DT, inp); inp.end_frame(); inp.up("a")
        self.assertEqual(g.phase, "play")
        return g, inp

    def run_frames(self, g, inp, n):
        for i in range(n):
            g.step(DT, inp)
            inp.end_frame()
            pk = g.puck
            self.assertTrue(-1 <= pk["x"] <= ah.TW + 1 and -1 <= pk["y"] <= ah.TL + 1, pk)
            if i % 30 == 0:
                g.render(self.canvas)
            if g.state != "play":
                break

    def test_paddle_stays_in_its_half_and_hits_the_puck(self):
        g, inp = self.game()
        g.wait = 0
        g.puck.update(x=g.me["x"], y=g.me["y"] - 40, vx=0.0, vy=0.0)
        inp.down("up")
        fastest = 0.0
        for _ in range(40):
            self.run_frames(g, inp, 1)
            fastest = min(fastest, g.puck["vy"])
        inp.up("up")
        self.assertGreaterEqual(g.me["y"], ah.TL / 2 + ah.PAD_R - 0.01)
        self.assertLess(fastest, -150)                             # sent up the table

    def test_goals_at_each_end(self):
        g, inp = self.game()
        g.wait = 0
        g.her.update(x=20.0, y=60.0)
        g.two = True                                               # nobody steers her paddle
        g.puck.update(x=ah.TW / 2, y=20.0, vx=0.0, vy=-300.0)
        self.run_frames(g, inp, 10)
        self.assertEqual((g.you, g.rose), (1, 0))
        self.assertEqual(g.mood, "oops")
        self.assertLess(g.puck["y"], ah.TL / 2)                    # served to the one scored on
        g.wait = 0
        g.me.update(x=20.0, y=ah.TL - 60)
        g.puck.update(x=ah.TW / 2, y=ah.TL - 20, vx=0.0, vy=300.0)
        self.run_frames(g, inp, 10)
        self.assertEqual((g.you, g.rose), (1, 1))
        g.wait = 0
        g.puck.update(x=20.0, y=20.0, vx=0.0, vy=-300.0)           # off the end rail, not in the goal
        self.run_frames(g, inp, 10)
        self.assertEqual((g.you, g.rose), (1, 1))

    def test_first_to_five_wins(self):
        g, inp = self.game(mode=2)
        g.you = ah.WIN - 1
        g.goal(mine=True)
        self.assertEqual(g.phase, "end")
        self.assertEqual(g.line, "Fine. Best of three?")
        self.run_frames(g, inp, 240)
        self.assertEqual(g.state, "over")
        self.assertTrue(g.win)
        self.assertGreater(g.last_score, 500)

    def test_momma_rose_beats_someone_who_never_moves(self):
        for mode in (0, 1, 2):
            g, inp = self.game(mode=mode, seed=5 + mode)
            g.me.update(x=24.0, y=ah.TL - 20)                      # parked in the corner
            self.run_frames(g, inp, 60 * 240)
            self.assertEqual(g.rose, ah.WIN, "mode %d: %d-%d" % (mode, g.you, g.rose))
            self.assertFalse(g.win)

    def test_two_players(self):
        g, inp = self.game()
        inp.p2 = common.Input()
        inp.p2.down("a")
        g.step(DT, inp)
        inp.p2.end_frame()
        self.assertTrue(g.two)
        x = g.her["x"]
        inp.p2.down("right")
        self.run_frames(g, inp, 20)
        self.assertGreater(g.her["x"], x + 20)
        self.assertLessEqual(g.her["y"], ah.TL / 2 - ah.PAD_R + 0.01)


if __name__ == "__main__":
    unittest.main()
