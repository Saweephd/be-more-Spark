"""Scary Babies: climb to the top while Big Baby rolls scary babies down the girders.

    D-pad left/right  walk        up/down  climb ladders
    big circle        jump        (jumping a baby scores points)
Grab a rattle to bonk babies for a few seconds (no climbing while you hold it).
Reach the EXIT at the top to clear the board. Each board is faster and busier.
Three lives.

Inspired by the classic barrel-climbing arcade game; all characters, art, sounds
and music here are original to this project.
"""
import math

import pygame

from . import common as c
from .common import H, W, Game, sprite, text


class Girder:
    def __init__(self, x0, x1, yl, yr, down_dir):
        self.x0, self.x1, self.yl, self.yr, self.down_dir = x0, x1, yl, yr, down_dir

    def y_at(self, x):
        x = max(self.x0, min(self.x1, x))
        return self.yl + (self.yr - self.yl) * (x - self.x0) / float(self.x1 - self.x0)


# girder 0 is the floor; babies roll downhill on each one and drop off the low end
GIRDERS = [
    Girder(0, 400, 226, 226, 1),
    Girder(50, 390, 184, 176, -1),
    Girder(10, 350, 136, 144, 1),
    Girder(50, 390, 104, 96, -1),
    Girder(10, 330, 58, 66, 1),
    Girder(150, 236, 26, 26, 1),     # the exit platform
]
LADDERS = [(120, 0), (340, 0), (90, 1), (250, 1), (160, 2), (300, 2), (100, 3), (230, 3), (190, 4)]  # (x, lower girder)
RATTLES = [(300, 1), (140, 3)]
START_X = 30
BOSS_X = 34

PAL = {"Y": (250, 222, 110), "y": (214, 176, 70), "s": (242, 204, 176), "S": (210, 168, 140), "k": (24, 24, 30),
       "g": (60, 170, 120), "G": (40, 120, 86), "j": (64, 96, 176), "J": (44, 66, 130), "w": (250, 250, 250)}
STEPHEN_TOP = [
    "...YYYYY....",
    "..YYYYYYY...",
    "..YYYYYYYY..",
    "..YYsssss...",
    "..Ysskssk...",
    "...sssssS...",
    "...ssSSs....",
    "....ss......",
    "..gggggggg..",
    ".ggggggggggs",
    "sgggggggggs.",
    "s.gggggggg..",
    "..GGGGGGGG..",
    "..jjjjjjjj..",
]
LEGS_A = ["..jjjJjjjj..", "..jjj..jjj..", "..jjj..jjj..", "..jjj..jjj..", "..kkk..kkk..", "............"]
LEGS_B = ["..jjjJjjjj..", "..jjj...jj..", ".jjj.....jj.", ".jjj.....jjj", ".kkk.....kkk", "............"]
BACK_TOP = ["...YYYYY....", "..YYYYYYY...", "..YYYYYYYY..", "..YYYYYYYY..", "..YYYYYYYY..", "...YYYYYY...", "...ssSSs....",
            "....ss......", "s.gggggggg.s", "sgggggggggg.", ".gggggggggs.", "..gggggggg..", "..GGGGGGGG..", "..jjjjjjjj.."]

# A cracked porcelain doll baby: hollow eyes with red pinpoints and a grin full of little teeth.
BPAL = {"p": (226, 222, 212), "P": (160, 156, 162), "e": (255, 34, 34), "k": (14, 10, 16), "C": (96, 84, 96),
        "w": (250, 248, 236)}
BABY = [
    "....kk.k....",
    "..ppppppCp..",
    ".pppppppCpp.",
    ".pkkkppkkkCp",
    "ppkekppkekpp",
    "ppkkkppkkkPp",
    "pCpppppppppp",
    "ppkwkwkwkwpp",
    ".ppkkkkkkpp.",
    ".PPpppppppP.",
    "..PPPCPPPP..",
    "....PPPP....",
]

