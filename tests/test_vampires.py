"""Vampires, Oh Well...: the floors, the fighting, the cards and the second hunter."""
import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("BMO_GAME_SOUND", "0")

try:
    import pygame
    from core import extras
    from core.games import GAMES, common
    from core.games.vampires import art, cards, game as G, levels, scenes
    OK = True
except ImportError:  # pragma: no cover
    OK = False


def new(stage=0, mode=1, scenes_on=False):
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((800, 480))
    g = G.Vampires(seed=4, scores_path=os.path.join(tempfile.mkdtemp(), "s.json"))
    g.scenes_on = scenes_on
    g.unlocked, g.level_choice, g.mode = 5, stage, mode
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
class TestVampires(unittest.TestCase):
    def test_floors_are_fair_and_always_the_same(self):
        self.assertEqual(len(levels.STAGES), 5)
        for i in range(5):
            a, b = levels.build(i), levels.build(i)
            self.assertEqual(a, b)
            self.assertEqual(a["ground"][0][0], 0)
            self.assertEqual(a["ground"][-1][1], a["length"])
            for (_, end), (start, _) in zip(a["ground"], a["ground"][1:]):
                self.assertLessEqual(start - end, 50)                       # every hole can be jumped
                self.assertLess(end, a["length"] - levels.ARENA)            # and none is in the boss room
            self.assertEqual(len(a["chests"]), 2)
            self.assertTrue(all(k in G.BEASTS for _, k in a["spawns"]))

    def test_walking_jumping_and_ledges(self):
        g, inp = new()
        g.level["spawns"] = []
        p = g.players[0]
        x0 = p.x
        inp.held = {"right"}
        run(g, inp, 1.0)
        self.assertGreater(p.x, x0 + 60)
        inp.held = set()
        inp.pressed = {"a"}
        g.step(1 / 60, inp)
        self.assertFalse(p.ground)
        top = p.y
        for _ in range(120):
            g.step(1 / 60, inp)
            inp.pressed = set()
            top = min(top, p.y)
        self.assertTrue(p.ground)
        self.assertLess(top, levels.FLOOR - 50)                              # high enough to reach a ledge
        lx, ly, lw = g.level["ledges"][0]
        p.x, p.y, p.vy, p.ground = lx + lw / 2, ly - 20.0, 0.0, False
        g.cam = max(0.0, p.x - 150)
        run(g, inp, 0.5)
        self.assertEqual((p.y, p.ground), (ly, True))
        inp.held = {"down"}
        inp.pressed = {"a"}
        run(g, inp, 0.8)
        self.assertEqual(p.y, levels.FLOOR)

    def test_attack_hurts_and_monsters_bite_back(self):
        g, inp = new()
        p = g.players[0]
        g.spawn_beast("zombie", p.x + 26)
        z = g.beasts[-1]
        hp = z.hp
        inp.pressed = {"b"}
        g.step(1 / 60, inp)
        self.assertLess(z.hp, hp)
        g.beasts = []
        g.spawn_beast("zombie", p.x + 2)
        run(g, inp, 0.1)
        self.assertEqual(p.hp, G.MAX_HP - 1)
        self.assertGreater(p.inv, 0)

    def test_a_chest_gives_a_card_that_stops_play_and_turns_over(self):
        g, inp = new()
        p = g.players[0]
        g.take_card(p, "coffee")
        self.assertTrue(g.found >> cards.KEYS.index("coffee") & 1)
        x = p.x
        inp.held = {"right"}
        run(g, inp, 0.6)
        self.assertEqual(p.x, x)                                             # play is paused
        inp.pressed = {"a"}
        run(g, inp, 0.6)
        self.assertGreaterEqual(g.cardview["turn"], 0.99)
        inp.pressed = {"a"}
        g.step(1 / 60, inp)
        self.assertIsNone(g.cardview)
        self.assertEqual(p.card, "coffee")
        inp.held = {"up"}
        inp.pressed = {"b"}
        g.step(1 / 60, inp)
        self.assertIn("coffee", p.fx)
        self.assertIsNone(p.card)
        saved = common.load_scores(g.scores_path)
        self.assertEqual(saved["vampires_cards"], g.found)

    def test_a_swing_from_the_same_floor_opens_a_chest_and_the_card_can_be_picked_up(self):
        g, inp = new()
        g.level["spawns"] = []
        p = g.players[0]
        for side in (1, -1):                                     # from the left of it, then from the right
            g.chests = [[int(p.x) + side * 24, levels.FLOOR], None]
            g.drops = []
            p.face, p.cool = side, 0.0
            inp.pressed = {"b"}
            g.step(1 / 60, inp)
            inp.pressed = set()
            self.assertIsNone(g.chests[0], side)
            self.assertEqual([d["kind"] for d in g.drops], ["card"])
            run(g, inp, 0.5)
        inp.held = {"left"}
        for _ in range(120):
            g.step(1 / 60, inp)
            if g.cardview:
                break
        self.assertIsNotNone(g.cardview)

    def test_each_card_does_what_it_says(self):
        g, inp = new()
        p = g.players[0]
        g.spawn_beast("vampire", p.x + 120)
        v = g.beasts[-1]
        p.card = "dawn"
        g.play_card(p)
        self.assertTrue(v.dead or v.hp < v.max_hp)
        p.card = "stapler"
        g.play_card(p)
        self.assertEqual(p.staples, 30)
        inp.pressed = {"b"}
        g.step(1 / 60, inp)
        self.assertTrue(any(s["kind"] == "staple" for s in g.shots))
        p.card = "bat"
        g.play_card(p)
        hp = p.hp
        g.hurt(p, 3, p.x + 5)
        self.assertEqual(p.hp, hp)                                           # nothing can hurt a bat
        p.fx = {}
        p.inv = 0
        g.cardview = dict(key="rosary", p=p, turn=1.0, target=1.0, t=1.0)
        g.close_card()
        g.hurt(p, 99, p.x + 5)
        self.assertEqual((p.hp, p.rosary, p.lives), (G.MAX_HP, False, G.LIVES))
        g.cardview = dict(key="fire", p=p, turn=1.0, target=1.0, t=1.0)
        g.close_card()
        self.assertEqual(p.damage(), 2)
        for key in cards.KEYS:                                               # every card has a front and a back
            self.assertEqual(cards.front(key).get_size(), (cards.CW, cards.CH))
            self.assertEqual(cards.back(key).get_size(), (cards.CW, cards.CH))

    def test_the_boss_room_and_clearing_a_floor(self):
        g, inp = new()
        p = g.players[0]
        g.cam = g.level["length"] - 400.0
        p.x = g.level["length"] - 200.0
        p.safe = (p.x, p.y)
        run(g, inp, 0.2)
        self.assertTrue(g.boss_on)
        boss = [b for b in g.beasts if b.boss]
        self.assertEqual(len(boss), 1)
        p.inv = 999
        for b in boss:
            g.wound(b, 999, p)
        run(g, inp, 4.0)
        self.assertEqual((g.stage, g.boss_on), (1, False))
        self.assertEqual(g.unlocked, 5)

    def test_lucas_says_his_line_and_the_last_boss_wins_the_game(self):
        g, inp = new(stage=4)
        p = g.players[0]
        g.cam = g.level["length"] - 400.0
        p.x = g.level["length"] - 200.0
        run(g, inp, 0.2)
        p.inv = 999
        for b in list(g.beasts):
            if b.boss:
                g.wound(b, 999, p)
        run(g, inp, 0.1)
        self.assertEqual(g.say_line, "I don't really care about winning, but I still win. Sheesh.")
        run(g, inp, 4.0)
        self.assertEqual((g.state, g.win, g.finished), ("over", True, True))

    def test_second_hunter_joins_as_angry_poppa_and_losing_every_life_ends_it(self):
        g, inp = new()
        inp.p2 = common.Input()
        inp.p2.pressed = {"a"}
        g.step(1 / 60, inp)
        self.assertEqual([p.kind for p in g.players], ["lucas", "poppa"])
        inp.p2.pressed = set()
        x = g.players[1].x
        inp.p2.held = {"right"}
        run(g, inp, 0.5)
        self.assertGreater(g.players[1].x, x)
        self.assertGreater(art.HUNTERS["poppa"]["damage"], art.HUNTERS["lucas"]["damage"])
        for p in g.players:
            p.lives = 1
            p.inv = 0
            g.hurt(p, 99, p.x + 5, force=True)
        self.assertEqual(g.state, "over")

    def test_roster_grows_album_opens_and_everything_draws(self):
        g = G.Vampires(seed=1, scores_path=os.path.join(tempfile.mkdtemp(), "s.json"))
        screen = pygame.display.set_mode((800, 480))
        canvas = pygame.Surface((common.W, common.H))
        self.assertEqual(g.roster(), ("lucas", "poppa"))
        g.unlocked = 5
        self.assertEqual(len(g.roster()), 8)
        res = common.run(g, screen=screen, max_frames=20)                    # the title in the real loop
        self.assertEqual(res["game"], "vampires")
        inp = common.Input()
        inp.pressed = {"b"}
        g.step(1 / 60, inp)
        self.assertIsNotNone(g.album)
        g.render(canvas); g.render_hd(screen)
        inp.pressed = {"right"}
        g.step(1 / 60, inp)
        self.assertEqual(g.album[0], 1)
        inp.pressed = {"b"}
        g.step(1 / 60, inp)
        self.assertIsNone(g.album)
        g, inp = new(scenes_on=True)
        self.assertIsNotNone(g.scene)
        for n in range(len(scenes.SHOTS)):
            for t in (0.0, 1.0, 3.5, 6.0):
                scenes.shot(screen, n, t)
        inp.pressed = {"b"}
        g.step(1 / 60, inp)
        self.assertIsNone(g.scene)
        for stage in range(5):
            g.start_stage(stage)
            g.cam = g.level["length"] - 400.0
            g.players[0].x = g.level["length"] - 200.0
            for kind in G.BEASTS:
                g.spawn_beast(kind, g.players[0].x + 60)
            for _ in range(30):
                g.step(1 / 60, inp)
                inp.pressed = set()
                g.render(canvas); g.render_hd(screen)
        for kind in art.ROSTER:
            for pose in ("stand", "walk", "jump", "attack", "hurt", "bat"):
                self.assertEqual(art.hunter(kind, pose).get_size(), (art.HW, art.HH))

    def test_registered_and_heard(self):
        self.assertIn("vampires", GAMES)
        for said in ("play vampires oh well", "let's play the vampire game", "play lucas's game", "start the monster game"):
            self.assertEqual(extras.match_game(said), "vampires", said)
        self.assertEqual(extras.match_game("play the big move"), "big_move")
        self.assertEqual(extras.match_game("play scary babies"), "scary_babies")


if __name__ == "__main__":
    unittest.main()
