"""Art for Vampires, Oh Well... Hunters, monsters and bosses, all drawn in code at four times size and
smoothed down once. Every design here is original to this project."""
import math
import random

import pygame

from ..alien_storm import art as A

SS = A.SS
_cache = {}

# name: looks and fighting style. speed px/s, damage per hit, reach px, seconds between swings.
HUNTERS = {
    "lucas": dict(title="Lucas", skin=(198, 142, 100), hair=(60, 36, 22), style="long", coat=(46, 46, 64), shirt=(120, 150, 190),
                  weapon="lanyard", wcol=(70, 130, 220), speed=96, damage=1, reach=38, cool=0.34, long_coat=True, shades=True),
    "poppa": dict(title="Angry Poppa", skin=(128, 86, 58), hair=(150, 150, 154), style="beard", coat=(236, 196, 60), shirt=(230, 120, 40),
                  weapon="newspaper", wcol=(240, 240, 232), speed=78, damage=2, reach=26, cool=0.46, wide=True),
    "whitney": dict(title="Whitney", skin=(236, 196, 168), hair=(90, 50, 30), style="bun", coat=(200, 80, 110), shirt=(250, 240, 230),
                    weapon="tape gun", wcol=(220, 60, 60), speed=104, damage=1, reach=30, cool=0.28),
    "rose": dict(title="Momma Rose", skin=(150, 100, 70), hair=(40, 30, 30), style="bob", coat=(170, 40, 90), shirt=(240, 200, 90),
                 weapon="handbag", wcol=(150, 30, 60), speed=84, damage=2, reach=28, cool=0.42),
    "heather": dict(title="Heather", skin=(246, 208, 182), hair=(240, 208, 110), style="long", coat=(46, 120, 124), shirt=(246, 242, 232),
                    weapon="ruler", wcol=(226, 178, 84), speed=100, damage=1, reach=34, cool=0.26),
    "stephen": dict(title="Stephen", skin=(240, 200, 170), hair=(236, 200, 96), style="short", coat=(120, 80, 50), shirt=(90, 110, 140),
                    weapon="wrench", wcol=(170, 176, 190), speed=92, damage=2, reach=26, cool=0.40),
    "alex": dict(title="Alex", skin=(176, 122, 84), hair=(24, 20, 22), style="hightop", coat=(96, 110, 70), shirt=(96, 110, 70),
                 weapon="mic stand", wcol=(190, 190, 200), speed=100, damage=1, reach=40, cool=0.36),
    "kj": dict(title="KJ", skin=(120, 78, 52), hair=(20, 16, 18), style="short", coat=(96, 110, 70), shirt=(96, 110, 70),
               weapon="clipboard", wcol=(150, 104, 60), speed=98, damage=2, reach=24, cool=0.36),
}
ROSTER = ("lucas", "poppa", "whitney", "rose", "heather", "stephen", "alex", "kj")


def _shade(col, f):
    return tuple(max(0, min(255, int(v * f))) for v in col)


def _new(w, h):
    return pygame.Surface((w * SS, h * SS), pygame.SRCALPHA)


def _done(s, scale=1.0):
    return pygame.transform.smoothscale(s, (max(1, int(s.get_width() / SS * scale)), max(1, int(s.get_height() / SS * scale))))


def _limb(s, col, a, b, w):
    A.line(s, col, a, b, w)
    for p in (a, b):
        A.oval(s, col, (p[0] - w / 2, p[1] - w / 2, w, w))


HW, HH = 44, 46                       # a hunter's frame: the figure stands in the middle, facing right


