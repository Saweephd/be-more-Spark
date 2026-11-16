"""Mazee Run: an endless runner starring Mazee.

Big button jumps (hold for a higher jump). D-pad down ducks under birds.
Score is the distance run plus fifty for every treat.
"""
import pygame

from . import common as c
from .common import H, W, Game, sprite, text

GROUND = 198
DOG_X = 44

PAL = {"W": (250, 250, 246), "G": (206, 206, 214), "K": (30, 30, 36), "P": (240, 130, 150),
       "S": (160, 160, 172)}

_BODY = [
    "...................WWW....",
    "..WW..............WWWWWW..",
    ".WWWW............WWWWWWWW.",
    ".WWWW...........WWWWKWWWW.",
    "..WWW...........WWWWWWWKK.",
    "..WWW...........GWWWWWWW..",
    "...WWWWWWWWWWWWWWWWWWPP...",
    "..WWWWWWWWWWWWWWWWWWW.....",
    "..WWWWWWWWWWWWWWWWWWW.....",
    "..WWWWWWWWWWWWWWWWWW......",
    "..GWWWWWWWWWWWWWWWWG......",
    "..GGWWWWWWWWWWWWWGG.......",
    "...GGGWWGGGGGGWWGG........",
]
_LEGS = [
    ["...WW.WW.....WW.WW........", "...WW.WW.....WW.WW........", "...SS.SS.....SS.SS........"],
    ["..WW...WW...WW...WW.......", ".WW.....WW.WW.....WW......", ".SS.....SS.SS.....SS......"],
    ["....WWW.......WWW.........", "....WWW.......WWW.........", "....SSS.......SSS........."],
    ["..WWW...WW.WW....WWW......", ".WW......WWW.......WW.....", ".........................."],
]
_DUCK = [
    "..................WWWW....",
    "..WW.............WWWWWWW..",
    ".WWWWWWWWWWWWWWWWWWWKWWWW.",
    ".WWWWWWWWWWWWWWWWWWWWWWKK.",
    "..WWWWWWWWWWWWWWWWWWWWPP..",
    "..GWWWWWWWWWWWWWWWWWG.....",
    "..GGGWWGGGGGGGWWWGGG......",
    "...SSS.SSS....SSS.SSS.....",
]

ITEM_PAL = {"r": (150, 150, 160), "d": (110, 110, 122), "R": (214, 60, 60), "D": (150, 36, 44),
            "g": (60, 150, 70), "h": (40, 110, 54), "b": (70, 80, 200), "y": (250, 200, 60),
            "o": (240, 150, 50), "k": (30, 30, 36), "w": (250, 250, 250), "t": (236, 220, 180),
            "T": (200, 176, 130)}
ROCK = ["....rrrr....", "..rrrrrrrr..", ".rrrrrrrrdd.", "rrrrrrrrdddd", "rrrrrrdddddd", "rdddddddddd."]
HYDRANT = ["...RRRR...", "..RRRRRR..", "..RRRRRR..", ".DRRRRRRD.", "RRRRwwRRRR", "RRRRwwRRRR", ".DRRRRRRD.",
           "..RRRRRR..", "..RRRRRR..", "..RRRRRR..", "..RRRRRR..", ".DDDDDDDD.", "DDDDDDDDDD"]
BUSH = ["......gggg........gg......", "...gggggggggg..ggggggg....", "..ggggggggggggggggggggg...", ".gggghggggggggggghgggggg..",
        "ggggggggggghgggggggggggggg", "gghggggggggggggggggggghggg", "gggggggghggggggggggggggggg", "hhhhhhhhhhhhhhhhhhhhhhhhhh"]
BIRD = [["..bb........", ".bbbb...by..", "bbbbbbbbbko.", "..bbbbbbbb..", "....bbbb....", "............"],
        ["............", "........by..", "bbbbbbbbbko.", ".bbbbbbbbb..", ".bbbbbbb....", "..bbb......."]]
BONE = [".tt......tt.", "tttt....tttt", "tttttttttttt", "tttttttttttt", "tTTt....tTTt", ".TT......TT."]


