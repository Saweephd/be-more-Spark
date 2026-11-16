"""Angry Poppa: clear the fungus gnats out of the house.

A side scroller in the look of late 1980s console action games. All art here is
original and drawn in code.

Controls
    D-pad left/right   walk
    D-pad up           jump
    D-pad down         pump the sprayer back up (one pump per tap)
    Big circle (A)     electric fly swatter, close range
    Triangle (B)       bug spray, long range, uses one unit of pressure
    Small circle       pause; hold two seconds to quit

Pickups
    3D printer   an upgrade: swatter reach, swatter power, spray tank, spray spread
    donut        one heart back
    green soda   speed boost for a few seconds

Clear every plant pot (the gnats hatch there), then walk out of the door.
"""
import math

import pygame

from . import common as c
from .common import H, W, Game, sprite, text

FLOOR = 208
GRAVITY = 900.0

HERO_PAL = {"H": (24, 20, 20), "S": (124, 80, 52), "s": (96, 60, 40), "E": (245, 245, 245),
            "J": (34, 38, 60), "j": (58, 64, 98), "W": (240, 240, 244), "T": (190, 40, 50),
            "K": (14, 14, 18)}
_TOP = [
    "......HHHHHH......",
    ".....HHHHHHHH.....",
    "....HHHHHHHHHH....",
    "....HHSSSSSSSS....",
    "....HSSSSSSSSS....",
    "....SSEKSSSEKS....",
    "....SSSSSSSSSS....",
    "....SSSSSssSSS....",
    ".....SSSsssSSS....",
    ".....SSSSSSSSS....",
    "......SSSSSSS.....",
    ".......SSSSS......",
    "...JJJJWWTTWWJJJ..",
    "..JJJJJjWTTWjJJJJ.",
    ".JJJJJJjWTTWjJJJJJ",
    ".JJJJJJJjTTjJJJJJJ",
    ".JJJJJJJJTTJJJJJJJ",
    ".JJJ.JJJJJJJJJ.JJJ",
    ".JJJ.JJJJJJJJJ.JJJ",
    ".SSS.JJJJJJJJJ.SSS",
    ".....JJJJJJJJJ....",
]
_LEGS = {
    "stand": [".....JJJJ.JJJJ...."] * 7 + ["....KKKKK.KKKKK...", "....KKKKK.KKKKKK.."],
    "run1": [".....JJJJJJJJJ....", "....JJJJJ.JJJJJ...", "...JJJJJ...JJJJJ..", "...JJJJ.....JJJJ..", "..JJJJ.......JJJJ.",
             "..JJJJ.......JJJJ.", ".JJJJ.........JJJJ", ".KKKK.........KKKK", ".KKKKK........KKKK"],
    "run2": [".....JJJJJJJJJ....", "......JJJJJJJ.....", "......JJJJJJJ.....", "......JJJJJJ......", "......JJJJJJ......",
             "......JJJJJJ......", "......JJJJJJ......", "......KKKKKK......", "......KKKKKKKK...."],
    "jump": [".....JJJJJJJJJ....", "....JJJJJ.JJJJJ...", "...JJJJJ...JJJJ...", "...JJJJ.....JJJJ..", "...JJJ......JJJJ..",
             "...KKK.......KKK..", "...KKKK......KKKK.", "..................", ".................."],
}

ART_PAL = {"k": (16, 16, 20), "w": (220, 226, 236), "W": (245, 248, 252), "g": (70, 160, 70), "G": (40, 110, 54),
           "p": (170, 96, 60), "P": (130, 70, 44), "d": (60, 40, 30), "r": (220, 60, 70), "y": (250, 210, 70),
           "o": (240, 160, 110), "O": (200, 120, 80), "m": (240, 130, 170), "c": (60, 200, 90), "C": (36, 140, 60),
           "s": (150, 156, 170), "S": (96, 100, 116), "b": (70, 130, 230), "l": (200, 255, 210)}
GNAT = [["w....w", ".wkkw.", "..kk..", ".k..k."], ["......", "wwkkww", "..kk..", ".k..k."]]
POT = ["....g..g....", "..g.gggg.g..", ".gggGggGggg.", "..gggGGggg..", "....gGGg....", ".pppppppppp.", ".pPPPPPPPPp.",
       "..pppppppp..", "..pppppppp..", "..pPPPPPPp..", "...pppppp...", "...dddddd..."]