def hunter(kind, pose="stand", frame=0, fire=False, scale=1.0):
    """poses: stand, walk (frames 0-3), jump, attack, hurt, bat."""
    key = ("h", kind, pose, frame, fire, scale)
    if key in _cache:
        return _cache[key]
    d = HUNTERS[kind]
    s = _new(HW, HH)
    cx = 20.0
    if pose == "bat":
        flap = 6 if frame % 2 else -4
        A.poly(s, (40, 34, 56), [(cx, 22), (cx - 16, 14 + flap), (cx - 10, 24), (cx - 15, 28), (cx - 4, 27)], mirror=cx)
        A.oval(s, (56, 48, 76), (cx - 5, 17, 10, 12))
        A.poly(s, (56, 48, 76), [(cx - 4, 18), (cx - 5, 12), (cx - 1, 17)], mirror=cx)
        A.oval(s, (255, 230, 120), (cx - 3, 20, 2, 2), mirror=cx)
        _cache[key] = _done(s, scale)
        return _cache[key]
    skin, coat, shirt, hair = d["skin"], d["coat"], d["shirt"], d["hair"]
    wide = 2.0 if d.get("wide") else 0.0
    swing = (0, 5, 0, -5)[frame % 4] if pose == "walk" else (3 if pose == "jump" else 0)
    lean = -2 if pose == "hurt" else 0
    hip = (cx + lean, 30.0)
    # legs
    for sg, col in ((-1, _shade((40, 44, 70), 0.8)), (1, (40, 44, 70))):
        foot = (hip[0] + sg * swing + (-2 if sg < 0 else 2), 44.0 - (4 if pose == "jump" and sg > 0 else 0))
        _limb(s, col, (hip[0] + sg * 2, hip[1]), foot, 4.4)
        A.poly(s, (30, 26, 30), [(foot[0] - 2.4, foot[1]), (foot[0] + 4, foot[1]), (foot[0] + 4, foot[1] + 2), (foot[0] - 2.4, foot[1] + 2)])
    # the coat tail behind
    if d.get("long_coat"):
        A.poly(s, _shade(coat, 0.8), [(cx - 6, 20), (cx - 9 - swing * 0.4, 40), (cx + 5, 40), (cx + 6, 20)])
    # torso
    A.poly(s, coat, [(cx - 6 - wide, 15), (cx + 6 + wide, 15), (cx + 6.5 + wide, 31), (cx - 6.5 - wide, 31)])
    A.poly(s, shirt, [(cx + 0.5, 15), (cx + 5, 15), (cx + 4, 30), (cx + 1.5, 30)])
    if kind == "lucas":                                             # the works badge
        A.line(s, d["wcol"], (cx + 1.5, 15), (cx + 3.5, 23), 0.6)
        A.poly(s, (250, 250, 250), [(cx + 2.2, 23), (cx + 5.2, 23), (cx + 5.2, 27), (cx + 2.2, 27)])
    # the back arm
    _limb(s, _shade(coat, 0.8), (cx - 4, 17), (cx - 6 - swing * 0.5, 26), 3.6)
    # head
    hx, hy = cx + lean + 0.5, 8.5
    A.oval(s, skin, (hx - 5.5, hy - 6, 11, 12.5))
    st = d["style"]
    if st == "long":
        A.poly(s, hair, [(hx - 6, hy - 3), (hx - 4, hy - 7), (hx + 3, hy - 7), (hx + 5.5, hy - 4), (hx + 2, hy - 4.6), (hx - 2, hy - 2), (hx - 3, hy + 7), (hx - 7.5, hy + 8)])
    elif st == "hightop":
        A.poly(s, hair, [(hx - 5.5, hy - 2), (hx - 5.5, hy - 10), (hx + 5, hy - 10), (hx + 5.5, hy - 4), (hx - 2, hy - 4)])
    elif st == "bun":
        A.oval(s, hair, (hx - 9, hy - 7, 6, 6))
        A.poly(s, hair, [(hx - 6, hy), (hx - 4.5, hy - 7), (hx + 3, hy - 7), (hx + 5.5, hy - 4), (hx - 2, hy - 4)])
    elif st == "bob":
        A.poly(s, hair, [(hx - 6.5, hy + 4), (hx - 5, hy - 7), (hx + 3, hy - 7.4), (hx + 5.8, hy - 4), (hx, hy - 4), (hx - 2.5, hy + 4)])
    elif st == "beard":
        A.poly(s, (40, 34, 36), [(hx - 5, hy - 3), (hx - 3, hy - 6.4), (hx + 3, hy - 6.4), (hx + 5, hy - 4)])
        A.poly(s, hair, [(hx - 3, hy + 2), (hx + 5.5, hy + 2), (hx + 4, hy + 7.5), (hx - 1, hy + 7.5)])
    else:
        A.poly(s, hair, [(hx - 5.6, hy - 1), (hx - 4.5, hy - 7), (hx + 3, hy - 7), (hx + 5.5, hy - 4), (hx - 2, hy - 4)])
    if d.get("shades"):
        A.poly(s, (20, 20, 26), [(hx + 0.5, hy - 1.6), (hx + 5.6, hy - 1.6), (hx + 5.2, hy + 1), (hx + 1, hy + 1)])
        A.line(s, (20, 20, 26), (hx - 4, hy - 1.2), (hx + 1, hy - 1.2), 0.5)
    else:
        A.oval(s, (20, 18, 20), (hx + 2.4, hy - 1.2, 1.6, 2))
    if pose == "hurt":
        A.oval(s, (60, 24, 30), (hx + 2, hy + 3, 3, 2.6))
    else:
        A.line(s, (120, 50, 50), (hx + 2, hy + 3.6), (hx + 5, hy + 3.4), 0.6)
    if kind == "lucas":
        A.poly(s, (255, 255, 255), [(hx + 3.6, hy + 3.8), (hx + 4.6, hy + 3.8), (hx + 4.1, hy + 5.2)])       # a hint of fang
    # the weapon arm
    shoulder = (cx + 3, 17.5)
    if pose == "attack":
        hand = (cx + 11, 18.5)
        _limb(s, coat, shoulder, hand, 3.8)
        reach = d["reach"] * 0.62
        col = (255, 150, 50) if fire else d["wcol"]
        tip = (min(HW - 2, hand[0] + reach), hand[1] - 1)
        if d["weapon"] == "lanyard":
            pts = [(hand[0] + (tip[0] - hand[0]) * i / 6.0, hand[1] + math.sin(i * 1.3) * 1.6) for i in range(7)]
            for a, b in zip(pts, pts[1:]):
                A.line(s, col, a, b, 1.3)
            A.poly(s, (250, 250, 250), [(tip[0] - 2, tip[1] - 2.5), (tip[0] + 2, tip[1] - 2.5), (tip[0] + 2, tip[1] + 2.5), (tip[0] - 2, tip[1] + 2.5)])
            if fire:
                A.oval(s, (255, 220, 90), (tip[0] - 3.5, tip[1] - 4, 7, 7))
        else:
            thick = {"newspaper": 3.4, "handbag": 5.5, "clipboard": 5.0, "tape gun": 4.0}.get(d["weapon"], 2.0)
            A.line(s, col, hand, tip, thick)
            A.line(s, _shade(col, 0.7), (hand[0], hand[1] + thick / 2), (tip[0], tip[1] + thick / 2), 0.5)
        A.oval(s, skin, (hand[0] - 2, hand[1] - 2, 4, 4))
        for i in range(3):
            A.line(s, (255, 255, 255), (tip[0] - 6 - i * 5, tip[1] - 7 - i), (tip[0] - 1 - i * 5, tip[1] - 6), 0.5)
    else:
        hand = (cx + 6 + swing * 0.5, 26.5) if pose != "jump" else (cx + 9, 14)
        _limb(s, coat, shoulder, hand, 3.8)
        A.oval(s, skin, (hand[0] - 2, hand[1] - 2, 4, 4))
    _cache[key] = _done(s, scale)
    return _cache[key]


