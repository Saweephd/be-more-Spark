"""Angry Poppa: clear the fungus gnats out of the house.

A side scroller in the look of late 1980s console action games. All art here is
original and drawn in code.

The house has three floors. Each stage scrolls through the rooms of one floor:
up through the first, second and third floors, then back down through the
second and first, with the gnats getting tougher at every stage. The queen
waits at the end of the last one.

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

On every floor: clear every plant pot (the gnats hatch there), then take the stairs.
"""
import math
import random

import pygame

from . import common as c
from .common import H, W, Game, sprite, text

FLOOR = 208
GRAVITY = 900.0
MAX_GNATS = 26

# ---------------------------------------------------------------- hero art
HERO_PAL = {"H": (24, 20, 20), "B": (30, 24, 22), "S": (124, 80, 52), "s": (96, 60, 40), "E": (245, 245, 245),
            "J": (34, 38, 60), "j": (58, 64, 98), "W": (240, 240, 244), "T": (190, 40, 50), "K": (14, 14, 18)}
_TOP = [
    "......HHHHHH......",
    ".....HHHHHHHH.....",
    "....HHHHHHHHHH....",
    "....HHSSSSSSSS....",
    "....HSSSSSSSSS....",
    "....SSEKSSSEKS....",
    "....SSSSSSSSSS....",
    "....BSSSSssSSB....",
    "....BBBBBBBBBB....",
    ".....BBBssBBBB....",
    "......BBBBBBB.....",
    ".......SBBBS......",
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
DART_PAL = dict(ART_PAL, k=(150, 20, 30), w=(250, 190, 190))
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

# ---------------------------------------------------------------- furniture
# kind: (width, height, tops) where tops are the heights you can stand on.
WOOD, WOOD_D, WOOD_L = (150, 104, 66), (120, 82, 52), (176, 128, 86)
FURN = {
    "sofa": (72, 40, (22,)), "armchair": (32, 40, (22,)), "coffee": (44, 16, (16,)), "tv": (56, 62, (24,)),
    "bookshelf": (40, 88, (88, 46)), "dining": (92, 34, (34,)), "chair": (16, 40, ()), "sideboard": (56, 38, (38,)),
    "stove": (36, 36, (36,)), "fridge": (40, 96, (96,)), "bed": (88, 34, (24,)), "nightstand": (20, 22, (22,)),
    "dresser": (46, 40, (40,)), "wardrobe": (46, 92, (92,)), "desk": (64, 34, (34,)), "bench": (84, 36, (36,)),
    "crate": (30, 26, (26,)), "trunk": (44, 22, (22,)),
}


def R(surf, col, x, y, w, h):
    pygame.draw.rect(surf, col, (int(x), int(y), int(w), int(h)))


def draw_furniture(surf, kind, x, w=None, top=None):
    """Draw one piece with its left edge at screen x, standing on the floor."""
    f = FLOOR
    x = int(x)
    if kind == "counter":
        R(surf, (236, 236, 228), x, f - 36, w, 5)
        R(surf, WOOD, x + 2, f - 31, w - 4, 31)
        for dx in range(26, int(w) - 8, 44):
            R(surf, WOOD_D, x + dx, f - 26, 2, 22)
        return
    if kind == "shelf":
        R(surf, WOOD_L, x, f - top, w, 4)
        R(surf, WOOD_D, x + 4, f - top + 4, 3, 6)
        R(surf, WOOD_D, x + w - 7, f - top + 4, 3, 6)
        return
    if kind == "window":
        R(surf, (150, 210, 250), x, 70, 64, 52)
        pygame.draw.rect(surf, (250, 250, 250), (x, 70, 64, 52), 3)
        R(surf, (250, 250, 250), x + 31, 70, 3, 52)
        R(surf, (250, 250, 250), x, 95, 64, 3)
        return
    if kind == "picture":
        R(surf, WOOD_D, x, 60, 34, 26)
        R(surf, (120, 170, 200), x + 3, 63, 28, 20)
        pygame.draw.polygon(surf, (90, 140, 90), [(x + 3, 83), (x + 14, 70), (x + 24, 83)])
        return
    if kind == "lamp":
        R(surf, (90, 90, 100), x + 6, f - 70, 2, 70)
        pygame.draw.polygon(surf, (250, 230, 170), [(x, f - 70), (x + 14, f - 70), (x + 11, f - 86), (x + 3, f - 86)])
        return
    if kind == "rug":
        R(surf, (150, 60, 70), x, f + 6, w, 10)
        R(surf, (200, 150, 90), x + 4, f + 9, w - 8, 4)
        return
    fw, fh, _ = FURN[kind]
    y = f - fh
    if kind == "sofa" or kind == "armchair":
        col, dark = ((70, 110, 150), (50, 84, 120)) if kind == "sofa" else ((150, 80, 70), (116, 58, 52))
        R(surf, dark, x, y, fw, fh - 4)
        R(surf, col, x + 6, f - 22, fw - 12, 12)
        R(surf, col, x, f - 28, 7, 24)
        R(surf, col, x + fw - 7, f - 28, 7, 24)
        R(surf, (40, 40, 46), x + 3, f - 4, 4, 4)
        R(surf, (40, 40, 46), x + fw - 7, f - 4, 4, 4)
    elif kind == "coffee":
        R(surf, WOOD_L, x, y, fw, 4)
        R(surf, WOOD_D, x + 4, y + 4, 3, 12)
        R(surf, WOOD_D, x + fw - 7, y + 4, 3, 12)
    elif kind == "tv":
        R(surf, WOOD, x, f - 24, fw, 24)
        R(surf, WOOD_D, x + 4, f - 18, fw - 8, 2)
        R(surf, (20, 20, 26), x + 4, y, fw - 8, 34)
        R(surf, (60, 90, 130), x + 7, y + 3, fw - 14, 28)
        R(surf, (20, 20, 26), x + fw // 2 - 4, f - 28, 8, 4)
    elif kind == "bookshelf":
        R(surf, WOOD_D, x, y, fw, fh)
        for i, sy in enumerate((y + 4, f - 46 + 4, f - 22)):
            R(surf, (60, 40, 30), x + 3, sy, fw - 6, 18)
            for b in range(6):
                R(surf, ((190, 60, 60), (60, 120, 190), (220, 190, 80), (80, 160, 100))[(b + i) % 4], x + 4 + b * 5, sy + 4, 4, 14)
        R(surf, WOOD_L, x, f - 46, fw, 3)
    elif kind == "dining":
        R(surf, WOOD_L, x, y, fw, 5)
        R(surf, WOOD_D, x + 6, y + 5, 4, 29)
        R(surf, WOOD_D, x + fw - 10, y + 5, 4, 29)
    elif kind == "chair":
        R(surf, WOOD, x + 1, y, 3, 40)
        R(surf, WOOD, x + 1, f - 20, 14, 3)
        R(surf, WOOD, x + 12, f - 20, 3, 20)
    elif kind in ("sideboard", "dresser", "nightstand"):
        R(surf, WOOD, x, y, fw, fh)
        R(surf, WOOD_L, x, y, fw, 3)
        for dy in range(7, fh - 6, 11):
            R(surf, WOOD_D, x + 3, y + dy, fw - 6, 1)
            R(surf, (230, 200, 120), x + fw // 2 - 2, y + dy + 4, 4, 2)
    elif kind == "stove":
        R(surf, (60, 62, 70), x, y, fw, fh)
        R(surf, (30, 30, 36), x + 5, y + 12, fw - 10, 18)
        for i in range(3):
            pygame.draw.circle(surf, (200, 60, 50), (x + 8 + i * 10, y + 6), 2)
    elif kind == "fridge":
        R(surf, (214, 220, 228), x, y, fw, fh)
        pygame.draw.rect(surf, (160, 168, 180), (x, y, fw, fh), 2)
        R(surf, (160, 168, 180), x, y + 34, fw, 2)
        R(surf, (120, 128, 140), x + 5, y + 14, 3, 16)
        R(surf, (120, 128, 140), x + 5, y + 42, 3, 26)
    elif kind == "bed":
        R(surf, WOOD_D, x, y, 6, fh)
        R(surf, WOOD_D, x + fw - 4, f - 20, 4, 20)
        R(surf, (236, 236, 240), x + 6, f - 24, fw - 10, 10)
        R(surf, (90, 110, 170), x + 30, f - 24, fw - 34, 10)
        R(surf, WOOD, x + 6, f - 14, fw - 10, 10)
        R(surf, (250, 250, 250), x + 8, f - 29, 18, 6)
    elif kind == "wardrobe":
        R(surf, WOOD, x, y, fw, fh)
        R(surf, WOOD_D, x + fw // 2 - 1, y + 4, 2, fh - 8)
        R(surf, (230, 200, 120), x + fw // 2 - 5, y + 44, 2, 8)
        R(surf, (230, 200, 120), x + fw // 2 + 3, y + 44, 2, 8)
    elif kind == "desk":
        R(surf, WOOD_L, x, y, fw, 4)
        R(surf, WOOD, x, y + 4, 18, 30)
        R(surf, WOOD_D, x + fw - 4, y + 4, 4, 30)
        R(surf, (40, 40, 48), x + 28, y - 20, 26, 18)
        R(surf, (110, 170, 220), x + 30, y - 18, 22, 14)
        R(surf, (40, 40, 48), x + 39, y - 2, 4, 2)
    elif kind == "bench":
        R(surf, (120, 124, 134), x, y, fw, 4)
        R(surf, (80, 84, 94), x + 4, y + 4, 4, 32)
        R(surf, (80, 84, 94), x + fw - 8, y + 4, 4, 32)
        R(surf, (80, 84, 94), x + 4, f - 12, fw - 8, 3)
        for px in (10, 48):                                  # two little 3D printers
            pygame.draw.rect(surf, (150, 156, 170), (x + px, y - 24, 24, 24), 2)
            R(surf, (250, 210, 70), x + px + 4, y - 18, 14, 2)
            R(surf, (60, 200, 90), x + px + 7, y - 8, 9, 6)
    elif kind in ("crate", "trunk"):
        R(surf, (166, 130, 84), x, y, fw, fh)
        pygame.draw.rect(surf, (120, 92, 58), (x, y, fw, fh), 2)
        R(surf, (120, 92, 58), x, y + fh // 2, fw, 2)


# Rooms: name, width, wall colour, floor colour, things in it.
# A thing is (kind, x) or ("counter", x, width) or ("shelf", x, height, width) or ("rug", x, width).
FIRST_FLOOR = [
    ("Den", 380, (176, 150, 124), (120, 84, 60),
     [("window", 96), ("picture", 20), ("sofa", 24), ("coffee", 116), ("bookshelf", 184), ("lamp", 236), ("tv", 280), ("rug", 30, 150)]),
    ("Living room", 430, (214, 200, 176), (150, 110, 76),
     [("window", 170), ("picture", 60), ("armchair", 20), ("sofa", 70), ("coffee", 160), ("shelf", 250, 104, 60), ("lamp", 320), ("bookshelf", 350), ("rug", 60, 170)]),
    ("Dining room", 400, (198, 180, 160), (140, 100, 70),
     [("window", 290), ("picture", 150), ("sideboard", 20), ("chair", 110), ("dining", 130), ("chair", 226), ("shelf", 262, 108, 56), ("rug", 110, 140)]),
    ("Kitchen", 450, (244, 232, 204), (170, 124, 84),
     [("window", 216), ("counter", 20, 150), ("shelf", 56, 104, 70), ("stove", 170), ("counter", 206, 96), ("fridge", 312), ("counter", 356, 74)]),
]
SECOND_FLOOR = [
    ("Hallway", 280, (206, 196, 182), (132, 96, 70),
     [("picture", 30), ("picture", 150), ("sideboard", 60), ("lamp", 150), ("wardrobe", 200), ("rug", 20, 240)]),
    ("Main bedroom", 450, (188, 196, 214), (150, 116, 90),
     [("window", 220), ("nightstand", 20), ("bed", 44), ("nightstand", 136), ("dresser", 196), ("shelf", 250, 108, 56), ("wardrobe", 330), ("rug", 40, 130)]),
    ("Office", 420, (200, 208, 190), (128, 96, 68),
     [("window", 60), ("picture", 280), ("desk", 30), ("bookshelf", 124), ("shelf", 176, 106, 60), ("desk", 250), ("bookshelf", 350)]),
    ("Guest bedroom", 400, (220, 198, 196), (150, 116, 90),
     [("window", 250), ("dresser", 20), ("bed", 96), ("nightstand", 188), ("shelf", 220, 104, 56), ("armchair", 300), ("lamp", 350)]),
]
THIRD_FLOOR = [
    ("Landing", 260, (190, 186, 176), (118, 90, 66),
     [("picture", 90), ("trunk", 30), ("crate", 110), ("lamp", 170), ("bookshelf", 196)]),
    ("Workshop", 470, (176, 184, 196), (104, 104, 110),
     [("window", 300), ("bench", 24), ("shelf", 60, 110, 70), ("crate", 130), ("bench", 190), ("shelf", 300, 104, 60), ("wardrobe", 390)]),
    ("Back bedroom", 400, (204, 190, 210), (150, 116, 90),
     [("window", 40), ("bed", 30), ("nightstand", 124), ("dresser", 190), ("shelf", 250, 106, 56), ("armchair", 330)]),
    ("Attic study", 420, (170, 156, 140), (110, 82, 58),
     [("picture", 200), ("trunk", 20), ("crate", 70), ("crate", 100), ("desk", 160), ("bookshelf", 250), ("shelf", 300, 108, 56), ("trunk", 360)]),
]

# One entry per stage: title, rooms, walking direction, and how nasty the gnats are.
STAGES = [
    dict(title="First floor", rooms=FIRST_FLOOR, direction=1, speed=1.0, per_room=3, pots=3, pot_hp=3, hatch=(3.5, 5.5), fat=0.0, dart=0.0),
    dict(title="Second floor", rooms=SECOND_FLOOR, direction=1, speed=1.1, per_room=4, pots=4, pot_hp=3, hatch=(3.0, 5.0), fat=0.2, dart=0.0),
    dict(title="Third floor", rooms=THIRD_FLOOR, direction=1, speed=1.2, per_room=4, pots=4, pot_hp=4, hatch=(2.6, 4.4), fat=0.25, dart=0.15),
    dict(title="Back down: second floor", rooms=SECOND_FLOOR, direction=-1, speed=1.3, per_room=5, pots=5, pot_hp=4, hatch=(2.3, 4.0), fat=0.3, dart=0.25),
    dict(title="Back down: first floor", rooms=FIRST_FLOOR, direction=-1, speed=1.4, per_room=5, pots=5, pot_hp=5, hatch=(2.0, 3.6), fat=0.35, dart=0.3, queen=True),
]


def build_stage(index):
    """Turn a stage description into a level: platforms, pots, gnat homes, pickups, exit."""
    st = STAGES[index]
    rng = random.Random(1000 + index)
    rooms, platforms, tops = [], [], []
    x0 = 0
    for name, width, wall, floor, things in st["rooms"]:
        rooms.append({"name": name, "x": x0, "w": width, "wall": wall, "floor": floor, "things": things})
        for th in things:
            kind, tx = th[0], x0 + th[1]
            if kind == "counter":
                platforms.append((tx, FLOOR - 36, th[2]))
                tops.append((tx + th[2] // 2, FLOOR - 36))
            elif kind == "shelf":
                platforms.append((tx, FLOOR - th[2], th[3]))
                tops.append((tx + th[3] // 2, FLOOR - th[2]))
            elif kind in FURN:
                fw, _, heights = FURN[kind]
                for hgt in heights:
                    inset = 6 if kind in ("sofa", "armchair") else 0
                    platforms.append((tx + inset, FLOOR - hgt, fw - 2 * inset))
                if heights and kind not in ("tv", "bed", "desk", "bench"):
                    tops.append((tx + fw // 2, FLOOR - heights[0]))
        x0 += width
    width = x0
    low = [t for t in tops if t[1] >= FLOOR - 50]
    high = [t for t in tops if t[1] < FLOOR - 50]
    rng.shuffle(low)
    rng.shuffle(high)
    edge = 150                                               # keep the start area calm
    start_x = 40 if st["direction"] > 0 else width - 40
    spots = [t for t in low + high[:2] if abs(t[0] - start_x) > edge]
    rng.shuffle(spots)
    pots = spots[:st["pots"]]
    while len(pots) < st["pots"]:                            # not enough furniture: use the floor
        pots.append((rng.randrange(200, width - 200), FLOOR))
    used = set(pots)
    perch = [t for t in high + low if t not in used]
    kinds = ["printer", "donut", "soda", "printer"]
    pickups = [(k, perch[i][0], perch[i][1]) for i, k in enumerate(kinds) if i < len(perch)]
    gnats = []
    for room in rooms:
        for _ in range(st["per_room"]):
            gx = rng.randrange(room["x"] + 30, room["x"] + room["w"] - 30)
            if abs(gx - start_x) > edge:
                gnats.append((gx, rng.randrange(70, 170)))
    door = width - 34 if st["direction"] > 0 else 34
    return {"name": st["title"], "width": width, "rooms": rooms, "platforms": platforms, "pots": pots,
            "gnats": gnats, "pickups": pickups, "door": door, "start": start_x, "stage": st}


def draw_rooms(surf, cam, level):
    for room in level["rooms"]:
        x = room["x"] - cam
        if x > W or x + room["w"] < 0:
            continue
        R(surf, room["wall"], x, 0, room["w"], FLOOR)
        R(surf, tuple(max(0, v - 22) for v in room["wall"]), x, 0, room["w"], 16)       # ceiling trim
        R(surf, tuple(max(0, v - 30) for v in room["wall"]), x, FLOOR - 6, room["w"], 6)  # skirting board
        R(surf, room["floor"], x, FLOOR, room["w"], H - FLOOR)
        dark = tuple(max(0, v - 24) for v in room["floor"])
        for bx in range(0, room["w"], 40):
            R(surf, dark, x + bx, FLOOR, 1, H - FLOOR)
        R(surf, dark, x, FLOOR, room["w"], 2)
        order = {"window": 0, "picture": 0, "rug": 1, "shelf": 2}
        for th in sorted(room["things"], key=lambda t: order.get(t[0], 3)):
            kind = th[0]
            tx = x + th[1]
            if tx > W + 10 or tx < -180:
                continue
            if kind == "counter" or kind == "rug":
                draw_furniture(surf, kind, tx, w=th[2])
            elif kind == "shelf":
                draw_furniture(surf, kind, tx, w=th[3], top=th[2])
            else:
                draw_furniture(surf, kind, tx)
    for room in level["rooms"][1:]:                          # doorways between rooms
        x = room["x"] - cam
        if -20 < x < W + 20:
            R(surf, (90, 70, 56), x - 5, 0, 10, FLOOR - 74)
            R(surf, (60, 46, 36), x - 5, FLOOR - 76, 10, 3)


def draw_stairs(surf, x, direction, open_):
    """The way to the next floor: a short flight of steps with a lit or dark sign."""
    col = (120, 92, 64)
    for i in range(6):
        sx = x - 26 + i * 8 if direction > 0 else x + 18 - i * 8
        R(surf, col, sx, FLOOR - 8 - i * 8, 8, 8 + i * 8)
        R(surf, (150, 118, 84), sx, FLOOR - 8 - i * 8, 8, 2)
    R(surf, (60, 200, 90) if open_ else (90, 70, 60), x - 12, FLOOR - 86, 24, 14)
    text(surf, "GO" if open_ else "--", (x, FLOOR - 85), 14, c.INK if open_ else (150, 130, 110), center=True, shadow=False)


class AngryPoppa(Game):
    name = "angry_poppa"
    title = "Angry Poppa"
    help_lines = ("Up: jump   Big button: swatter", "Triangle: spray   Down: pump", "Clear the pots, then take the stairs")
    title_color = (250, 210, 70)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.frames = {k: sprite(_TOP + legs, HERO_PAL, 2) for k, legs in _LEGS.items()}
        self.frames_l = {k: c.flip(v) for k, v in self.frames.items()}
        self.gnat_art = {"gnat": [sprite(g, ART_PAL, 2) for g in GNAT], "fat": [sprite(g, ART_PAL, 4) for g in GNAT],
                         "dart": [sprite(g, DART_PAL, 2) for g in GNAT]}
        self.art = {"pot": sprite(POT, ART_PAL, 2), "pot_dead": sprite(POT_DEAD, ART_PAL, 2),
                    "printer": sprite(PRINTER, ART_PAL, 2), "donut": sprite(DONUT, ART_PAL, 2),
                    "soda": sprite(SODA, ART_PAL, 2), "heart": sprite(HEART, ART_PAL, 2)}
        self.win = False
        self.level_index = 0
        self.reset()

    # ---------- setup ----------
    def reset(self):
        self.score = 0
        self.hearts = 4
        self.win = False
        self.up = {k: 0 for k in UPGRADES}
        self.level_index = 0
        self.load_level()

    def load_level(self):
        lv = self.level = build_stage(self.level_index)
        st = self.stage = lv["stage"]
        self.x, self.y = float(lv["start"]), float(FLOOR)
        self.vx = self.vy = 0.0
        self.face = st["direction"]
        self.on_ground = True
        self.swing = 0.0
        self.swing_cool = 0.0
        self.pump_anim = 0.0
        self.pressure = self.max_pressure
        self.invuln = 0.0
        self.boost = 0.0
        self.level_time = 0.0
        self.cleared = False
        self.banner = ("Stage %d: %s" % (self.level_index + 1, lv["name"]), 2.4)
        self.gnats = [self.new_gnat(x, y) for x, y in lv["gnats"]]
        self.pots = [{"x": x, "y": y, "hp": st["pot_hp"], "max": st["pot_hp"], "timer": self.rng.uniform(2, 5), "hit": 0.0}
                     for x, y in lv["pots"]]
        self.pickups = [{"kind": k, "x": float(x), "y": float(y), "vy": 0.0} for k, x, y in lv["pickups"]]
        self.puffs = []      # spray particles: x, y, vx, vy, ttl
        self.sparks = []     # x, y, ttl
        self.queen = None
        if st.get("queen"):
            qx = lv["door"] + 110 * (-st["direction"])
            self.queen = {"x": float(qx), "y": 110.0, "hx": float(qx), "hp": 40, "max": 40, "ph": 0.0, "spawn": 3.0, "hit": 0.0}
        self.cam = max(0.0, min(lv["width"] - W, self.x - 150))

    def new_gnat(self, x, y, kind=None):
        st = self.stage
        if kind is None:
            r = self.rng.random()
            kind = "fat" if r < st["fat"] else "dart" if r < st["fat"] + st["dart"] else "gnat"
        base = self.rng.uniform(34, 52) * st["speed"]
        return {"x": float(x), "y": float(y), "hx": float(x), "hy": float(y), "ph": self.rng.uniform(0, 6.28),
                "kind": kind, "hp": 3 if kind == "fat" else 1, "speed": base * (0.75 if kind == "fat" else 1.0),
                "dash": self.rng.uniform(1.5, 3.5), "dvx": 0.0, "dvy": 0.0, "dt": 0.0}

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

    def room_name(self):
        for room in self.level["rooms"]:
            if room["x"] <= self.x < room["x"] + room["w"]:
                return room["name"]
        return ""

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
        if self.state != "play":
            return
        self.update_queen(dt)
        if self.state != "play":
            return
        self.update_pots(dt)
        self.update_puffs(dt)
        self.update_pickups(dt)
        self.sparks = [[x, y, t - dt] for x, y, t in self.sparks if t > dt]
        self.cam = max(0.0, min(lv["width"] - W, self.x - 150))

        if not self.cleared and all(p["hp"] <= 0 for p in self.pots) and self.queen is None:
            self.cleared = True
            self.banner = ("All clear! Take the stairs", 2.5)
        if self.cleared and abs(self.x - lv["door"]) < 12:
            self.finish_level()

    def hurt_gnat(self, g, damage):
        g["hp"] -= damage
        if g["hp"] <= 0 and g in self.gnats:
            self.gnats.remove(g)
            self.score += {"gnat": 10, "dart": 20, "fat": 30}[g["kind"]]
            self.sparks.append([g["x"], g["y"], 0.25])
            if self.rng.random() < 0.06:
                self.pickups.append({"kind": self.rng.choice(("donut", "soda")), "x": g["x"], "y": g["y"], "vy": 0.0})

    def swat(self):
        rect = self.swat_rect()
        damage = 1 + self.up["power"]
        for g in list(self.gnats):
            if rect.collidepoint(g["x"], g["y"]):
                self.hurt_gnat(g, damage + 1)                 # two swats for a fat gnat, one once the swatter is upgraded
        for p in self.pots:
            if p["hp"] > 0 and rect.colliderect(pygame.Rect(p["x"] - 12, p["y"] - 24, 24, 24)):
                self.hurt_pot(p, damage)
        q = self.queen
        if q and rect.colliderect(pygame.Rect(int(q["x"]) - 22, int(q["y"]) - 16, 44, 32)):
            self.hurt_queen(2 * damage)

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

    def hurt_queen(self, damage):
        q = self.queen
        q["hp"] -= damage
        q["hit"] = 0.12
        if q["hp"] <= 0:
            self.score += 2000
            for k in range(8):
                self.sparks.append([q["x"] + math.cos(k) * 16, q["y"] + math.sin(k) * 12, 0.6])
            self.queen = None
            self.banner = ("The queen is down!", 2.5)

    def lose_heart(self):
        self.hearts -= 1
        self.invuln = 1.3
        self.score = max(0, self.score - 10)
        if self.hearts <= 0:
            self.game_over()

    def update_gnats(self, dt):
        hero = self.hero_rect()
        hx, hy = self.x, self.y - 36
        for g in list(self.gnats):
            g["ph"] += dt * 7
            dx, dy = hx - g["x"], hy - g["y"]
            dist = math.hypot(dx, dy) or 1.0
            if g["dt"] > 0:                                   # a dart gnat mid-dash
                g["dt"] -= dt
                g["x"] += g["dvx"] * dt
                g["y"] += g["dvy"] * dt
            elif dist < 230:
                g["x"] += dx / dist * g["speed"] * dt
                g["y"] += dy / dist * g["speed"] * dt
                if g["kind"] == "dart":
                    g["dash"] -= dt
                    if g["dash"] <= 0 and dist < 150:
                        g["dvx"], g["dvy"] = dx / dist * 210, dy / dist * 210
                        g["dt"], g["dash"] = 0.45, self.rng.uniform(1.8, 3.2)
            else:
                g["x"] += (g["hx"] - g["x"]) * dt
                g["y"] += (g["hy"] - g["y"]) * dt
            g["x"] += math.cos(g["ph"]) * 26 * dt
            g["y"] = min(FLOOR - 4.0, g["y"] + math.sin(g["ph"] * 1.3) * 26 * dt)
            if self.invuln <= 0 and hero.collidepoint(g["x"], g["y"]):
                self.hurt_gnat(g, 1)
                self.lose_heart()
                if self.state != "play":
                    return

    def update_queen(self, dt):
        q = self.queen
        if not q:
            return
        q["ph"] += dt
        q["hit"] = max(0.0, q["hit"] - dt)
        q["x"] = q["hx"] + math.sin(q["ph"] * 0.9) * 70
        q["y"] = 104 + math.sin(q["ph"] * 1.7) * 44
        if abs(q["x"] - self.x) < 300:
            q["spawn"] -= dt
            if q["spawn"] <= 0 and len(self.gnats) < MAX_GNATS:
                for _ in range(2):
                    self.gnats.append(self.new_gnat(q["x"], q["y"] + 10))
                q["spawn"] = 2.6
        if self.invuln <= 0 and self.hero_rect().colliderect(pygame.Rect(int(q["x"]) - 18, int(q["y"]) - 12, 36, 26)):
            self.lose_heart()

    def update_pots(self, dt):
        lo, hi = self.stage["hatch"]
        for p in self.pots:
            p["hit"] = max(0.0, p["hit"] - dt)
            if p["hp"] <= 0:
                continue
            p["timer"] -= dt
            if p["timer"] <= 0 and abs(p["x"] - self.x) < 260 and len(self.gnats) < MAX_GNATS:
                self.gnats.append(self.new_gnat(p["x"], p["y"] - 26))
                p["timer"] = self.rng.uniform(lo, hi)

    def update_puffs(self, dt):
        for f in self.puffs:
            f[0] += f[2] * dt
            f[1] += f[3] * dt
            f[2] *= 0.5 ** (dt / 0.34)
            f[3] *= 0.5 ** (dt / 0.34)
            f[4] -= dt
            for g in list(self.gnats):
                if f[4] > 0 and abs(g["x"] - f[0]) < 8 and abs(g["y"] - f[1]) < 8:
                    self.hurt_gnat(g, 1)
                    if g["kind"] == "fat":
                        f[4] = 0                              # a fat gnat soaks up the puff
            for p in self.pots:
                if p["hp"] > 0 and abs(p["x"] - f[0]) < 10 and -24 < f[1] - p["y"] < 0 and f[4] > 0:
                    self.hurt_pot(p, 1)
                    f[4] = 0
            q = self.queen
            if q and f[4] > 0 and abs(q["x"] - f[0]) < 22 and abs(q["y"] - f[1]) < 16:
                self.hurt_queen(1)
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
        self.score += 500 + max(0, 400 - int(self.level_time) * 2) + self.hearts * 50
        if self.level_index + 1 < len(STAGES):
            self.level_index += 1
            self.hearts = min(6, self.hearts + 1)
            self.load_level()
        else:
            self.win = True
            self.game_over()

    # ---------- drawing ----------
    def draw(self, surf):
        lv = self.level
        cam = int(self.cam)
        draw_rooms(surf, cam, lv)
        dx = lv["door"] - cam
        if -60 < dx < W + 60:
            draw_stairs(surf, dx, self.stage["direction"], self.cleared)
        for p in self.pots:
            x, y = p["x"] - cam - 12, p["y"] - 24
            if -30 < x < W:
                surf.blit(self.art["pot" if p["hp"] > 0 else "pot_dead"], (x, y))
                if p["hit"] > 0:
                    pygame.draw.rect(surf, c.WHITE, (x, y, 24, 24), 1)
                for i in range(max(0, p["hp"])):
                    R(surf, (220, 60, 70), x + 12 - p["max"] * 3 + i * 6, y - 5, 4, 3)
        for pk in self.pickups:
            img = self.art[pk["kind"]]
            bob = int(math.sin(self.time * 5 + pk["x"]) * 2)
            surf.blit(img, (int(pk["x"]) - cam - img.get_width() // 2, int(pk["y"]) - img.get_height() + bob))
        for g in self.gnats:
            x = int(g["x"]) - cam
            if -16 < x < W + 16:
                img = self.gnat_art[g["kind"]][int(g["ph"]) % 2]
                surf.blit(img, (x - img.get_width() // 2, int(g["y"]) - img.get_height() // 2))
        if self.queen:
            self.draw_queen(surf, cam)
        for f in self.puffs:
            pygame.draw.circle(surf, (200, 240, 230), (int(f[0]) - cam, int(f[1])), 2 + int((0.6 - f[4]) * 6), 1)
        for x, y, t in self.sparks:
            for k in range(4):
                a = k * 1.57 + t * 20
                pygame.draw.line(surf, (255, 240, 120), (int(x) - cam, int(y)),
                                 (int(x + math.cos(a) * 7) - cam, int(y + math.sin(a) * 7)))
        self.draw_hero(surf, cam)
        self.draw_hud(surf)

    def draw_queen(self, surf, cam):
        q = self.queen
        x, y = int(q["x"]) - cam, int(q["y"])
        flap = int(q["ph"] * 14) % 2
        wing = (236, 240, 248) if q["hit"] <= 0 else (255, 120, 120)
        pygame.draw.ellipse(surf, wing, (x - 34, y - 22 - flap * 6, 30, 18 + flap * 6))
        pygame.draw.ellipse(surf, wing, (x + 4, y - 22 - flap * 6, 30, 18 + flap * 6))
        pygame.draw.ellipse(surf, (20, 20, 26), (x - 20, y - 10, 40, 24))
        pygame.draw.ellipse(surf, (60, 40, 70), (x - 12, y - 4, 26, 14))
        pygame.draw.circle(surf, (20, 20, 26), (x - 20, y - 2), 9)
        pygame.draw.circle(surf, (230, 40, 50), (x - 24, y - 4), 3)
        pygame.draw.polygon(surf, (250, 210, 70), [(x - 27, y - 10), (x - 25, y - 18), (x - 21, y - 12), (x - 18, y - 19), (x - 15, y - 11)])
        for lx in (-8, 2, 12):
            pygame.draw.line(surf, (20, 20, 26), (x + lx, y + 12), (x + lx - 3, y + 20))

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
        R(surf, (210, 60, 60), can[0] - 4, can[1] - 4, 8, 14)
        R(surf, (230, 230, 236), can[0] - 2, can[1] - 8, 5, 4)

    def draw_hud(self, surf):
        for i in range(self.hearts):
            surf.blit(self.art["heart"], (6 + i * 16, 5))
        text(surf, "Spray", (6, 22), 16)
        for i in range(self.max_pressure):
            R(surf, c.INK, 40 + i * 8, 23, 7, 9)
            R(surf, (120, 230, 210) if i < self.pressure else (70, 80, 90), 41 + i * 8, 24, 5, 7)
        text(surf, "Score %d" % self.score, (W - 96, 5), 20)
        left = sum(1 for p in self.pots if p["hp"] > 0)
        text(surf, "Pots %d" % left, (W - 96, 22), 16, c.YELLOW if left else (120, 230, 140))
        text(surf, self.room_name(), (W // 2, 22), 16, c.WHITE, center=True)
        if self.boost > 0:
            text(surf, "BOOST", (W // 2, 5), 18, (120, 240, 140), center=True)
        if self.queen:
            q = self.queen
            R(surf, c.INK, W // 2 - 61, H - 14, 122, 8)
            R(surf, (200, 50, 70), W // 2 - 60, H - 13, int(120 * q["hp"] / q["max"]), 6)
            text(surf, "QUEEN", (W // 2, H - 28), 16, (250, 210, 70), center=True)
        if self.banner:
            text(surf, self.banner[0], (W // 2, 44), 22, c.YELLOW, center=True)

    def render(self, surf):
        super().render(surf)
        if self.state == "over" and self.win:
            R(surf, c.BLACK, 60, 52, W - 120, 44)
            text(surf, "HOUSE CLEAR!", (W // 2, 60), 44, (120, 240, 140), center=True)


def make(**kw):
    return AngryPoppa(**kw)