class MazeeRun(Game):
    name = "mazee_run"
    title = "Mazee Run"
    help_lines = ("Big button: jump (hold to jump higher)", "D-pad down: duck", "Grab the treats!")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.run_frames = [sprite(_BODY + legs, PAL, 2) for legs in _LEGS[:2]]
        self.jump_frame = sprite(_BODY + _LEGS[3], PAL, 2)
        self.duck_frame = sprite(_DUCK, PAL, 2)
        self.art = {"rock": sprite(ROCK, ITEM_PAL, 2), "hydrant": sprite(HYDRANT, ITEM_PAL, 2),
                    "bush": sprite(BUSH, ITEM_PAL, 2), "bone": sprite(BONE, ITEM_PAL, 2),
                    "bird": [sprite(f, ITEM_PAL, 2) for f in BIRD]}
        self.reset()

    def reset(self):
        self.score = 0
        self.dist = 0.0
        self.treats = 0
        self.y = float(GROUND)
        self.vy = 0.0
        self.on_ground = True
        self.ducking = False
        self.obstacles = []      # dicts: kind, x, y, w, h
        self.bones = []
        self.next_spawn = 180.0
        self.next_bone = 260.0
        self.anim = 0.0

    @property
    def speed(self):
        return min(340.0, 150.0 + self.dist / 40.0)

    def dog_rect(self):
        if self.ducking:
            return pygame.Rect(DOG_X + 10, int(self.y) - 14, 32, 14)
        return pygame.Rect(DOG_X + 10, int(self.y) - 30, 32, 30)

    def spawn(self):
        r = self.rng.random()
        level = self.dist
        if level > 600 and r < 0.22:
            kind, w, h, y = "bird", 24, 12, GROUND - 30 - self.rng.choice((0, 0, 34))
        elif r < 0.5:
            kind, w, h, y = "rock", 24, 12, GROUND - 12
        elif r < 0.8:
            kind, w, h, y = "hydrant", 20, 26, GROUND - 26
        elif level > 500:
            kind, w, h, y = "bush", 52, 16, GROUND - 16
        else:
            kind, w, h, y = "rock", 24, 12, GROUND - 12
        self.obstacles.append({"kind": kind, "x": float(W + 10), "y": y, "w": w, "h": h})
        gap = self.rng.uniform(0.85, 1.6) * self.speed + 70
        self.next_spawn = gap

    def update(self, dt, inp):
        self.anim += dt * (6 + self.speed / 40)
        move = self.speed * dt
        self.dist += move
        self.ducking = self.on_ground and "down" in inp.held
        if self.on_ground and "a" in inp.pressed and not self.ducking:
            self.vy = -470.0
            self.on_ground = False
        if not self.on_ground:
            if self.vy < 0 and "a" not in inp.held:
                self.vy *= 0.45 ** (dt * 60 / 4)      # let go early for a short hop
            self.vy += 1250.0 * dt
            self.y += self.vy * dt
            if self.y >= GROUND:
                self.y, self.vy, self.on_ground = float(GROUND), 0.0, True
        self.next_spawn -= move
        if self.next_spawn <= 0:
            self.spawn()
        self.next_bone -= move
        if self.next_bone <= 0:
            self.bones.append({"x": float(W + 10), "y": GROUND - self.rng.choice((16, 54, 84))})
            self.next_bone = self.rng.uniform(220, 520)
        for o in self.obstacles:
            o["x"] -= move * (1.25 if o["kind"] == "bird" else 1.0)
        for b in self.bones:
            b["x"] -= move
        self.obstacles = [o for o in self.obstacles if o["x"] > -70]
        self.bones = [b for b in self.bones if b["x"] > -20]
        dog = self.dog_rect()
        for b in list(self.bones):
            if dog.colliderect(pygame.Rect(int(b["x"]), b["y"], 24, 12)):
                self.bones.remove(b)
                self.treats += 1
        self.score = int(self.dist / 10) + self.treats * 50
        for o in self.obstacles:
            if dog.colliderect(pygame.Rect(int(o["x"]) + 3, o["y"] + 3, o["w"] - 6, o["h"] - 3)):
                self.game_over()
                return

    def draw_background(self, surf):
        for i, col in enumerate(((120, 190, 240), (140, 204, 244), (170, 218, 248), (200, 232, 250))):
            pygame.draw.rect(surf, col, (0, i * 40, W, 40))
        pygame.draw.rect(surf, (200, 232, 250), (0, 160, W, 40))
        pygame.draw.circle(surf, (255, 236, 150), (330, 44), 18)
        off = self.dist * 0.08
        for i in range(4):
            x = int((i * 130 - off) % (W + 80)) - 40
            pygame.draw.ellipse(surf, (255, 255, 255), (x, 30 + (i % 2) * 22, 46, 14))
            pygame.draw.ellipse(surf, (255, 255, 255), (x + 14, 24 + (i % 2) * 22, 30, 16))
        off = self.dist * 0.25
        for i in range(4):
            x = int((i * 150 - off) % (W + 200)) - 100
            pygame.draw.ellipse(surf, (120, 180, 120), (x, 140, 200, 120))
        off = self.dist * 0.6
        for i in range(12):
            x = int((i * 40 - off) % (W + 40)) - 20
            pygame.draw.rect(surf, (236, 228, 208), (x, 168, 5, 30))
        pygame.draw.rect(surf, (236, 228, 208), (0, 176, W, 4))
        pygame.draw.rect(surf, (90, 170, 80), (0, GROUND, W, H - GROUND))
        pygame.draw.rect(surf, (70, 140, 64), (0, GROUND, W, 3))
        off = self.dist
        for i in range(14):
            x = int((i * 31 - off) % (W + 30)) - 10
            pygame.draw.line(surf, (60, 124, 58), (x, GROUND + 10 + (i * 7) % 24), (x + 4, GROUND + 10 + (i * 7) % 24))

    def draw(self, surf):
        self.draw_background(surf)
        for b in self.bones:
            surf.blit(self.art["bone"], (int(b["x"]), b["y"]))
        for o in self.obstacles:
            img = self.art[o["kind"]]
            if o["kind"] == "bird":
                img = img[int(self.anim / 2) % 2]
            surf.blit(img, (int(o["x"]), o["y"]))
        if self.ducking:
            surf.blit(self.duck_frame, (DOG_X, int(self.y) - 16))
        elif not self.on_ground:
            surf.blit(self.jump_frame, (DOG_X, int(self.y) - 30))
        else:
            surf.blit(self.run_frames[int(self.anim) % 2], (DOG_X, int(self.y) - 32))
        text(surf, "Score %d" % self.score, (8, 6), 20)
        text(surf, "Treats %d" % self.treats, (W - 80, 6), 20)


def make(**kw):
    return MazeeRun(**kw)