# ---------------------------------------------------------------- monsters (all face left; the game flips them)
SIZES = {"zombie": (30, 44), "skeleton": (30, 44), "wolf": (40, 42), "bat": (26, 18), "ghost": (28, 34), "vampire": (36, 48)}


def monster(kind, frame=0, scale=1.0, look=None, flash=False):
    key = ("m", kind, frame, scale, look, flash)
    if key in _cache:
        return _cache[key]
    w, h = SIZES[kind]
    s = _new(w, h)
    cx = w / 2.0
    step = 3 if frame % 2 else -3
    if kind == "zombie":
        skin, suit = (126, 170, 110), (70, 76, 100)
        if look == "watchman":
            suit = (40, 50, 90)
        for sg in (-1, 1):
            _limb(s, _shade(suit, 0.75), (cx + sg * 2, 30), (cx + sg * 2 + sg * step, 42), 4.6)
        A.poly(s, suit, [(cx - 7, 15), (cx + 7, 15), (cx + 6.5, 31), (cx - 6.5, 31)])
        A.poly(s, (230, 230, 220), [(cx - 4, 15), (cx - 0.5, 15), (cx - 1.5, 26), (cx - 3.4, 26)])
        A.poly(s, (190, 40, 50), [(cx - 3, 16), (cx - 1.4, 16), (cx - 1.8, 25), (cx - 3, 23)])                # the tie
        _limb(s, suit, (cx - 4, 18), (cx - 13, 19 + step * 0.3), 3.6); A.oval(s, skin, (cx - 16, 17 + step * 0.3, 4.4, 4.4))
        _limb(s, _shade(suit, 0.8), (cx + 2, 18), (cx - 9, 22 - step * 0.3), 3.6); A.oval(s, skin, (cx - 12, 20 - step * 0.3, 4.4, 4.4))
        A.oval(s, skin, (cx - 7, 2, 12, 13))
        A.poly(s, (60, 80, 60), [(cx - 5, 5), (cx - 2, 2), (cx + 5, 3), (cx + 5, 6)])
        A.oval(s, (255, 255, 200), (cx - 5.5, 6.5, 3, 3)); A.oval(s, (20, 20, 20), (cx - 5, 7.4, 1.2, 1.2))
        A.line(s, (50, 70, 50), (cx - 5.5, 11.5), (cx - 1, 11.5), 0.8)
        if look == "watchman":
            A.poly(s, (30, 38, 70), [(cx - 8, 4), (cx - 6, 0), (cx + 5, 0), (cx + 5.5, 4)])
            A.poly(s, (30, 38, 70), [(cx - 11, 4), (cx - 6, 3), (cx - 6, 5)])
            A.oval(s, (240, 200, 70), (cx - 3, 1, 3, 2.4))
    elif kind == "skeleton":
        bone = (236, 232, 214)
        for sg in (-1, 1):
            A.line(s, bone, (cx + sg * 2, 29), (cx + sg * 2 + sg * step, 42), 1.6)
        A.line(s, bone, (cx, 14), (cx, 29), 1.8)
        for ry in (17, 20, 23):
            A.line(s, bone, (cx - 5, ry), (cx + 5, ry), 1.2)
        A.poly(s, bone, [(cx - 4, 28), (cx + 4, 28), (cx + 3, 31), (cx - 3, 31)])
        A.line(s, bone, (cx - 5, 16), (cx - 12, 12 + step), 1.5); A.line(s, bone, (cx + 5, 16), (cx + 9, 24), 1.5)
        A.line(s, bone, (cx - 12, 12 + step), (cx - 15, 8 + step), 2.2)                                      # a bone to throw
        A.oval(s, bone, (cx - 6.5, 1, 12, 12)); A.poly(s, bone, [(cx - 4.5, 11), (cx + 3, 11), (cx + 2, 14.5), (cx - 3.5, 14.5)])
        A.oval(s, (30, 26, 30), (cx - 5, 5, 3.4, 4)); A.oval(s, (30, 26, 30), (cx - 0.5, 5, 3.4, 4))
        A.line(s, (30, 26, 30), (cx - 3.5, 12.8), (cx + 1.6, 12.8), 0.6)
        if look == "mummy":
            for ry in range(3, 42, 5):
                A.line(s, (200, 180, 130), (cx - 6, ry), (cx + 6, ry + 1.5), 1.6)
    elif kind == "wolf":
        fur, dark = (110, 96, 90), (76, 64, 60)
        for sg, lx in ((-1, cx + 7), (1, cx - 3)):
            _limb(s, dark, (lx, 28), (lx - step * sg, 40), 4.4)
        A.poly(s, fur, [(cx - 9, 12), (cx + 10, 15), (cx + 12, 30), (cx - 6, 30)])
        if look == "alpha":
            A.poly(s, (50, 54, 80), [(cx - 8, 14), (cx + 9, 16), (cx + 10, 27), (cx + 3, 30), (cx - 2, 24), (cx - 6, 29)])     # torn suit
            A.poly(s, (190, 40, 50), [(cx - 5, 15), (cx - 3, 15), (cx - 4, 24)])
        _limb(s, fur, (cx - 6, 16), (cx - 15, 22 + step * 0.4), 4.0)
        for k in (-1, 0, 1):
            A.line(s, (240, 240, 230), (cx - 16, 22 + step * 0.4 + k), (cx - 19, 24 + step * 0.4 + k * 2), 0.6)
        A.poly(s, fur, [(cx - 14, 6), (cx - 6, 2), (cx - 1, 6), (cx - 2, 13), (cx - 9, 14), (cx - 18, 11)])  # the head and muzzle
        A.poly(s, fur, [(cx - 7, 3), (cx - 6, -2 + 2), (cx - 3, 4)]); A.poly(s, dark, [(cx - 3, 4), (cx - 1, 0), (cx, 6)])
        A.oval(s, (255, 210, 60), (cx - 10.5, 5.5, 2.6, 2.2)); A.oval(s, (20, 16, 16), (cx - 18.6, 9.4, 2.4, 2))
        A.poly(s, (250, 250, 240), [(cx - 16, 11.6), (cx - 15, 14), (cx - 14, 11.8)]); A.poly(s, (250, 250, 240), [(cx - 13, 12), (cx - 12, 14.4), (cx - 11, 12.2)])
        A.poly(s, dark, [(cx + 10, 22), (cx + 18, 14), (cx + 12, 27)])                                       # the tail
    elif kind == "bat":
        flap = 5 if frame % 2 else -3
        A.poly(s, (70, 50, 90), [(cx, 10), (cx - 12, 4 + flap), (cx - 8, 11), (cx - 11, 14), (cx - 3, 13)], mirror=cx)
        A.oval(s, (90, 66, 114), (cx - 4, 5, 8, 10))
        A.poly(s, (90, 66, 114), [(cx - 3.4, 6), (cx - 4, 1.5), (cx - 0.8, 5)], mirror=cx)
        A.oval(s, (255, 80, 80), (cx - 2.6, 8, 1.8, 1.8), mirror=cx)
    elif kind == "ghost":
        body = pygame.Surface((w * SS, h * SS), pygame.SRCALPHA)
        A.oval(body, (220, 236, 250), (4, 2, 20, 22))
        wob = 2 if frame % 2 else 0
        A.poly(body, (220, 236, 250), [(4, 13), (24, 13), (24, 31), (20, 27 + wob), (16, 32), (12, 27 + wob), (8, 32 - wob), (4, 28)])
        A.oval(body, (30, 40, 70), (8, 10, 4, 6)); A.oval(body, (30, 40, 70), (14.5, 10, 4, 6))
        A.oval(body, (30, 40, 70), (11, 19, 5, 6 if look != "banshee" else 10))
        if look == "banshee":
            A.poly(body, (150, 190, 210), [(3, 12), (6, 1), (22, 1), (25, 12), (27, 30), (22, 14), (6, 14), (1, 30)])
        body.set_alpha(215)
        s.blit(body, (0, 0))
    else:                                                            # vampire
        cape, lining = (30, 26, 40), (150, 30, 50)
        if look == "twin_b":
            lining = (60, 60, 170)
        if look == "chairman":
            cape, lining = (60, 20, 30), (220, 180, 60)
        A.poly(s, cape, [(cx - 7, 13), (cx + 7, 13), (cx + 14, 44 + step * 0.3), (cx - 14, 44 - step * 0.3)])
        A.poly(s, lining, [(cx - 4, 15), (cx + 4, 15), (cx + 6, 44), (cx - 6, 44)])
        A.poly(s, (24, 22, 30), [(cx - 4.5, 15), (cx + 4.5, 15), (cx + 4, 34), (cx - 4, 34)])
        A.poly(s, (240, 240, 240), [(cx - 2, 15), (cx + 2, 15), (cx, 22)])
        for sg in (-1, 1):
            _limb(s, (24, 22, 30), (cx + sg * 2, 33), (cx + sg * 2.5, 45), 3.6)
        A.poly(s, cape, [(cx - 7, 13), (cx - 10, 7), (cx - 4, 12)], mirror=cx)                               # the high collar
        A.oval(s, (214, 220, 226), (cx - 6, 1, 11.5, 13))
        A.poly(s, (20, 18, 24), [(cx - 6, 5), (cx - 4, 0.5), (cx + 5, 0.5), (cx + 5.5, 5), (cx, 2.6)])
        A.oval(s, (230, 40, 50), (cx - 5, 6, 2.6, 2.2)); A.oval(s, (230, 40, 50), (cx - 0.5, 6, 2.6, 2.2))
        A.line(s, (120, 30, 40), (cx - 4.4, 10.6), (cx + 0.6, 10.6), 0.6)
        A.poly(s, (255, 255, 255), [(cx - 4, 10.8), (cx - 3, 10.8), (cx - 3.5, 13)]); A.poly(s, (255, 255, 255), [(cx - 1, 10.8), (cx, 10.8), (cx - 0.5, 13)])
        if look == "chairman":
            A.poly(s, (236, 196, 70), [(cx - 5, 1), (cx - 5, -3 + 3), (cx - 2.5, 0.5), (cx - 0.5, -3 + 2.6), (cx + 1.5, 0.5), (cx + 4, 0), (cx + 4, 1.4)])
    out = _done(s, scale)
    if flash:
        white = out.copy()
        white.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
        out = white
    _cache[key] = out
    return out


