"""Scary Babies: walking, ladders, jumping babies, rattle, dying, clearing a board."""
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
    from core.games import common, scary_babies as sb
    from core import extras
    HAVE_PYGAME = True
except Exception:
    HAVE_PYGAME = False

DT = 1 / 60


@unittest.skipUnless(HAVE_PYGAME, "pygame not installed")
class ScaryBabiesTests(unittest.TestCase):
    def setUp(self):
        fd, self.scores = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(self.scores)
        self.canvas = pygame.Surface((common.W, common.H))
        self.game = sb.make(seed=2, scores_path=self.scores)
        self.inp = common.Input()
        self.run_frames(1, "a")
        self.game.throw_t = 999          # no babies unless a test adds them

    def tearDown(self):
        if os.path.exists(self.scores):
            os.unlink(self.scores)

    def run_frames(self, n, *held):
        for b in held:
            self.inp.down(b)
        for _ in range(n):
            self.game.step(DT, self.inp)
            self.game.render(self.canvas)
            self.inp.end_frame()
        for b in held:
            self.inp.up(b)

    def test_layout_ladders_join_girders(self):
        for lx, lo in sb.LADDERS:
            for g in (sb.GIRDERS[lo], sb.GIRDERS[lo + 1]):
                self.assertTrue(g.x0 <= lx <= g.x1, (lx, lo))
        for i in range(1, 5):            # each girder's low end overhangs the one below
            g, below = sb.GIRDERS[i], sb.GIRDERS[i - 1]
            end = g.x1 if g.down_dir > 0 else g.x0
            self.assertTrue(below.x0 <= end <= below.x1, i)

    def test_walk_and_climb_to_the_top_clears_board(self):
        g = self.game
        g.safe = 0
        for lx, lo in [(120, 0), (90, 1), (160, 2), (100, 3), (190, 4)]:
            self.assertEqual(g.g, lo)
            while abs(g.px - lx) > 2:
                self.run_frames(1, "right" if g.px < lx else "left")
            self.run_frames(150, "up")
        self.assertEqual(g.state_p, "cleared")
        self.run_frames(400)
        self.assertGreaterEqual(g.score, 4000)          # the bonus is added to the score
        self.assertEqual(g.board, 2)
        self.assertEqual(g.g, 0)

    def baby_at(self, x, girder=0, direction=-1):
        b = {"x": float(x), "y": sb.GIRDERS[girder].y_at(x), "g": girder, "dir": direction, "st": "roll",
             "vy": 0.0, "spin": 0.0, "jumped": False, "crawl": 0.0, "ladders": set()}
        self.game.babies.append(b)
        return b

    def test_baby_hit_costs_a_life(self):
        g = self.game
        g.safe = 0
        self.baby_at(g.px + 8)
        self.run_frames(10)
        self.assertEqual(g.state_p, "dying")
        self.assertEqual(g.lives, 2)
        self.run_frames(110)
        self.assertEqual(g.state_p, "walk")
        self.assertEqual(g.babies, [])

    def test_jumping_a_baby_scores(self):
        g = self.game
        g.safe = 0
        self.baby_at(g.px + 30)
        self.run_frames(8)
        self.run_frames(1, "a")
        self.run_frames(40)
        self.assertNotEqual(g.state_p, "dying")
        self.assertGreaterEqual(g.score, 100)

    def test_rattle_bonks_babies_and_blocks_ladders(self):
        g = self.game
        g.safe = 0
        g.rattle = 5
        g.facing = 1
        self.baby_at(g.px + 30)
        self.run_frames(20)
        self.assertEqual(g.babies, [])
        self.assertGreaterEqual(g.score, 300)
        g.px = 120.0
        self.run_frames(20, "up")
        self.assertEqual(g.state_p, "walk")

    def test_boss_throws_and_babies_reach_the_floor(self):
        g = self.game
        g.throw_t = 0
        g.safe = 999
        seen_floor = False
        for _ in range(60 * 30):
            g.step(DT, self.inp)
            seen_floor |= any(b["g"] == 0 for b in g.babies)
        self.assertTrue(seen_floor)

    def test_game_over_after_three_lives(self):
        g = self.game
        for _ in range(3):
            g.safe = 0
            self.baby_at(g.px + 6)
            self.run_frames(110)
        self.assertEqual(g.state, "over")

    def test_later_boards_are_harder(self):
        g = self.game
        s1, c1 = g.baby_speed, g.ladder_chance
        g.board = 5
        self.assertGreater(g.baby_speed, s1)
        self.assertGreater(g.ladder_chance, c1)

    def test_voice(self):
        self.assertEqual(extras.match_game("play scary babies"), "scary_babies")

    def test_stephen_has_things_to_say(self):
        for line in ("Hey Victor, come look at this...", "AI can't do my job.", "First thing tomorrow, Lynn is out of here..."):
            self.assertIn(line, sb.STEPHEN_LINES)
        heard = set()
        for _ in range(60 * 40):
            self.game.safe = 999
            self.game.step(DT, self.inp)
            self.inp.end_frame()
            if self.game.quip_t > 0:
                heard.add(self.game.quip)
        self.assertGreaterEqual(len(heard & set(sb.STEPHEN_LINES)), 3)
        self.game.say("First thing tomorrow, Lynn is out of here...")
        self.game.px = common.W - 4                       # the bubble stays on the screen at the edge
        self.game.render(self.canvas)
        self.game.lose_life()
        self.assertIn(self.game.quip, sb.STEPHEN_OUCH)


if __name__ == "__main__":
    unittest.main()
