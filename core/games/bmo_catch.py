"""BMO Catch: catch the good things, dodge the spiky ones.

D-pad left and right move the catcher. Big button gives a short dash.
On the touchscreen the catcher follows your finger. Three lives.
"""
import pygame

from . import common as c
from .common import H, W, Game, sprite, text

FLOOR = 214
PAL = {"t": (150, 110, 220), "T": (104, 70, 170), "k": (30, 30, 36), "w": (250, 250, 250),
       "y": (250, 204, 60), "Y": (214, 160, 30), "r": (232, 70, 90), "R": (170, 40, 60),
       "b": (90, 170, 250), "B": (50, 110, 210), "g": (120, 220, 110), "G": (70, 160, 70),
       "s": (150, 150, 165), "S": (96, 96, 112), "o": (245, 150, 60)}

CATCHER = [
    "y........................y",
    "yy......................yy",
    "syy....................yys",
    "ssyyyyyyyyyyyyyyyyyyyyyyss",
    ".stttttttttttttttttttttts.",
    ".stttkkttttttttttttkkttts.",
    ".stttkkttttttttttttkkttts.",
    ".sttttttttkkkkkkttttttTTs.",
    ".stttttttttkkkkttttTTTTTs.",
    ".sTTTTTTTTTTTTTTTTTTTTTTs.",
    "..ssssssssssssssssssssss..",
    "...SSS..............SSS...",
    "..SkkkS............SkkkS..",
    "...SSS..............SSS...",
]
STAR = ["....yy....", "....yy....", "...yyyy...", "yyyyyyyyyy", ".yyyyyyyy.", "..yyyyyy..", "..yyYYyy..", ".yyY..Yyy.", ".yY....Yy."]
HEART = [".rr...rr..", "rrrr.rrrr.", "rrrrrrrrr.", "rrrrrrrrr.", ".rrrrrrR..", "..rrrRR...", "...rRR....", "....R....."]
GEM = ["..bbbbbb..", ".bbwbbbBB.", "bbwbbbbBBB", ".bbbbbBBB.", "..bbbBBB..", "...bBBB...", "....BB...."]
CELL = ["...ss...", ".gggggg.", ".gggggg.", ".gggwgg.", ".ggwwgg.", ".gggwgg.", ".gGGGGg.", ".GGGGGG."]
SPIKE = ["k...kk...k", ".k..SS..k.", "..SSSSSS..", ".SSsSSSSS.", "kSSSSSSSSk", "kSSSSSsSSk", ".SSSSSSSS.", "..SSSSSS..", ".k..SS..k.", "k...kk...k"]

KINDS = {  # name: (art, points, weight)
    "star": (STAR, 10, 5), "gem": (GEM, 15, 3), "cell": (CELL, 20, 2), "heart": (HEART, 25, 2),
    "spike": (SPIKE, 0, 4),
}


class BmoCatch(Game):
    name = "bmo_catch"
    title = "BMO Catch"
    help_lines = ("D-pad: move the catcher", "Big button: dash", "Dodge the spiky ones!")
    title_color = (190, 160, 250)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.art = {k: sprite(v[0], PAL, 2) for k, v in KINDS.items()}
        self.catcher = sprite(CATCHER, PAL, 2)
        self.life_icon = sprite(HEART, PAL)
        self.stars = [(self.rng.randrange(W), self.rng.randrange(FLOOR), self.rng.choice((1, 1, 2))) for _ in range(40)]
        self.reset()

    def reset(self):
        self.score = 0
        self.lives = 3
        self.x = W / 2 - 26
        self.items = []
        self.spawn_in = 0.6
        self.elapsed = 0.0
        self.combo = 0
        self.dash_t = 0.0
        self.dash_cool = 0.0
        self.dash_dir = 1
        self.flash = 0.0
        self.pops = []       # floating score text: [x, y, msg, ttl]

    def spawn(self):
        names = list(KINDS)
        weights = [KINDS[n][2] for n in names]
        if self.elapsed > 40:
            weights[names.index("spike")] += 2
        kind = self.rng.choices(names, weights)[0]
        speed = self.rng.uniform(60, 90) + min(150, self.elapsed * 2.2)
        self.items.append({"kind": kind, "x": float(self.rng.randrange(8, W - 28)), "y": -22.0, "vy": speed})
        self.spawn_in = max(0.28, 0.95 - self.elapsed * 0.012) * self.rng.uniform(0.7, 1.3)

    def update(self, dt, inp):
        self.elapsed += dt
        self.flash = max(0.0, self.flash - dt)
        self.dash_cool = max(0.0, self.dash_cool - dt)
        speed = 230.0
        direction = ("right" in inp.held) - ("left" in inp.held)
        if direction:
            self.dash_dir = direction
        if "a" in inp.pressed and self.dash_cool <= 0 and inp.touch is None:
            self.dash_t, self.dash_cool = 0.16, 0.55
        if self.dash_t > 0:
            self.dash_t -= dt
            self.x += self.dash_dir * 620.0 * dt
        elif inp.touch is not None:
            target = inp.touch[0] - 26
            step = 520.0 * dt
            self.x += max(-step, min(step, target - self.x))
        else:
            self.x += direction * speed * dt
        self.x = max(2.0, min(W - 54.0, self.x))
        self.spawn_in -= dt
        if self.spawn_in <= 0:
            self.spawn()
        mouth = pygame.Rect(int(self.x) + 4, FLOOR - 28, 44, 14)
        for it in list(self.items):
            it["y"] += it["vy"] * dt
            img = self.art[it["kind"]]
            rect = pygame.Rect(int(it["x"]), int(it["y"]), img.get_width(), img.get_height())
            if rect.colliderect(mouth):
                self.items.remove(it)
                if it["kind"] == "spike":
                    self.lives -= 1
                    self.combo = 0
                    self.flash = 0.35
                    if self.lives <= 0:
                        self.game_over()
                        return
                else:
                    self.combo += 1
                    gain = KINDS[it["kind"]][1] * (1 + min(4, self.combo // 5))
                    self.score += gain
                    self.pops.append([it["x"], FLOOR - 44.0, "+%d" % gain, 0.7])
            elif it["y"] > FLOOR + 4:
                self.items.remove(it)
                if it["kind"] != "spike":
                    self.combo = 0
        for p in self.pops:
            p[1] -= 30 * dt
            p[3] -= dt
        self.pops = [p for p in self.pops if p[3] > 0]

    def draw(self, surf):
        surf.fill((20, 22, 48))
        for x, y, r in self.stars:
            surf.fill((90, 96, 150) if r == 1 else (150, 156, 210), (x, y, r, r))
        pygame.draw.rect(surf, (52, 60, 110), (0, FLOOR, W, H - FLOOR))
        pygame.draw.rect(surf, (80, 92, 160), (0, FLOOR, W, 2))
        for it in self.items:
            surf.blit(self.art[it["kind"]], (int(it["x"]), int(it["y"])))
        surf.blit(self.catcher, (int(self.x), FLOOR - 28))
        for p in self.pops:
            text(surf, p[2], (int(p[0]), int(p[1])), 16, c.YELLOW)
        if self.flash > 0:
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((230, 40, 40, int(160 * self.flash / 0.35)))
            surf.blit(shade, (0, 0))
        text(surf, "Score %d" % self.score, (8, 6), 20)
        if self.combo >= 5:
            text(surf, "x%d" % (1 + min(4, self.combo // 5)), (W // 2, 6), 20, c.YELLOW, center=True)
        for i in range(self.lives):
            surf.blit(self.life_icon, (W - 14 - i * 13, 7))


def make(**kw):
    return BmoCatch(**kw)