def small(kind, scale=1.0):
    """Pickups and props."""
    if ("s", kind, scale) in _cache:
        return _cache[("s", kind, scale)]
    s = _new(16, 20)
    if kind == "heart":
        A.oval(s, (232, 70, 90), (2, 5, 7, 7)); A.oval(s, (232, 70, 90), (7, 5, 7, 7)); A.poly(s, (232, 70, 90), [(2.4, 9.5), (13.6, 9.5), (8, 16)])
        A.oval(s, (255, 170, 180), (4, 6.4, 2.4, 2.4))
    elif kind == "lamp":
        A.poly(s, (90, 90, 100), [(6, 18), (10, 18), (9, 10), (7, 10)]); A.poly(s, (240, 220, 140), [(3, 10), (13, 10), (10.5, 3), (5.5, 3)])
        A.oval(s, (255, 250, 200), (6, 8, 4, 3))
    elif kind == "card":
        A.poly(s, (60, 30, 90), [(3, 2), (13, 2), (13, 18), (3, 18)]); A.poly(s, (236, 196, 70), [(4.2, 3.2), (11.8, 3.2), (11.8, 16.8), (4.2, 16.8)])
        A.poly(s, (60, 30, 90), [(5, 4), (11, 4), (11, 16), (5, 16)]); A.oval(s, (236, 196, 70), (6.4, 8, 3.2, 4))
    elif kind == "chest":
        A.poly(s, (120, 76, 40), [(1, 9), (15, 9), (15, 19), (1, 19)]); A.poly(s, (150, 100, 56), [(1, 9), (3, 4), (13, 4), (15, 9)])
        A.poly(s, (236, 196, 70), [(7, 8), (9, 8), (9, 12), (7, 12)]); A.line(s, (236, 196, 70), (1, 9), (15, 9), 0.7)
    elif kind == "bone":
        A.line(s, (236, 232, 214), (4, 10), (12, 10), 2); A.oval(s, (236, 232, 214), (2, 7.6, 3.4, 5)); A.oval(s, (236, 232, 214), (10.6, 7.6, 3.4, 5))
    elif kind == "staple":
        A.line(s, (220, 226, 240), (3, 10), (13, 10), 1.6); A.line(s, (220, 226, 240), (3, 10), (3, 13), 1.2); A.line(s, (220, 226, 240), (13, 10), (13, 13), 1.2)
    elif kind == "scream":
        for r in (3, 6, 9):
            pygame.draw.arc(s, (190, 230, 255), ((8 - r) * SS, (10 - r) * SS, 2 * r * SS, 2 * r * SS), math.pi * 0.6, math.pi * 1.4, SS)
    elif kind == "wave":
        A.poly(s, (255, 230, 150), [(1, 19), (5, 8), (8, 15), (11, 6), (15, 19)])
    elif kind == "orb":
        A.oval(s, (160, 40, 70), (3, 5, 10, 10)); A.oval(s, (255, 140, 160), (5, 7, 4, 4))
    _cache[("s", kind, scale)] = _done(s, scale)
    return _cache[("s", kind, scale)]


