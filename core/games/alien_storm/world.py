"""Scenery, ships, bosses and effects for Alien Storm: Tom Cat Alley. Drawn in code and cached."""
import math
import random

import pygame

from . import art
from .art import SS, AL, poly, line, oval, _canvas, _down, _star

_c = {}

SEA = [  # base, streak, glint for each stage
    ((26, 82, 128), (44, 108, 152), (150, 200, 230)),
    ((34, 48, 62), (52, 68, 84), (120, 136, 150)),
    ((20, 112, 136), (40, 144, 164), (170, 232, 230)),
    ((20, 22, 34), (34, 38, 58), (70, 130, 230)),
]


def sea(stage):
    """A 400 x 480 strip that tiles top to bottom."""
    if ("sea", stage) in _c:
        return _c[("sea", stage)]
    base, streak, glint = SEA[stage]
    s = pygame.Surface((400, 480))
    s.fill(base)
    rng = random.Random(10 + stage)
    if stage == 3:                                   # the skin of the mothership: plates, lights, conduits
        for y in range(0, 480, 60):
            pygame.draw.line(s, streak, (0, y), (400, y), 2)
            off = 0 if (y // 60) % 2 else 50
            for x in range(off, 400, 100):
                pygame.draw.line(s, streak, (x, y), (x, y + 60), 1)
                pygame.draw.rect(s, (28, 32, 50), (x + 8, y + 8, 84, 44))
                if rng.random() < 0.5:
                    pygame.draw.rect(s, (40, 80, 160), (x + 14, y + 14, 20, 3))
                if rng.random() < 0.3:
                    pygame.draw.circle(s, glint, (x + 70, y + 30), 3)
                    pygame.draw.circle(s, (160, 210, 255), (x + 70, y + 30), 1)
        for x in (70, 330):
            pygame.draw.rect(s, (60, 20, 30), (x - 4, 0, 8, 480))
            pygame.draw.rect(s, (200, 50, 60), (x - 1, 0, 2, 480))
    else:
        for _ in range(260):
            x, y, w = rng.randrange(400), rng.randrange(480), rng.randrange(5, 26)
            col = streak if rng.random() < 0.85 else glint
            for dy in (0, 480, -480):
                pygame.draw.line(s, col, (x, y + dy), (x + w, y + dy))
        if stage == 1:
            for _ in range(70):                      # whitecaps
                x, y = rng.randrange(400), rng.randrange(480)
                pygame.draw.line(s, (170, 184, 196), (x, y), (x + rng.randrange(3, 9), y))
    _c[("sea", stage)] = s
    return s


def cloud(stage, i):
    key = ("cloud", stage, i)
    if key in _c:
        return _c[key]
    rng = random.Random(stage * 10 + i)
    w, h = rng.randrange(90, 170), rng.randrange(40, 70)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    col = (236, 242, 248) if stage != 1 else (70, 78, 90)
    sh = (200, 212, 226) if stage != 1 else (48, 54, 66)
    for c, dy in ((sh, 4), (col, 0)):
        r2 = random.Random(stage * 10 + i)
        for _ in range(14):
            r = r2.randrange(9, h // 2 - 4)
            x, y = r2.randrange(r, w - r), r2.randrange(r, h - r - 3)
            pygame.draw.circle(s, c, (x, y + dy), r)
    s.set_alpha(150 if stage != 1 else 200)
    _c[key] = s
    return s


def island(i):
    key = ("island", i)
    if key in _c:
        return _c[key]
    rng = random.Random(40 + i)
    w, h = rng.randrange(80, 150), rng.randrange(60, 110)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pts = []
    for k in range(14):
        a = k / 14 * math.tau
        r = 0.34 + rng.random() * 0.14
        pts.append((w / 2 + math.cos(a) * w * r, h / 2 + math.sin(a) * h * r))

    def grow(f):
        return [(w / 2 + (x - w / 2) * f, h / 2 + (y - h / 2) * f) for x, y in pts]
    pygame.draw.polygon(s, (120, 220, 220), grow(1.16))      # shallows
    pygame.draw.polygon(s, (236, 220, 160), grow(1.0))       # beach
    pygame.draw.polygon(s, (60, 140, 70), grow(0.82))        # jungle
    pygame.draw.polygon(s, (40, 110, 56), grow(0.5))
    for _ in range(22):
        x, y = w / 2 + rng.uniform(-0.28, 0.28) * w, h / 2 + rng.uniform(-0.28, 0.28) * h
        pygame.draw.circle(s, (30, 96, 48), (int(x), int(y)), 3)
        pygame.draw.circle(s, (90, 170, 90), (int(x) - 1, int(y) - 1), 1)
    _c[key] = s
    return s


def boom(size):
    """Ten frames of a fireball that turns to smoke."""
    key = ("boom", size)
    if key in _c:
        return _c[key]
    frames = []
    rng = random.Random(size)
    blobs = [(rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), rng.uniform(0.35, 0.6)) for _ in range(7)]
    for f in range(10):
        u = f / 9
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        for bx, by, br in blobs:
            r = int(size * br * (0.5 + u * 0.9))
            x, y = int(size + bx * size * (0.6 + u)), int(size + by * size * (0.6 + u))
            if u < 0.55:
                pygame.draw.circle(s, (255, 150, 40), (x, y), r)
                pygame.draw.circle(s, (255, 226, 120), (x, y), max(1, int(r * (0.7 - u))))
                if u < 0.2:
                    pygame.draw.circle(s, (255, 255, 240), (x, y), max(1, int(r * 0.4)))
            else:
                g = int(90 - 50 * u)
                pygame.draw.circle(s, (g, g, g + 6), (x, y), r)
        s.set_alpha(255 if u < 0.5 else int(255 * (1 - u) * 2))
        frames.append(s)
    _c[key] = frames
    return frames


def pickup(kind):
    key = ("pickup", kind)
    if key in _c:
        return _c[key]
    col = {"M": (230, 70, 70), "H": (70, 200, 110), "L": (80, 150, 240), "P": (240, 200, 70)}[kind]
    s = _canvas(14, 14)
    oval(s, (255, 255, 255), (0, 0, 14, 14))
    oval(s, col, (1.2, 1.2, 11.6, 11.6))
    oval(s, tuple(min(255, c + 60) for c in col), (3, 2.4, 5, 3))
    out = _down(s)
    f = pygame.font.Font(None, 15)
    t = f.render(kind, True, (255, 255, 255))
    out.blit(t, (7 - t.get_width() // 2, 7 - t.get_height() // 2 + 1))
    _c[key] = out
    return out


def missile(kind):
    """Small missiles seen from above, nose up. heat = white with red, radar = long with blue."""
    key = ("missile", kind)
    if key in _c:
        return _c[key]
    s = _canvas(5, 14)
    body = (240, 240, 244)
    tip = (220, 60, 60) if kind == "heat" else (60, 110, 220)
    L = 9 if kind == "heat" else 11
    poly(s, body, [(1.7, 2), (3.3, 2), (3.3, 2 + L), (1.7, 2 + L)])
    poly(s, tip, [(1.7, 2.4), (3.3, 2.4), (2.5, 0)])
    poly(s, (120, 126, 136), [(0.4, 1 + L), (1.7, L - 1), (1.7, 2 + L)], mirror=2.5)
    _c[key] = out = _down(s)
    return out


def extra_alien(kind):
    key = ("xalien", kind)
    if key in _c:
        return _c[key]
    if kind == "seeker":
        s = _canvas(16, 16)
        oval(s, (120, 200, 255, 90), (0, 0, 16, 16))
        oval(s, AL["body"], (2, 2, 12, 12))
        oval(s, AL["hi"], (3.2, 3, 7, 5))
        for a in range(4):
            x, y = 8 + math.cos(a * math.pi / 2 + 0.78) * 7, 8 + math.sin(a * math.pi / 2 + 0.78) * 7
            oval(s, AL["edge"], (x - 1.2, y - 1.2, 2.4, 2.4))
        _star(s, 8, 8, 2.6)
    else:                                            # a gun turret on the mothership's hull
        s = _canvas(22, 22)
        oval(s, (44, 50, 76), (1, 1, 20, 20))
        oval(s, AL["body"], (3, 3, 16, 16))
        poly(s, AL["edge"], [(9.6, 11), (12.4, 11), (12, 21), (10, 21)])
        oval(s, AL["hi"], (5, 4.6, 8, 5))
        _star(s, 11, 10, 3)
    _c[key] = out = _down(s)
    return out


# ------------------------------------------------------------------ bosses, nose down
def boss(kind, flash=False):
    key = ("boss", kind)
    if key not in _c:
        _c[key] = _boss(kind)
        w = _c[key].copy()
        w.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_ADD)
        _c[("bossflash", kind)] = w
    return _c[("bossflash", kind)] if flash else _c[key]


def _boss(kind):
    b, hi, edge, glow = AL["body"], AL["hi"], AL["edge"], AL["glow"]
    if kind == "lance":                              # a huge blade shaped strike cruiser
        W, H, cx = 70, 120, 35.0
        s = _canvas(W, H)
        for ex in (cx - 9, cx, cx + 9):
            oval(s, (120, 200, 255, 110), (ex - 4, -3, 8, 12))
            poly(s, glow, [(ex - 2, 0), (ex + 2, 0), (ex, 8)])
        poly(s, b, [(cx, 120), (cx - 6, 84), (cx - 34, 30), (cx - 22, 26), (cx - 14, 6), (cx, 10)], mirror=cx)
        poly(s, hi, [(cx, 114), (cx - 4, 84), (cx - 9, 16), (cx, 14)], mirror=cx)
        poly(s, (30, 40, 70), [(cx - 12, 30), (cx - 28, 32), (cx - 12, 62)], mirror=cx)
        line(s, edge, (cx - 34, 30), (cx - 6, 84), 0.9, mirror=cx)
        line(s, edge, (cx - 6, 84), (cx, 120), 0.9, mirror=cx)
        for y in (34, 46, 58):
            oval(s, (255, 90, 90), (cx - 20 + (y - 34) * 0.45, y, 3, 3), mirror=cx)
        _star(s, cx, 44, 8)
        line(s, glow, (cx, 62), (cx, 108), 0.8)
    elif kind == "thunderhead":                      # a wide storm gunship
        W, H, cx = 130, 80, 65.0
        s = _canvas(W, H)
        for ex in (cx - 40, cx - 20, cx + 20, cx + 40):
            poly(s, glow, [(ex - 2.5, 2), (ex + 2.5, 2), (ex, 10)])
        poly(s, b, [(cx, 80), (cx - 14, 62), (cx - 30, 70), (cx - 62, 40), (cx - 56, 12), (cx - 30, 6), (cx - 12, 14), (cx, 8)], mirror=cx)
        poly(s, hi, [(cx, 74), (cx - 12, 58), (cx - 14, 20), (cx, 14)], mirror=cx)
        poly(s, (30, 40, 70), [(cx - 22, 20), (cx - 54, 18), (cx - 56, 40), (cx - 30, 60)], mirror=cx)
        line(s, edge, (cx - 62, 40), (cx - 30, 70), 1.0, mirror=cx)
        line(s, edge, (cx - 30, 70), (cx - 14, 62), 1.0, mirror=cx)
        for px in (cx - 46, cx + 46):                # lightning projectors
            oval(s, (60, 70, 120), (px - 8, 30, 16, 16))
            oval(s, (255, 250, 170), (px - 4.5, 33.5, 9, 9))
            oval(s, (255, 255, 255), (px - 2, 36, 4, 4))
        _star(s, cx, 38, 9)
    elif kind == "leviathan":                        # a flying wing carrier
        W, H, cx = 210, 96, 105.0
        s = _canvas(W, H)
        for ex in (cx - 60, cx - 36, cx - 12, cx + 12, cx + 36, cx + 60):
            oval(s, (120, 200, 255, 110), (ex - 5, -2, 10, 12))
            poly(s, glow, [(ex - 2.6, 4), (ex + 2.6, 4), (ex, -2)])
        poly(s, b, [(cx, 96), (cx - 24, 76), (cx - 104, 34), (cx - 92, 16), (cx - 50, 20), (cx - 30, 8), (cx, 14)], mirror=cx)
        poly(s, hi, [(cx, 90), (cx - 20, 72), (cx - 36, 24), (cx, 18)], mirror=cx)
        line(s, edge, (cx - 104, 34), (cx - 24, 76), 1.0, mirror=cx)
        line(s, edge, (cx - 24, 76), (cx, 96), 1.0, mirror=cx)
        for bx in (cx - 74, cx - 52):                # launch bays
            poly(s, (10, 12, 20), [(bx - 7, 30), (bx + 7, 32), (bx + 7, 46), (bx - 7, 42)], mirror=cx)
            line(s, (255, 150, 60), (bx - 7, 30), (bx + 7, 32), 0.8, mirror=cx)
        for tx in (cx - 88, cx + 88):
            oval(s, (60, 70, 120), (tx - 5, 26, 10, 10))
            oval(s, (255, 90, 90), (tx - 2, 29, 4, 4))
        _star(s, cx, 46, 11)
    else:                                            # the Red Star core
        W = H = 120
        cx = 60.0
        s = _canvas(W, H)
        oval(s, (255, 60, 60, 22), (6, 6, 108, 108))
        for k in range(8):
            a = k * math.pi / 4
            x, y = cx + math.cos(a) * 46, cx + math.sin(a) * 46
            poly(s, b, [(cx + math.cos(a - 0.2) * 24, cx + math.sin(a - 0.2) * 24), (x, y),
                        (cx + math.cos(a + 0.2) * 24, cx + math.sin(a + 0.2) * 24)])
            oval(s, edge, (x - 3, y - 3, 6, 6))
        oval(s, (44, 50, 76), (cx - 34, cx - 34, 68, 68))
        oval(s, b, (cx - 30, cx - 30, 60, 60))
        oval(s, hi, (cx - 24, cx - 26, 30, 18))
        oval(s, (120, 20, 30), (cx - 19, cx - 19, 38, 38))
        _star(s, cx, cx, 17)
    return _down(s)


# ------------------------------------------------------------------ the fleet, from above, bow up
def ship(kind):
    key = ("ship", kind)
    if key in _c:
        return _c[key]
    grey, hi, dk, deck = (136, 142, 152), (172, 178, 188), (84, 90, 100), (106, 112, 122)
    if kind == "destroyer":
        W, H, cx = 16, 100, 8.0
        s = _canvas(W, H)
        poly(s, grey, [(cx, 0), (cx - 5, 18), (cx - 6.5, 60), (cx - 5.5, 98), (cx, 100)], mirror=cx)
        poly(s, deck, [(cx, 6), (cx - 3.6, 20), (cx - 4.8, 60), (cx - 4, 94), (cx, 95)], mirror=cx)
        poly(s, hi, [(cx - 3.6, 30), (cx + 3.6, 30), (cx + 3.6, 52), (cx - 3.6, 52)])       # superstructure
        poly(s, dk, [(cx - 2.4, 34), (cx + 2.4, 34), (cx + 2.4, 42), (cx - 2.4, 42)])
        oval(s, hi, (cx - 2.2, 16, 4.4, 4.4)); line(s, dk, (cx, 18), (cx, 10), 0.7)          # gun
        for y in (22, 24.5, 27):                                                               # missile cells
            for x in (-2, 0, 2):
                oval(s, dk, (cx + x - 0.7, y, 1.4, 1.4))
        poly(s, dk, [(cx - 2, 56), (cx + 2, 56), (cx + 2, 64), (cx - 2, 64)])                 # funnel
        poly(s, deck, [(cx - 4, 76), (cx + 4, 76), (cx + 4, 92), (cx - 4, 92)])               # helicopter deck
        oval(s, (230, 230, 220), (cx - 2.4, 81, 4.8, 4.8)); oval(s, deck, (cx - 1.6, 81.8, 3.2, 3.2))
    elif kind == "battleship":
        W, H, cx = 28, 150, 14.0
        s = _canvas(W, H)
        poly(s, grey, [(cx, 0), (cx - 5, 20), (cx - 12, 62), (cx - 12, 120), (cx - 8, 148), (cx, 150)], mirror=cx)
        poly(s, (150, 128, 96), [(cx, 8), (cx - 3.4, 22), (cx - 9.6, 62), (cx - 9.6, 118), (cx - 6, 143), (cx, 144)], mirror=cx)  # teak deck
        poly(s, hi, [(cx - 6, 60), (cx + 6, 60), (cx + 7, 100), (cx - 7, 100)])
        poly(s, dk, [(cx - 3, 64), (cx + 3, 64), (cx + 3, 76), (cx - 3, 76)])
        oval(s, dk, (cx - 3, 80, 6, 7)); oval(s, dk, (cx - 3, 90, 6, 7))                      # funnels
        for ty, d in ((30, -1), (46, -1), (112, 1)):                                           # three triple turrets
            oval(s, hi, (cx - 5.5, ty - 5, 11, 11))
            oval(s, grey, (cx - 4, ty - 3.5, 8, 8))
            for gx in (-2.4, 0, 2.4):
                line(s, dk, (cx + gx, ty), (cx + gx, ty + d * 13), 0.9)
        for y in (66, 74, 82, 90):
            oval(s, hi, (cx - 9.6, y, 2.6, 2.6), mirror=cx)
    else:                                            # submarine
        W, H, cx = 14, 90, 7.0
        s = _canvas(W, H)
        c1, c2 = (34, 38, 46), (58, 64, 74)
        poly(s, c1, [(cx, 0), (cx - 4, 8), (cx - 5, 40), (cx - 3.4, 80), (cx, 90)], mirror=cx)
        poly(s, c2, [(cx, 3), (cx - 1.6, 9), (cx - 2, 60), (cx, 80)], mirror=cx)
        poly(s, c1, [(cx - 2, 26), (cx + 2, 26), (cx + 2, 38), (cx - 2, 38)])                  # sail
        poly(s, c1, [(cx - 6.6, 29), (cx - 2, 28), (cx - 2, 32), (cx - 6.6, 32)], mirror=cx)  # planes
        for y in range(44, 70, 5):
            oval(s, c1, (cx - 2.6, y, 1.8, 1.8), mirror=cx)
        poly(s, c1, [(cx - 5.6, 82), (cx, 79), (cx, 85)], mirror=cx)
    _c[key] = out = _down(s)
    return out


def carrier_small():
    """The carrier at flight scale (bow up), used when the jets pass over the fleet."""
    if "carrier_small" not in _c:
        _c["carrier_small"] = art.carrier(200)
    return _c["carrier_small"]