POT_DEAD = ["............", "............", "............", "....d..d....", "...d.dd.d...", ".pppppppppp.", ".pPPPPPPPPp.",
            "..pppppppp..", "..pppppppp..", "..pPPPPPPp..", "...pppppp...", "...dddddd..."]
PRINTER = ["ssssssssss", "s........s", "s.yyyy...s", "s..bb....s", "s..bb....s", "s........s", "s.cccc...s", "s.cccc...s", "SSSSSSSSSS", "S.S....S.S"]
DONUT = ["..mmmmmm..", ".mmmmmmmm.", "mmmWmmymmm", "mmm.oo.mmm", "mmm.oo.rmm", "ommmmmmmmo", ".oooooooo.", "..OOOOOO.."]
SODA = ["..ssss..", ".cccccc.", ".cCcccc.", ".clcccc.", ".clcccc.", ".cCcccc.", ".cccccc.", ".cCCCCc.", "..ssss.."]
HEART = [".rr.rr.", "rrrrrrr", "rrrrrrr", ".rrrrr.", "..rrr..", "...r..."]

UPGRADES = ("reach", "power", "tank", "spread")
UPGRADE_LABEL = {"reach": "Swatter reach up", "power": "Swatter power up", "tank": "Bigger spray tank", "spread": "Wider spray"}


def kitchen():
    """Level 1. World is 1500 wide. Platforms are (x, y, width): you can stand on top."""
    return {
        "name": "Kitchen",
        "width": 1500,
        "platforms": [(150, 172, 210), (440, 172, 120), (640, 160, 90), (800, 172, 260), (1130, 172, 150),
                      (250, 112, 70), (860, 112, 80), (1160, 112, 70), (560, 56, 60)],
        "pots": [(300, 172), (690, 160), (930, 172), (1190, 112), (1330, FLOOR)],
        "gnats": [(220, 120), (380, 90), (520, 140), (760, 100), (880, 60), (1010, 130), (1090, 90), (1260, 140), (1400, 110)],
        "swarms": [(600, 100), (1300, 80)],
        "pickups": [("donut", 276, 100), ("printer", 580, 44), ("soda", 890, 100), ("printer", 1186, 100)],
        "door": 1450,
        "draw": draw_kitchen,
    }


LEVELS = [kitchen]


def draw_kitchen(surf, cam, level):
    """Background for the kitchen: wall, tile backsplash, cabinets, window, fridge, stove."""
    surf.fill((244, 232, 204))
    pygame.draw.rect(surf, (226, 212, 180), (0, 0, W, 20))
    for wx in range(0, level["width"], 300):                       # upper cabinets
        x = wx + 20 - cam
        if -200 < x < W:
            pygame.draw.rect(surf, (150, 104, 66), (x, 24, 150, 44))
            pygame.draw.rect(surf, (120, 82, 52), (x, 24, 150, 44), 2)
            pygame.draw.line(surf, (120, 82, 52), (x + 75, 24), (x + 75, 68), 2)
            pygame.draw.rect(surf, (230, 200, 120), (x + 66, 44, 4, 8))
            pygame.draw.rect(surf, (230, 200, 120), (x + 80, 44, 4, 8))
    for wx in range(200, level["width"], 420):                     # windows
        x = wx - cam
        if -100 < x < W:
            pygame.draw.rect(surf, (150, 210, 250), (x, 78, 70, 56))
            pygame.draw.rect(surf, (250, 250, 250), (x, 78, 70, 56), 3)
            pygame.draw.line(surf, (250, 250, 250), (x + 35, 78), (x + 35, 134), 3)
            pygame.draw.line(surf, (250, 250, 250), (x, 106), (x + 70, 106), 3)
    start = -(cam % 16)
    for x in range(int(start), W, 16):                             # tile backsplash
        pygame.draw.line(surf, (216, 204, 176), (x, 140), (x, 172))
    pygame.draw.line(surf, (216, 204, 176), (0, 156), (W, 156))
    fx = 1050 - cam                                                 # fridge
    if -80 < fx < W:
        pygame.draw.rect(surf, (214, 220, 228), (fx, 70, 62, FLOOR - 70))
        pygame.draw.rect(surf, (160, 168, 180), (fx, 70, 62, FLOOR - 70), 2)
        pygame.draw.line(surf, (160, 168, 180), (fx, 118), (fx + 62, 118), 2)
        pygame.draw.rect(surf, (120, 128, 140), (fx + 6, 90, 3, 20))
        pygame.draw.rect(surf, (120, 128, 140), (fx + 6, 126, 3, 30))
    sx = 610 - cam                                                  # stove
    if -80 < sx < W:
        pygame.draw.rect(surf, (60, 62, 70), (sx, 174, 70, FLOOR - 174))
        pygame.draw.rect(surf, (30, 30, 36), (sx + 8, 184, 54, 18))
        for i in range(4):
            pygame.draw.circle(surf, (200, 60, 50), (sx + 10 + i * 16, 179), 2)
    pygame.draw.rect(surf, (170, 124, 84), (0, FLOOR, W, H - FLOOR))  # floor
    start = -(cam % 40)
    for x in range(int(start), W, 40):
        pygame.draw.line(surf, (146, 104, 70), (x, FLOOR), (x, H))
    pygame.draw.line(surf, (146, 104, 70), (0, FLOOR), (W, FLOOR), 2)