def backdrop(stage, width=800, height=240):
    """A wide wall painting for one stage: the factory, getting grander and spookier as Lucas climbs."""
    key = ("bg", stage)
    if key in _cache:
        return _cache[key]
    rng = random.Random(40 + stage)
    wall, trim, night = (((54, 60, 74), (40, 44, 56), (20, 24, 50)), ((84, 74, 70), (60, 52, 50), (24, 22, 54)),
                         ((70, 82, 78), (50, 60, 58), (26, 26, 60)), ((40, 50, 66), (28, 36, 50), (16, 18, 44)),
                         ((60, 40, 50), (44, 28, 36), (30, 16, 46)))[stage]
    s = pygame.Surface((width, height))
    s.fill(wall)
    for x in range(0, width, 100):                                    # tall windows with the moon outside
        pygame.draw.rect(s, trim, (x + 22, 26, 56, 96))
        pygame.draw.rect(s, night, (x + 26, 30, 48, 88))
        pygame.draw.circle(s, (236, 232, 200), (x + 60, 50), 9)
        pygame.draw.circle(s, night, (x + 56, 47), 8)
        pygame.draw.line(s, trim, (x + 50, 30), (x + 50, 118), 2); pygame.draw.line(s, trim, (x + 26, 74), (x + 74, 74), 2)
        for _ in range(3):
            wx, wy = x + rng.randrange(26, 70), rng.randrange(30, 60)
            pygame.draw.line(s, (120, 126, 150), (wx, 30), (wx + rng.randrange(-8, 8), wy))
    for x in range(0, width, 100):                                    # what stands along the wall
        bx = x + 84
        if stage == 0:                                                # crates and drums on the loading dock
            pygame.draw.rect(s, (110, 80, 50), (bx, 150, 30, 30)); pygame.draw.rect(s, (80, 56, 34), (bx, 150, 30, 30), 2)
            pygame.draw.line(s, (80, 56, 34), (bx, 150), (bx + 30, 180), 2)
        elif stage == 1:                                              # pill presses
            pygame.draw.rect(s, (130, 140, 150), (bx, 128, 26, 52)); pygame.draw.circle(s, (220, 60, 60), (bx + 13, 140), 4)
            pygame.draw.rect(s, (90, 100, 110), (bx + 6, 150, 14, 30))
        elif stage == 2:                                              # the bottling line
            for k in range(3):
                pygame.draw.rect(s, (200, 150, 70), (bx + k * 10, 160, 7, 14)); pygame.draw.rect(s, (250, 250, 250), (bx + k * 10 + 1, 156, 5, 4))
            pygame.draw.rect(s, (60, 66, 76), (bx - 6, 174, 44, 6))
        elif stage == 3:                                              # glassware in the laboratory
            pygame.draw.polygon(s, (120, 220, 160), [(bx + 8, 180), (bx + 22, 180), (bx + 17, 160), (bx + 17, 150), (bx + 13, 150), (bx + 13, 160)])
            pygame.draw.rect(s, (60, 66, 76), (bx - 6, 180, 44, 4))
        else:                                                         # portraits on the executive floor
            pygame.draw.rect(s, (200, 160, 60), (bx, 130, 26, 34)); pygame.draw.rect(s, (40, 30, 40), (bx + 3, 133, 20, 28))
            pygame.draw.circle(s, (214, 220, 226), (bx + 13, 144), 5); pygame.draw.circle(s, (230, 40, 50), (bx + 11, 143), 1); pygame.draw.circle(s, (230, 40, 50), (bx + 15, 143), 1)
    for _ in range(18):                                               # cobwebs in the corners
        x, y = rng.randrange(width), rng.choice((0, 0, 122))
        for a in (0.3, 0.8, 1.3):
            pygame.draw.line(s, (150, 150, 160), (x, y), (x + math.cos(a) * 16, y + math.sin(a) * 16))
    _cache[key] = s
    return s