KPAL = {"n": (150, 104, 124), "N": (104, 64, 88), "p": (222, 216, 206), "P": (156, 150, 158), "e": (255, 34, 34),
        "k": (14, 10, 16), "r": (170, 96, 110), "m": (120, 16, 36), "d": (230, 226, 214), "D": (176, 170, 178),
        "C": (90, 78, 92), "w": (250, 248, 236)}
_BOSS_ROWS = [
    "nnnnnnnnnnnn", "nnnnnnnnnnnnnnnn", "nnNNNNNNNNNNNNNNnn", "nnNppppppCpppppppNnn", "nNpppppppCCppppppNn",
    "nNpkkkkpppppCpkkkkpNn", "NpkkekkppppkkekkpN", "ppkkkkpppppCkkkkpp", "prrpppppppppppCrrp",
    "pppmmmmmmmmmmmmppp", "ppmwkwkwkwkwkwkmpp", "pppmkwkwkwkwkwmppp", "pppppmmmmmmmmppppp",
    "PppppppppppppppppP", "pppPppppppppppppPppp", "pppPppppppppppppPppp", "ppp.dddddddddddd.ppp",
    "pp..dddddddddddd..pp", "....dddDDDDDDddd....", "....dddddddddddd....", "....ppp......ppp....",
    "...pppp......pppp...", "...PPPP......PPPP...",
]
BOSS = [r.center(22, ".") for r in _BOSS_ROWS]