class AngryPoppa(Game):
    name = "angry_poppa"
    title = "Angry Poppa"
    help_lines = ("Up: jump   Big button: swatter", "Triangle: spray   Down: pump", "Clear the pots, then find the door")
    title_color = (250, 210, 70)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.frames = {k: sprite(_TOP + legs, HERO_PAL, 2) for k, legs in _LEGS.items()}
        self.frames_l = {k: c.flip(v) for k, v in self.frames.items()}
        self.gnat_art = [sprite(g, ART_PAL, 2) for g in GNAT]
        self.art = {"pot": sprite(POT, ART_PAL, 2), "pot_dead": sprite(POT_DEAD, ART_PAL, 2),
                    "printer": sprite(PRINTER, ART_PAL, 2), "donut": sprite(DONUT, ART_PAL, 2),
                    "soda": sprite(SODA, ART_PAL, 2), "heart": sprite(HEART, ART_PAL, 2)}
        self.level_index = 0
        self.reset()

    # ---------- setup ----------
    def reset(self):
        self.score = 0
        self.hearts = 4
        self.up = {k: 0 for k in UPGRADES}
        self.level_index = 0
        self.load_level()

    def load_level(self):
        lv = self.level = LEVELS[self.level_index]()
        self.x, self.y = 40.0, float(FLOOR)
        self.vx = self.vy = 0.0
        self.face = 1
        self.on_ground = True
        self.swing = 0.0
        self.swing_cool = 0.0
        self.pump_anim = 0.0
        self.pressure = self.max_pressure
        self.invuln = 0.0
        self.boost = 0.0
        self.cam = 0.0
        self.level_time = 0.0
        self.cleared = False
        self.banner = (lv["name"], 2.0)
        self.gnats = [self.new_gnat(x, y) for x, y in lv["gnats"]]
        for sx, sy in lv["swarms"]:
            for i in range(5):
                self.gnats.append(self.new_gnat(sx + i * 6 - 12, sy + (i % 2) * 8, swarm=True))
        self.pots = [{"x": x, "y": y, "hp": 3, "timer": self.rng.uniform(2, 5), "hit": 0.0} for x, y in lv["pots"]]
        self.pickups = [{"kind": k, "x": float(x), "y": float(y), "vy": 0.0} for k, x, y in lv["pickups"]]
        self.puffs = []      # spray particles: x, y, vx, vy, ttl
        self.sparks = []     # x, y, ttl

    def new_gnat(self, x, y, swarm=False):
        return {"x": float(x), "y": float(y), "hx": float(x), "hy": float(y), "ph": self.rng.uniform(0, 6.28),
                "speed": self.rng.uniform(34, 52) * (1.15 if swarm else 1.0), "swarm": swarm}

    # ---------- derived values ----------
    @property
    def max_pressure(self):
        return 5 + 2 * self.up["tank"]

    @property
    def reach(self):
        return 34 + 10 * self.up["reach"]

    def hero_rect(self):
        return pygame.Rect(int(self.x) - 10, int(self.y) - 56, 20, 56)

    def swat_rect(self):
        r = self.reach
        return pygame.Rect(int(self.x) + (6 if self.face > 0 else -6 - r), int(self.y) - 68, r, 66)

    # ---------- update ----------
    def update(self, dt, inp):
        lv = self.level
        self.level_time += dt
        self.invuln = max(0.0, self.invuln - dt)
        self.boost = max(0.0, self.boost - dt)
        self.swing = max(0.0, self.swing - dt)
        self.swing_cool = max(0.0, self.swing_cool - dt)
        self.pump_anim = max(0.0, self.pump_anim - dt)
        if self.banner:
            self.banner = (self.banner[0], self.banner[1] - dt) if self.banner[1] > dt else None

        # movement
        direction = ("right" in inp.held) - ("left" in inp.held)
        speed = 96.0 * (1.55 if self.boost > 0 else 1.0)
        self.vx = direction * speed
        if direction:
            self.face = direction
        if "up" in inp.pressed and self.on_ground:
            self.vy = -365.0
            self.on_ground = False
        old_y = self.y
        self.vy += GRAVITY * dt
        self.x = max(10.0, min(lv["width"] - 10.0, self.x + self.vx * dt))
        self.y += self.vy * dt
        self.on_ground = False
        if self.y >= FLOOR:
            self.y, self.vy, self.on_ground = float(FLOOR), 0.0, True
        elif self.vy > 0:
            for px, py, pw in lv["platforms"]:
                if px - 4 <= self.x <= px + pw + 4 and old_y <= py <= self.y:
                    self.y, self.vy, self.on_ground = float(py), 0.0, True
                    break

        # tools
        if "a" in inp.pressed and self.swing_cool <= 0:
            self.swing, self.swing_cool = 0.2, 0.32
            self.swat()
        if "b" in inp.pressed and self.pressure > 0:
            self.pressure -= 1
            self.spray()
        if "down" in inp.pressed and self.on_ground and self.pressure < self.max_pressure:
            self.pressure += 1
            self.pump_anim = 0.18

        self.update_gnats(dt)
        self.update_pots(dt)
        self.update_puffs(dt)
        self.update_pickups(dt)
        self.sparks = [[x, y, t - dt] for x, y, t in self.sparks if t > dt]
        self.cam = max(0.0, min(lv["width"] - W, self.x - 150))

        if not self.cleared and all(p["hp"] <= 0 for p in self.pots):
            self.cleared = True
            self.banner = ("Pots clear! Head for the door", 2.5)
        if self.cleared and self.x >= lv["door"] - 6:
            self.finish_level()

    def kill_gnat(self, g):
        if g in self.gnats:
            self.gnats.remove(g)
            self.score += 10
            self.sparks.append([g["x"], g["y"], 0.25])
            if self.rng.random() < 0.06:
                self.pickups.append({"kind": self.rng.choice(("donut", "soda")), "x": g["x"], "y": g["y"], "vy": 0.0})

    def swat(self):
        rect = self.swat_rect()
        damage = 1 + self.up["power"]
        for g in list(self.gnats):
            if rect.collidepoint(g["x"], g["y"]):
                self.kill_gnat(g)
        for p in self.pots:
            if p["hp"] > 0 and rect.colliderect(pygame.Rect(p["x"] - 12, p["y"] - 24, 24, 24)):
                self.hurt_pot(p, damage)

    def spray(self):
        n = 6 + 2 * self.up["spread"]
        fan = 0.22 + 0.12 * self.up["spread"]
        for i in range(n):
            ang = (i / (n - 1) - 0.5) * 2 * fan
            v = self.rng.uniform(190, 250)
            self.puffs.append([self.x + self.face * 18, self.y - 36, self.face * math.cos(ang) * v, math.sin(ang) * v - 10, 0.6])

    def hurt_pot(self, p, damage):
        p["hp"] -= damage
        p["hit"] = 0.15
        if p["hp"] <= 0:
            self.score += 100
            self.sparks.append([p["x"], p["y"] - 12, 0.4])

    def update_gnats(self, dt):
        hero = self.hero_rect()
        hx, hy = self.x, self.y - 36
        for g in list(self.gnats):
            g["ph"] += dt * 7
            dx, dy = hx - g["x"], hy - g["y"]
            dist = math.hypot(dx, dy) or 1.0
            if dist < 230:
                g["x"] += dx / dist * g["speed"] * dt
                g["y"] += dy / dist * g["speed"] * dt
            else:
                g["x"] += (g["hx"] - g["x"]) * dt
                g["y"] += (g["hy"] - g["y"]) * dt
            g["x"] += math.cos(g["ph"]) * 26 * dt
            g["y"] += math.sin(g["ph"] * 1.3) * 26 * dt
            if self.invuln <= 0 and hero.collidepoint(g["x"], g["y"]):
                self.hearts -= 1
                self.invuln = 1.3
                self.kill_gnat(g)
                self.score = max(0, self.score - 10)
                if self.hearts <= 0:
                    self.game_over()
                    return

    def update_pots(self, dt):
        for p in self.pots:
            p["hit"] = max(0.0, p["hit"] - dt)
            if p["hp"] <= 0:
                continue
            p["timer"] -= dt
            near = abs(p["x"] - self.x) < 260
            if p["timer"] <= 0 and near and len(self.gnats) < 26:
                self.gnats.append(self.new_gnat(p["x"], p["y"] - 26))
                p["timer"] = self.rng.uniform(3.0, 5.0)

    def update_puffs(self, dt):
        for f in self.puffs:
            f[0] += f[2] * dt
            f[1] += f[3] * dt
            f[2] *= 0.5 ** (dt / 0.34)
            f[3] *= 0.5 ** (dt / 0.34)
            f[4] -= dt
            for g in list(self.gnats):
                if abs(g["x"] - f[0]) < 7 and abs(g["y"] - f[1]) < 7:
                    self.kill_gnat(g)
            for p in self.pots:
                if p["hp"] > 0 and abs(p["x"] - f[0]) < 10 and -24 < f[1] - p["y"] < 0 and f[4] > 0:
                    self.hurt_pot(p, 1)
                    f[4] = 0
        self.puffs = [f for f in self.puffs if f[4] > 0]

    def update_pickups(self, dt):
        hero = self.hero_rect().inflate(8, 4)
        for pk in list(self.pickups):
            floor = FLOOR
            for px, py, pw in self.level["platforms"]:
                if px <= pk["x"] <= px + pw and pk["y"] <= py + 1:
                    floor = min(floor, py)
            if pk["y"] < floor:
                pk["vy"] += GRAVITY * dt
                pk["y"] = min(float(floor), pk["y"] + pk["vy"] * dt)
            if hero.collidepoint(pk["x"], pk["y"] - 8):
                self.pickups.remove(pk)
                self.score += 25
                if pk["kind"] == "donut":
                    self.hearts = min(6, self.hearts + 1)
                    self.banner = ("Donut! One heart back", 1.2)
                elif pk["kind"] == "soda":
                    self.boost = 7.0
                    self.banner = ("Speed boost!", 1.2)
                else:
                    choices = [k for k in UPGRADES if self.up[k] < 2]
                    if choices:
                        k = self.rng.choice(choices)
                        self.up[k] += 1
                        if k == "tank":
                            self.pressure = self.max_pressure
                        self.banner = (UPGRADE_LABEL[k], 1.6)

    def finish_level(self):
        bonus = 500 + max(0, 300 - int(self.level_time) * 2) + self.hearts * 50
        self.score += bonus
        if self.level_index + 1 < len(LEVELS):
            self.level_index += 1
            self.load_level()
        else:
            self.win = True
            self.game_over()

    # ---------- drawing ----------
    def draw(self, surf):
        lv = self.level
        cam = int(self.cam)
        lv["draw"](surf, cam, lv)
        for px, py, pw in lv["platforms"]:
            x = px - cam
            if -pw < x < W:
                pygame.draw.rect(surf, (236, 236, 228), (x, py, pw, 5))
                pygame.draw.rect(surf, (150, 104, 66), (x + 2, py + 5, pw - 4, (FLOOR - py - 5) if py > 140 else 4))
                if py > 140:
                    for dx in range(30, pw - 10, 50):
                        pygame.draw.rect(surf, (120, 82, 52), (x + dx, py + 10, 2, FLOOR - py - 16))
        dx = lv["door"] - cam
        if -40 < dx < W:
            pygame.draw.rect(surf, (96, 66, 44), (dx - 14, FLOOR - 58, 30, 58))
            pygame.draw.rect(surf, (60, 200, 90) if self.cleared else (70, 48, 32), (dx - 11, FLOOR - 55, 24, 55))
            pygame.draw.circle(surf, (240, 210, 90), (dx + 8, FLOOR - 28), 2)
        for p in self.pots:
            img = self.art["pot" if p["hp"] > 0 else "pot_dead"]
            x, y = p["x"] - cam - 12, p["y"] - 24
            if -30 < x < W:
                surf.blit(img, (x, y))
                if p["hit"] > 0:
                    pygame.draw.rect(surf, c.WHITE, (x, y, 24, 24), 1)
                if p["hp"] > 0:
                    for i in range(p["hp"]):
                        pygame.draw.rect(surf, (220, 60, 70), (x + 4 + i * 6, y - 5, 4, 3))
        for pk in self.pickups:
            img = self.art[pk["kind"]]
            bob = int(math.sin(self.time * 5 + pk["x"]) * 2)
            surf.blit(img, (int(pk["x"]) - cam - img.get_width() // 2, int(pk["y"]) - img.get_height() + bob))
        for g in self.gnats:
            x = int(g["x"]) - cam
            if -12 < x < W + 12:
                surf.blit(self.gnat_art[int(g["ph"]) % 2], (x - 6, int(g["y"]) - 4))
        for f in self.puffs:
            r = 2 + int((0.6 - f[4]) * 6)
            pygame.draw.circle(surf, (200, 240, 230), (int(f[0]) - cam, int(f[1])), r, 1)
        for x, y, t in self.sparks:
            for k in range(4):
                a = k * 1.57 + t * 20
                pygame.draw.line(surf, (255, 240, 120), (int(x) - cam, int(y)),
                                 (int(x + math.cos(a) * 7) - cam, int(y + math.sin(a) * 7)))
        self.draw_hero(surf, cam)
        self.draw_hud(surf)

    def draw_hero(self, surf, cam):
        if self.invuln > 0 and int(self.time * 20) % 2:
            return
        if not self.on_ground:
            key = "jump"
        elif abs(self.vx) > 1:
            key = "run1" if int(self.time * 9) % 2 else "run2"
        else:
            key = "stand"
        img = (self.frames if self.face > 0 else self.frames_l)[key]
        hx, hy = int(self.x) - cam, int(self.y)
        surf.blit(img, (hx - 18, hy - 60 + (2 if self.pump_anim > 0 else 0)))
        f = self.face
        hand = (hx + f * 16, hy - 30)
        if self.swing > 0:                                   # swatter mid-swing, crackling
            tip = (hand[0] + f * (self.reach - 8), hand[1] - 22 + int((0.2 - self.swing) * 170))
            pygame.draw.line(surf, (60, 60, 70), hand, tip, 2)
            pygame.draw.ellipse(surf, (250, 220, 80), (tip[0] - 9, tip[1] - 12, 18, 24), 2)
            pygame.draw.line(surf, (255, 255, 200), (tip[0] - 6, tip[1] - 6), (tip[0] + 6, tip[1] + 6))
            pygame.draw.line(surf, (255, 255, 200), (tip[0] + 6, tip[1] - 6), (tip[0] - 6, tip[1] + 6))
        else:                                                # swatter at rest, held upright
            pygame.draw.line(surf, (60, 60, 70), hand, (hand[0] + f * 4, hand[1] - 22), 2)
            pygame.draw.ellipse(surf, (250, 220, 80), (hand[0] + f * 4 - 7, hand[1] - 42, 14, 21), 2)
        can = (hx - f * 16, hy - 28)                         # spray can in the other hand
        pygame.draw.rect(surf, (210, 60, 60), (can[0] - 4, can[1] - 4, 8, 14))
        pygame.draw.rect(surf, (230, 230, 236), (can[0] - 2, can[1] - 8, 5, 4))

    def draw_hud(self, surf):
        for i in range(self.hearts):
            surf.blit(self.art["heart"], (6 + i * 16, 5))
        text(surf, "Spray", (6, 22), 16)
        for i in range(self.max_pressure):
            col = (120, 230, 210) if i < self.pressure else (70, 80, 90)
            pygame.draw.rect(surf, c.INK, (40 + i * 8, 23, 7, 9))
            pygame.draw.rect(surf, col, (41 + i * 8, 24, 5, 7))
        text(surf, "Score %d" % self.score, (W - 96, 5), 20)
        left = sum(1 for p in self.pots if p["hp"] > 0)
        text(surf, "Pots %d" % left, (W - 96, 22), 16, c.YELLOW if left else (120, 230, 140))
        if self.boost > 0:
            text(surf, "BOOST", (W // 2, 5), 18, (120, 240, 140), center=True)
        if self.banner:
            text(surf, self.banner[0], (W // 2, 44), 22, c.YELLOW, center=True)

    def draw_title_art(self, surf):
        self.draw(surf)

    def render(self, surf):
        super().render(surf)
        if self.state == "over" and getattr(self, "win", False):
            pygame.draw.rect(surf, c.BLACK, (60, 52, W - 120, 44))
            text(surf, "HOUSE CLEAR!", (W // 2, 60), 44, (120, 240, 140), center=True)

    def game_over(self):
        if not hasattr(self, "win"):
            self.win = False
        super().game_over()

    def step(self, dt, inp):
        was_over = self.state == "over"
        super().step(dt, inp)
        if was_over and self.state == "play":
            self.win = False


def make(**kw):
    return AngryPoppa(**kw)