# ---------------------------------------------------------------- full resolution (800 x 480) drawing
K = 2.4                                # sprite size on the full screen: a little larger than twice the old one
PAD = 3                                # room for the ink outline
INK = (14, 10, 22)


def inked(img, flash=False):
    """A sprite with a dark outline round it, so it stands off any background. flash = solid white."""
    mask = pygame.mask.from_surface(img, 60)
    w, h = img.get_size()
    out = pygame.Surface((w + 2 * PAD, h + 2 * PAD), pygame.SRCALPHA)
    edge = mask.to_surface(setcolor=INK + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, -2), (-2, 2), (2, 2), (0, 3)):
        out.blit(edge, (PAD + dx, PAD + dy))
    out.blit(mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)) if flash else img, (PAD, PAD))
    return out


def hd_hunter(kind, pose="stand", frame=0, fire=False, face=1, size=K):
    key = ("hh", kind, pose, frame, fire, face, size)
    if key not in _cache:
        img = inked(hunter(kind, pose, frame, fire, size))
        _cache[key] = img if face > 0 else pygame.transform.flip(img, True, False)
    return _cache[key]


def hd_monster(kind, frame=0, scale=1.0, look=None, flash=False, face=-1, size=K):
    key = ("hm", kind, frame, scale, look, flash, face, size)
    if key not in _cache:
        img = inked(monster(kind, frame, scale * size, look), flash)
        _cache[key] = img if face < 0 else pygame.transform.flip(img, True, False)
    return _cache[key]


def hd_small(kind, flip=False, size=2.2):
    key = ("hs", kind, flip, size)
    if key not in _cache:
        img = inked(small(kind, size))
        _cache[key] = pygame.transform.flip(img, True, False) if flip else img
    return _cache[key]


def glow(radius, col):
    """A soft round light, to be added onto the picture."""
    key = ("glow", radius, col)
    if key not in _cache:
        s = pygame.Surface((radius * 2, radius * 2))
        for r in range(radius, 0, -3):
            k = (1 - r / float(radius)) ** 2
            pygame.draw.circle(s, tuple(int(v * k) for v in col), (radius, radius), r)
        _cache[key] = s
    return _cache[key]