class ScaryBabies(Game):
    levels = tuple("Board %d" % (i + 1) for i in range(8))
    name = "scary_babies"
    title = "Scary Babies"
    music = "scary_babies"
    help_lines = ("D-pad: walk and climb   Big button: jump", "Jump the babies, grab a rattle to bonk them",
                  "Reach the EXIT at the top!")
    title_color = (250, 150, 200)

    def __init__(self, **kw):
        super().__init__(**kw)
        walk_a = sprite(STEPHEN_TOP + LEGS_A, PAL)
        walk_b = sprite(STEPHEN_TOP + LEGS_B, PAL)
        self.frames = {"a": walk_a, "b": walk_b, "back": sprite(BACK_TOP + LEGS_A, PAL),
                       "back2": c.flip(sprite(BACK_TOP + LEGS_A, PAL))}
        base = sprite(BABY, BPAL)
        self.baby_frames = [pygame.transform.rotate(base, a) for a in (0, 90, 180, 270)]
        self.boss = sprite(BOSS, KPAL, 2)
        self.life_icon = sprite(STEPHEN_TOP[:8], PAL)
        self.reset()

    # ----- setup -----
    def reset(self):
        self.score = 0
        self.lives = 3
        self.board = self.level_choice + 1
        self.start_board()

    def start_board(self):
        self.px, self.g = float(START_X), 0
        self.state_p = "walk"          # walk, climb, jump, dying, cleared
        self.ladder = None
        self.py = GIRDERS[0].y_at(self.px)
        self.vy = 0.0
        self.vx = 0.0
        self.facing = 1
        self.anim = 0.0
        self.babies = []
        self.pops = []
        self.rattle = 0.0
        self.rattles = [list(r) + [True] for r in RATTLES]
        self.throw_t = 1.6
        self.hold = 0.0
        self.bonus = 5000
        self.bonus_t = 0.0
        self.safe = 1.5
        self.timer = 0.0
        self.flicker = 0.0
        self.flicker_t = 4.0
        self.redflash = 0.0
        self.peepers = [[(i * 97 + 23) % (W - 20) + 10, (i * 53) % 90 + 20, (i * 1.7) % 5.0] for i in range(6)]

    @property
    def baby_speed(self):
        return min(125, 58 + 11 * (self.board - 1))

    @property
    def ladder_chance(self):
        return min(0.55, 0.2 + 0.07 * (self.board - 1))

    # ----- update -----
    def update(self, dt, inp):
        self.timer += dt
        self.pops = [[x, y - 20 * dt, m, t - dt] for x, y, m, t in self.pops if t > dt]
        if self.state_p == "dying":
            self.anim += dt
            if self.anim > 1.6:
                if self.lives <= 0:
                    self.game_over()
                else:
                    self.start_board()
            return
        if self.state_p == "cleared":
            self.anim += dt
            if self.bonus > 0:
                step = min(self.bonus, int(4000 * dt) // 100 * 100 or 100)
                self.bonus -= step
                self.score += step
            elif self.anim > 2.2:
                self.board += 1
                self.reach_level(self.board - 1)
                self.start_board()
            return
        self.safe = max(0.0, self.safe - dt)
        self.update_spooks(dt)
        self.bonus_t += dt
        if self.bonus_t >= 2.0:
            self.bonus_t -= 2.0
            self.bonus = max(0, self.bonus - 100)
        self.rattle = max(0.0, self.rattle - dt)
        self.update_player(dt, inp)
        self.update_boss(dt)
        self.update_babies(dt)

    def update_spooks(self, dt):
        """The lights stutter now and then, and red eyes open and shut in the dark."""
        self.flicker = max(0.0, self.flicker - dt)
        self.redflash = max(0.0, self.redflash - dt)
        self.flicker_t -= dt
        if self.flicker_t <= 0:
            self.flicker = 0.45
            self.flicker_t = self.rng.uniform(5.0, 11.0)
            if self.rng.random() < 0.6:
                self.sfx("giggle")
        for pe in self.peepers:
            pe[2] -= dt
            if pe[2] < -1.2:                    # eyes shut; open somewhere else later
                pe[0] = self.rng.randrange(10, W - 10)
                pe[1] = self.rng.randrange(20, 110)
                pe[2] = self.rng.uniform(2.0, 6.0)

    def ladder_here(self, lower=None, upper=None):
        for lx, lo in LADDERS:
            if abs(self.px - lx) <= 5 and (lower is None or lo == lower) and (upper is None or lo + 1 == upper):
                return (lx, lo)
        return None

    def update_player(self, dt, inp):
        gd = GIRDERS[self.g]
        if self.state_p == "walk":
            move = (1 if "right" in inp.held else 0) - (1 if "left" in inp.held else 0)
            if move:
                self.facing = move
                self.anim += dt
            self.px = max(gd.x0 + 4, min(gd.x1 - 4, self.px + move * 62 * dt))
            self.py = gd.y_at(self.px)
            if "up" in inp.held and self.rattle <= 0:
                ld = self.ladder_here(lower=self.g)
                if ld:
                    self.state_p, self.ladder, self.px = "climb", ld, float(ld[0])
            elif "down" in inp.held and self.rattle <= 0:
                ld = self.ladder_here(upper=self.g)
                if ld:
                    self.state_p, self.ladder, self.px = "climb", ld, float(ld[0])
            if "a" in inp.pressed and self.state_p == "walk":
                self.state_p, self.vy, self.vx = "jump", -165.0, move * 62
                self.sfx("jump")
        elif self.state_p == "climb":
            lx, lo = self.ladder
            top, bot = GIRDERS[lo + 1].y_at(lx), GIRDERS[lo].y_at(lx)
            dy = (1 if "down" in inp.held else 0) - (1 if "up" in inp.held else 0)
            if dy:
                self.anim += dt
            self.py += dy * 42 * dt
            if self.py <= top:
                self.py, self.g, self.state_p = top, lo + 1, "walk"
                if self.g == len(GIRDERS) - 1:
                    self.clear_board()
            elif self.py >= bot:
                self.py, self.g, self.state_p = bot, lo, "walk"
        elif self.state_p == "jump":
            self.vy += 480 * dt
            self.px = max(gd.x0 + 4, min(gd.x1 - 4, self.px + self.vx * dt))
            self.py += self.vy * dt
            floor = gd.y_at(self.px)
            if self.vy > 0 and self.py >= floor:
                self.py, self.state_p = floor, "walk"
        # rattles hang above the girder; touch one to take it
        for r in self.rattles:
            rx, rg, here = r
            if here and rg == self.g and abs(self.px - rx) < 8 and self.py - 18 < GIRDERS[rg].y_at(rx) - 20:
                r[2] = False
                self.rattle = 8.0
                self.sfx("powerup")
                self.pops.append([rx, GIRDERS[rg].y_at(rx) - 30, "RATTLE!", 1.0])

    def clear_board(self):
        self.state_p, self.anim = "cleared", 0.0
        self.babies = []
        self.sfx("clear")
        self.pops.append([self.px, self.py - 30, "SAFE!", 1.5])

    def update_boss(self, dt):
        if self.hold > 0:
            self.hold -= dt
            if self.hold <= 0:
                gd = GIRDERS[4]
                self.babies.append({"x": BOSS_X + 28.0, "y": gd.y_at(BOSS_X + 28), "g": 4, "dir": 1, "st": "roll",
                                    "vy": 0.0, "spin": 0.0, "jumped": False, "crawl": 0.0, "ladders": set()})
                self.sfx("throw")
            return
        self.throw_t -= dt
        if self.throw_t <= 0:
            base = max(1.15, 3.0 - 0.32 * (self.board - 1))
            self.throw_t = base * self.rng.uniform(0.75, 1.3)
            self.hold = 0.55

    def update_babies(self, dt):
        speed = self.baby_speed
        for b in self.babies:
            b["spin"] += dt * speed / 6.0
            gd = GIRDERS[b["g"]]
            if b["st"] == "roll":
                b["x"] += b["dir"] * speed * dt
                for lx, lo in LADDERS:      # sometimes take a ladder down
                    if lo + 1 == b["g"] and abs(b["x"] - lx) < 2 and lx not in b["ladders"]:
                        b["ladders"].add(lx)
                        if self.rng.random() < self.ladder_chance:
                            b["st"], b["x"], b["lad"] = "ladder", float(lx), lo
                            break
                if b["st"] == "roll":
                    if b["x"] > gd.x1 or b["x"] < gd.x0:
                        if b["g"] == 0:
                            b["gone"] = True
                        else:
                            b["st"], b["vy"] = "fall", 0.0
                    else:
                        b["y"] = gd.y_at(b["x"])
            elif b["st"] == "ladder":
                b["y"] += 60 * dt
                low = GIRDERS[b["lad"]]
                if b["y"] >= low.y_at(b["x"]):
                    self.land(b, b["lad"])
            elif b["st"] == "fall":
                b["vy"] += 500 * dt
                b["y"] += b["vy"] * dt
                b["x"] += b["dir"] * 25 * dt
                low = GIRDERS[b["g"] - 1]
                if b["y"] >= low.y_at(b["x"]):
                    self.land(b, b["g"] - 1)
            elif b["st"] == "crawl":
                b["crawl"] -= dt
                d = 1 if self.px > b["x"] else -1
                lurch = 0.25 + 1.75 * max(0.0, math.sin(b["crawl"] * 7.0)) ** 2   # creep, creep, LUNGE
                b["x"] += d * 34 * lurch * dt
                b["dir"] = d
                b["y"] = GIRDERS[b["g"]].y_at(b["x"])
                if b["crawl"] <= 0:
                    b["st"], b["dir"] = "roll", 1
            self.check_baby(b)
        self.babies = [b for b in self.babies if not b.get("gone")]

    def land(self, b, g):
        b["g"] = g
        b["y"] = GIRDERS[g].y_at(b["x"])
        b["dir"] = GIRDERS[g].down_dir
        b["st"] = "roll"
        if g == 0 and self.board >= 2 and self.rng.random() < min(0.5, 0.15 * (self.board - 1)):
            b["st"], b["crawl"] = "crawl", 8.0
            self.sfx("giggle")

    def check_baby(self, b):
        if self.state_p in ("dying", "cleared") or b.get("gone"):
            return
        bx, by = b["x"], b["y"] - 6
        # player box: 10 wide, 18 tall above the feet
        nx = max(self.px - 5, min(self.px + 5, bx))
        ny = max(self.py - 18, min(self.py - 1, by))
        touching = (nx - bx) ** 2 + (ny - by) ** 2 < 36
        if self.rattle > 0 and abs(bx - (self.px + self.facing * 10)) < 11 and abs(by - (self.py - 9)) < 12:
            b["gone"] = True
            self.score += 300
            self.sfx("bonk")
            self.pops.append([bx, by - 10, "WAAH! 300", 1.0])
            return
        if touching and self.safe <= 0:
            self.lose_life()
            return
        if (self.state_p == "jump" and not b["jumped"] and abs(bx - self.px) < 7 and self.py < by - 4
                and b["g"] == self.g):
            b["jumped"] = True
            self.score += 100
            self.sfx("coin")
            self.pops.append([bx, by - 16, "100", 0.8])

    def lose_life(self):
        self.redflash = 0.5
        self.lives -= 1
        self.state_p, self.anim = "dying", 0.0
        self.sfx("hurt" if self.lives > 0 else "giggle")

    # ----- draw -----
    def draw_title_art(self, surf):
        self.draw(surf)

    def draw(self, surf):
        surf.fill((26, 18, 44))
        for i in range(30):
            x, y = (i * 137) % W, (i * 71) % 120 + 4
            surf.set_at((x, y), (200, 200, 230))
        pygame.draw.circle(surf, (240, 236, 200), (360, 30), 12)
        pygame.draw.circle(surf, (26, 18, 44), (366, 26), 11)
        for x, y, t in self.peepers:            # something watching from the dark
            if t > 0 and not (0.0 < t % 2.3 < 0.12):
                for ex in (x - 3, x + 3):
                    pygame.draw.circle(surf, (110, 0, 10), (ex, y), 2)
                    surf.set_at((ex, y), (255, 60, 60))
        for lx, lo in LADDERS:
            top, bot = GIRDERS[lo + 1].y_at(lx), GIRDERS[lo].y_at(lx)
            pygame.draw.line(surf, (110, 200, 230), (lx - 5, top), (lx - 5, bot), 2)
            pygame.draw.line(surf, (110, 200, 230), (lx + 5, top), (lx + 5, bot), 2)
            y = top + 4
            while y < bot:
                pygame.draw.line(surf, (110, 200, 230), (lx - 5, y), (lx + 5, y))
                y += 6
        for i, gd in enumerate(GIRDERS):
            pts = [(gd.x0, gd.yl), (gd.x1, gd.yr), (gd.x1, gd.yr + 6), (gd.x0, gd.yl + 6)]
            pygame.draw.polygon(surf, (220, 70, 120), pts)
            x = gd.x0
            while x < gd.x1 - 6:
                y = gd.y_at(x)
                pygame.draw.line(surf, (150, 40, 80), (x, y + 6), (x + 6, y), 1)
                x += 6
        ex = 193
        pygame.draw.rect(surf, (60, 200, 110), (ex - 14, 6, 28, 18), border_radius=3)
        text(surf, "EXIT", (ex, 10), 16, c.WHITE, center=True)
        for rx, rg, here in self.rattles:
            if here:
                y = GIRDERS[rg].y_at(rx) - 26
                pygame.draw.line(surf, (240, 200, 80), (rx, y), (rx, y + 8), 2)
                pygame.draw.circle(surf, (250, 120, 200), (int(rx), int(y)), 4)
        self.draw_boss(surf)
        for b in self.babies:
            img = self.baby_frames[int(b["spin"]) % 4] if b["st"] in ("roll", "fall") else self.baby_frames[0]
            bx, by = int(b["x"]), int(b["y"])
            if b["st"] == "crawl":
                if int(self.timer * 6) % 2:
                    img = c.flip(img)
                bx += int(math.sin(self.timer * 50) * 1.5)      # twitching
                self.glow(surf, bx, by - 6, 9, (255, 30, 30), 70)
            else:
                self.glow(surf, bx, by - 6, 7, (255, 30, 30), 35)
            surf.blit(img, (bx - 6, by - 12))
        self.draw_player(surf)
        self.draw_dark(surf)
        for x, y, m, t in self.pops:
            text(surf, m, (int(x), int(y)), 16, c.YELLOW, center=True)
        text(surf, "%d" % int(self.score), (6, 2), 18, c.WHITE)
        text(surf, "BOARD %d" % self.board, (W // 2 - 70, 2), 16, (250, 160, 210))
        text(surf, "BONUS %d" % self.bonus, (W - 100, 2), 16, c.YELLOW)
        for i in range(max(0, self.lives)):
            surf.blit(self.life_icon, (W - 112 - i * 14, 16))
        if self.state_p == "cleared":
            text(surf, "BOARD CLEAR!", (W // 2, 96), 34, c.YELLOW, center=True)

    def glow(self, surf, x, y, r, col, alpha):
        g = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for k in range(3):
            pygame.draw.circle(g, col + (alpha // 3,), (r, r), int(r * (1 - k * 0.3)))
        surf.blit(g, (x - r, y - r))

    def draw_dark(self, surf):
        """A vignette, the stuttering lights, and a red flash when Stephen gets got."""
        if not hasattr(self, "_vignette"):
            v = pygame.Surface((W, H), pygame.SRCALPHA)
            for i in range(16):
                a = int(10 * i)
                pygame.draw.rect(v, (0, 0, 0, max(0, 150 - a)), (i * 4, i * 3, W - i * 8, H - i * 6), 4)
            self._vignette = v
        surf.blit(self._vignette, (0, 0))
        if self.flicker > 0 and int(self.flicker * 18) % 3 != 0:
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 165))
            surf.blit(shade, (0, 0))
            for b in self.babies:                # in the dark you only see their eyes
                for ex in (-2, 2):
                    pygame.draw.circle(surf, (255, 40, 40), (int(b["x"]) + ex, int(b["y"]) - 7), 1)
            bx, by = BOSS_X, int(GIRDERS[4].y_at(BOSS_X)) - self.boss.get_height() + 13
            for ex in (-7, 7):
                pygame.draw.circle(surf, (255, 40, 40), (bx + ex, by), 2)
        if self.redflash > 0:
            f = pygame.Surface((W, H), pygame.SRCALPHA)
            f.fill((160, 0, 10, int(160 * self.redflash / 0.5)))
            surf.blit(f, (0, 0))

    def draw_boss(self, surf):
        feet = GIRDERS[4].y_at(BOSS_X)
        bob = int(math.sin(self.timer * 6) * 1)
        bx, by = BOSS_X - 22, int(feet) - self.boss.get_height() + bob
        for ex in (-7, 7):                       # eyes that glow
            self.glow(surf, BOSS_X + ex, by + 13, 6, (255, 30, 30), 90)
        surf.blit(self.boss, (bx, by))
        if self.hold > 0:   # baby held over the head
            surf.blit(self.baby_frames[0], (BOSS_X - 6, by - 10))
            line = ("hee hee hee...", "PLAY WITH US!", "WAAAH!")[int(self.timer / 3) % 3]
            text(surf, line, (BOSS_X + 18, by - 26), 16, (255, 90, 90), center=True)

    def draw_player(self, surf):
        if self.state_p == "dying":
            img = pygame.transform.rotate(self.frames["a"], self.anim * 720)
            r = img.get_rect(center=(int(self.px), int(self.py) - 10))
            surf.blit(img, r)
            return
        if self.state_p == "climb":
            img = self.frames["back" if int(self.anim * 8) % 2 == 0 else "back2"]
        else:
            img = self.frames["b" if (self.state_p == "jump" or int(self.anim * 8) % 2) else "a"]
            if self.facing < 0:
                img = c.flip(img)
        if self.safe > 0 and int(self.timer * 12) % 2:
            return
        surf.blit(img, (int(self.px) - 6, int(self.py) - 20))
        if self.rattle > 0:
            swing = math.sin(self.timer * 18) * 8
            hx = int(self.px + self.facing * 9)
            hy = int(self.py - 14 + swing)
            pygame.draw.line(surf, (240, 200, 80), (int(self.px + self.facing * 4), int(self.py) - 10), (hx, hy), 2)
            pygame.draw.circle(surf, (250, 120, 200), (hx, hy), 4)


def make(**kw):
    return ScaryBabies(**kw)


if __name__ == "__main__":
    c.main(make)