def vignette():
    """Darkness creeping in from the corners."""
    if "vig" not in _cache:
        small_s = pygame.Surface((100, 60), pygame.SRCALPHA)
        for y in range(60):
            for x in range(100):
                d = math.hypot((x - 50) / 50.0, (y - 30) / 30.0)
                small_s.set_at((x, y), (6, 4, 14, int(max(0.0, min(1.0, (d - 0.55) / 0.85)) * 190)))
        _cache["vig"] = pygame.transform.smoothscale(small_s, (800, 480))
    return _cache["vig"]


THEMES = (   # wall top, wall bottom, trim, floor, accent light
    ((44, 50, 70), (26, 28, 44), (70, 76, 100), (58, 60, 72), (120, 150, 220)),
    ((74, 60, 62), (40, 30, 36), (110, 90, 86), (84, 70, 66), (230, 160, 110)),
    ((50, 70, 70), (24, 36, 40), (84, 110, 108), (60, 80, 78), (130, 220, 190)),
    ((34, 44, 70), (16, 20, 40), (60, 76, 116), (44, 54, 78), (150, 130, 240)),
    ((70, 34, 48), (34, 14, 26), (130, 70, 80), (90, 44, 56), (240, 190, 90)),
)


def wall(stage, width=1600, height=416):
    """The back wall of a floor at full resolution: stonework, tall arched windows with the moon outside and
    its light falling in, pillars, and whatever the factory keeps on this floor."""
    key = ("wall", stage)
    if key in _cache:
        return _cache[key]
    rng = random.Random(70 + stage)
    top, bottom, trim, _, light = THEMES[stage]
    s = pygame.Surface((width, height))
    for y in range(0, height, 2):
        k = y / float(height)
        pygame.draw.rect(s, tuple(int(a + (b - a) * k) for a, b in zip(top, bottom)), (0, y, width, 2))
    for row in range(0, height, 26):                                   # stone courses
        off = 0 if (row // 26) % 2 else 40
        pygame.draw.line(s, _shade(bottom, 0.8), (0, row), (width, row))
        for x in range(off, width, 80):
            pygame.draw.line(s, _shade(bottom, 0.8), (x, row), (x, row + 26))
            if rng.random() < 0.12:
                pygame.draw.rect(s, _shade(top, 1.12), (x + 2, row + 2, 76, 22))
    rays = pygame.Surface((width, height), pygame.SRCALPHA)
    for x in range(0, width, 400):                                     # two windows and a pillar in every 400
        for wx in (x + 70, x + 250):
            pygame.draw.rect(s, _shade(trim, 0.7), (wx - 8, 60, 96, 220))
            pygame.draw.ellipse(s, _shade(trim, 0.7), (wx - 8, 16, 96, 96))
            night = pygame.Rect(wx, 68, 80, 204)
            for y in range(night.top - 40, night.bottom, 2):
                k = (y - night.top + 40) / 244.0
                pygame.draw.rect(s, (int(14 + 30 * k), int(16 + 34 * k), int(44 + 60 * k)), (wx, y, 80, 2))
            pygame.draw.polygon(s, _shade(trim, 0.7), [(wx, 28), (wx, 68), (wx + 6, 44), (wx + 20, 30)])
            pygame.draw.polygon(s, _shade(trim, 0.7), [(wx + 80, 28), (wx + 80, 68), (wx + 74, 44), (wx + 60, 30)])
            if wx == x + 70:
                pygame.draw.circle(s, (250, 246, 220), (wx + 52, 96), 17)
                pygame.draw.circle(s, (226, 220, 190), (wx + 46, 92), 4); pygame.draw.circle(s, (226, 220, 190), (wx + 58, 102), 3)
            for _ in range(5):
                pygame.draw.circle(s, (230, 230, 255), (wx + rng.randrange(6, 74), rng.randrange(50, 180)), 1)
            for cx_, cy_ in ((wx + 14, 170), (wx + 44, 190)):          # drifting cloud
                pygame.draw.ellipse(s, (60, 64, 104), (cx_, cy_, 40, 10))
            pygame.draw.line(s, trim, (wx + 40, 30), (wx + 40, 272), 4)
            for by in (120, 196):
                pygame.draw.line(s, trim, (wx, by), (wx + 80, by), 4)
            pygame.draw.rect(s, trim, (wx - 14, 272, 108, 10))
            pygame.draw.polygon(rays, light + (26,), [(wx, 80), (wx + 80, 80), (wx + 190, height), (wx + 30, height)])
        px = x + 180                                                   # the pillar
        pygame.draw.rect(s, trim, (px, 0, 44, height))
        pygame.draw.rect(s, _shade(trim, 1.25), (px + 4, 0, 8, height))
        pygame.draw.rect(s, _shade(trim, 0.7), (px + 32, 0, 12, height))
        pygame.draw.rect(s, _shade(trim, 1.1), (px - 8, 0, 60, 16)); pygame.draw.rect(s, _shade(trim, 1.1), (px - 8, height - 18, 60, 18))
        bx = x + 330                                                   # what this floor keeps
        base = height
        if stage == 0:
            for i, (dx, dy, sz) in enumerate(((0, 0, 56), (50, 0, 44), (14, -56, 44))):
                r = pygame.Rect(bx + dx, base - sz + dy, sz, sz)
                pygame.draw.rect(s, (124, 88, 52), r); pygame.draw.rect(s, (84, 58, 34), r, 4)
                pygame.draw.line(s, (84, 58, 34), r.topleft, r.bottomright, 4); pygame.draw.line(s, (84, 58, 34), r.topright, r.bottomleft, 4)
        elif stage == 1:
            pygame.draw.rect(s, (120, 128, 140), (bx, base - 130, 70, 130), border_radius=6)
            pygame.draw.rect(s, (80, 86, 98), (bx + 10, base - 70, 50, 70))
            pygame.draw.rect(s, (60, 64, 74), (bx + 26, base - 150, 18, 24))
            for i, col in enumerate(((230, 70, 70), (240, 200, 70), (90, 200, 110))):
                pygame.draw.circle(s, col, (bx + 16 + i * 19, base - 108), 6)
            for i in range(4):
                pygame.draw.ellipse(s, (240, 240, 245), (bx + 76 + i * 12, base - 12, 10, 6))
        elif stage == 2:
            pygame.draw.rect(s, (56, 62, 72), (bx - 30, base - 36, 150, 10)); pygame.draw.rect(s, (40, 44, 52), (bx - 20, base - 26, 8, 26)); pygame.draw.rect(s, (40, 44, 52), (bx + 100, base - 26, 8, 26))
            for i in range(6):
                pygame.draw.rect(s, (190, 130, 60), (bx - 22 + i * 22, base - 66, 14, 30), border_radius=3)
                pygame.draw.rect(s, (250, 250, 250), (bx - 19 + i * 22, base - 74, 8, 8)); pygame.draw.rect(s, (240, 236, 220), (bx - 21 + i * 22, base - 56, 12, 10))
        elif stage == 3:
            pygame.draw.rect(s, (56, 62, 82), (bx - 30, base - 44, 150, 10)); pygame.draw.rect(s, (40, 44, 60), (bx - 22, base - 34, 8, 34)); pygame.draw.rect(s, (40, 44, 60), (bx + 104, base - 34, 8, 34))
            for i, col in enumerate(((120, 230, 160), (230, 120, 220), (120, 180, 250))):
                fx = bx - 14 + i * 44
                pygame.draw.polygon(s, (200, 220, 230), [(fx, base - 44), (fx + 30, base - 44), (fx + 20, base - 76), (fx + 20, base - 96), (fx + 10, base - 96), (fx + 10, base - 76)])
                pygame.draw.polygon(s, col, [(fx + 3, base - 46), (fx + 27, base - 46), (fx + 21, base - 64), (fx + 9, base - 64)])
                pygame.draw.circle(s, col, (fx + 15, base - 110 - i * 6), 3)
        else:
            pygame.draw.rect(s, (206, 164, 62), (bx, base - 250, 84, 108)); pygame.draw.rect(s, (40, 26, 40), (bx + 8, base - 242, 68, 92))
            pygame.draw.ellipse(s, (214, 220, 226), (bx + 28, base - 226, 28, 34)); pygame.draw.polygon(s, (30, 20, 30), [(bx + 16, base - 152), (bx + 42, base - 196), (bx + 68, base - 152)])
            pygame.draw.circle(s, (230, 40, 50), (bx + 36, base - 212), 3); pygame.draw.circle(s, (230, 40, 50), (bx + 48, base - 212), 3)
            pygame.draw.rect(s, (120, 30, 40), (bx - 10, base - 110, 104, 110)); pygame.draw.rect(s, (160, 50, 60), (bx - 10, base - 110, 104, 14))
    s.blit(rays, (0, 0))
    for x in range(0, width, 200):                                     # cobwebs up in the corners
        cx_ = x + rng.randrange(0, 60)
        for a in (0.2, 0.6, 1.0, 1.4):
            pygame.draw.line(s, (170, 170, 186), (cx_, 0), (cx_ + math.cos(a) * 46, math.sin(a) * 46))
        for r in (16, 30, 44):
            pygame.draw.arc(s, (170, 170, 186), (cx_ - r, -r, 2 * r, 2 * r), -1.45, -0.15, 1)
    _cache[key] = s
    return s


def beams(stage, width=1200, height=70):
    """Dark pipes and chains along the ceiling, nearer than the wall, so they slide past faster."""
    key = ("beams", stage)
    if key in _cache:
        return _cache[key]
    rng = random.Random(90 + stage)
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    dark = (12, 10, 20)
    pygame.draw.rect(s, dark, (0, 0, width, 12))
    pygame.draw.rect(s, (30, 28, 44), (0, 12, width, 3))
    for x in range(0, width, 150):
        pygame.draw.rect(s, dark, (x + 20, 0, 14, 26))
        length = rng.randrange(24, 60)
        for y in range(14, length, 7):                                 # a hanging chain
            pygame.draw.ellipse(s, dark, (x + 90, y, 6, 9), 2)
        if rng.random() < 0.5:
            pygame.draw.polygon(s, dark, [(x + 84, length), (x + 102, length), (x + 93, length + 12)])
    _cache[key] = s
    return s
