"""Art for Black Warrior: Victor, the Tower Row thugs, the Trillion Heir, Mazee, the stages and cutscene pieces.

Characters are assembled from painted parts (head, torso, limbs posed by joint
angles) with a lit edge, a blue rim light and a dark colored outline, then
cached. Everything here is drawn in code and original to this project.

Victor's close-up portraits are personal, so they are not in this repository:
the game loads them from a private folder on BMO (see PRIVATE_DIR) and falls
back to a masked portrait drawn here when they are missing.
"""
import math
import os
import random

import pygame

from . import pixart as px

W, H = 400, 240
OUT = (10, 8, 14)
PRIVATE_DIR = os.environ.get("BW_PRIVATE_DIR", os.path.expanduser("~/.local/share/bmo-games/private"))

SKIN = [(44, 25, 20), (68, 39, 28), (94, 57, 38), (122, 77, 52), (150, 99, 68), (180, 124, 88)]
SUIT = [(11, 13, 20), (22, 26, 38), (35, 42, 61), (58, 69, 96)]
BLUE = [(14, 59, 140), (31, 111, 224), (79, 180, 255), (184, 236, 255)]
GOLD = [(120, 80, 20), (190, 140, 40), (240, 200, 80), (255, 240, 170)]

_cache = {}
_fonts = {}


def font(size):
    f = _fonts.get(size)
    if f is None:
        f = _fonts[size] = pygame.font.Font(None, size)
    return f


def say(surf, msg, pos, size=18, col=(255, 255, 255), center=True, outline=OUT):
    px.outlined_text(surf, font(size), msg, pos, col, outline=outline, center=center)


# ------------------------------------------------------------------ drawing kit
class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = {}

    def put(self, x, y, k):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[(x, y)] = k

    def stamp(self, rows, ox, oy):
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch not in ". ":
                    self.put(ox + x, oy + y, ch)

    def disc(self, x, y, r, k):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r + r:
                    self.put(x + dx, y + dy, k)

    def limb(self, a, b, r, k, hi=None, rim=None):
        (x0, y0), (x1, y1) = a, b
        n = max(1, int(math.hypot(x1 - x0, y1 - y0)))
        for i in range(n + 1):
            t = i / n
            self.disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r, k)
        for i in range(n + 1):
            t = i / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if hi:
                self.put(x - r + 1, y - 1, hi)
            if rim:
                self.put(x + r, y, rim)

    def surface(self, pal):
        s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        for (x, y), k in self.px.items():
            if k in pal:
                s.set_at((x, y), pal[k])
        return s


def outlined(s, col=OUT):
    w, h = s.get_size()
    out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
    sil = pygame.mask.from_surface(s).to_surface(setcolor=col + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(sil, (dx, dy))
    out.blit(s, (1, 1))
    return out


def white(surf):
    key = ("white", id(surf))
    s = _cache.get(key)
    if s is None:
        s = _cache[key] = pygame.mask.from_surface(surf).to_surface(setcolor=(255, 255, 255, 255),
                                                                    unsetcolor=(0, 0, 0, 0))
    return s


# ------------------------------------------------------------------ fighters
VIC_PAL = {
    "h": (20, 15, 20), "H": (46, 40, 54),
    "s": SKIN[3], "S": SKIN[1], "L": SKIN[4], "l": SKIN[5], "d": SKIN[0],
    "w": (226, 214, 200), "k": (16, 10, 10), "m": (70, 30, 28),
    "a": SUIT[0], "A": SUIT[1], "c": SUIT[2], "C": SUIT[3],
    "b": BLUE[0], "B": BLUE[1], "g": BLUE[2], "G": BLUE[3],
}
HEAD_FACE = [
    "....hhhhhhh....",
    "..hhhhhhhhhhh..",
    ".hhhhhhhhHHhhh.",
    ".hhhhhhhhhhHhh.",
    ".hhhLlllllhhh..",
    ".hhLllllkklhh..",
    ".hsLLsLlwkkLs..",
    "SsssLssslllssS.",
    "SsssLsssslsssss",
    ".SssssssssLsss.",
    ".SssssssmmmLs..",
    "..Sssssssmss...",
    "...SSsssssS....",
    ".....SSSSS.....",
]
HEAD_MASK = [
    "..a........a...",
    ".aaa......aaa..",
    ".abaaaaaaaaba..",
    ".aaaaaaCaaaaa..",
    ".aaaaaaacCaaa..",
    ".aaaaaaaaaaaa..",
    ".aaaaaaaggGgaa.",
    "AaaaaaaaaaaaaaC",
    "AaaaaaBaaaaaaaC",
    ".AaaaaaBaaaaaC.",
    ".AaaaaaacccaC..",
    "..Aaaaaaaaaa...",
    "...AAaaaaaA....",
    ".....AAAAA.....",
]
TORSO = [
    "....AAAAAAAAg.....",
    "..AcCCCaaaaCCCcg..",
    ".AcCCcaaaaaacCCcg.",
    ".AacaGaaaaaaGacaB.",
    ".AaaaaBaaaaBaaaacB",
    ".AacaaaaggaaaaacB.",
    "..AcaaaagGaaaacaB.",
    "..AaccaaaaaaccaB..",
    "...AacaaaaaacaB...",
    "...AaaccaaccaaB...",
    "...AcccbbbbcccB...",
    "...AAaaaaaaaaaA...",
]
GOON_PALS = {
    "valet": {"a": (110, 24, 40), "A": (70, 14, 26), "c": (160, 50, 64), "C": (200, 170, 90),
              "b": (110, 24, 40), "B": GOLD[2], "g": GOLD[2], "G": GOLD[3],
              "s": (226, 176, 140), "S": (180, 130, 100), "L": (240, 196, 160), "l": (250, 214, 180),
              "h": (120, 70, 40), "H": (160, 100, 60)},
    "security": {"a": (70, 74, 86), "A": (44, 46, 56), "c": (110, 114, 128), "C": (150, 154, 168),
                 "b": (70, 74, 86), "B": (230, 230, 236), "g": (200, 40, 50), "G": (240, 240, 240),
                 "s": (200, 150, 116), "S": (150, 104, 80), "L": (220, 172, 136), "l": (236, 190, 156),
                 "h": (30, 26, 26), "H": (60, 54, 54)},
}
CITIZEN_PALS = [
    {"a": (60, 120, 170), "A": (40, 84, 120), "c": (90, 150, 200), "C": (140, 190, 230), "b": (60, 120, 170),
     "B": (250, 250, 250), "g": (250, 200, 80), "G": (255, 240, 170)},
    {"a": (170, 90, 60), "A": (120, 60, 40), "c": (210, 130, 90), "C": (240, 180, 130), "b": (170, 90, 60),
     "B": (250, 250, 250), "g": (90, 200, 120), "G": (200, 255, 210),
     "s": (150, 99, 68), "S": (94, 57, 38), "L": (180, 124, 88), "l": (206, 150, 110)},
    {"a": (90, 150, 90), "A": (60, 104, 60), "c": (130, 190, 120), "C": (180, 230, 160), "b": (90, 150, 90),
     "B": (250, 250, 250), "g": (250, 120, 150), "G": (255, 200, 220),
     "s": (236, 190, 150), "S": (190, 140, 104), "L": (246, 208, 172), "l": (252, 222, 190), "h": (150, 90, 50)},
]

# far arm (upper, lower), near arm, far leg (thigh, shin), near leg, head bob, lean, drop
POSES = {
    "idle0": ((40, 150), (60, 160), (-14, -4), (14, 4), 0, 0, 0),
    "idle1": ((40, 150), (58, 162), (-14, -4), (14, 4), 1, 0, 1),
    "walk0": ((30, 150), (50, 160), (-24, -10), (26, 8), 0, 0, 0),
    "walk1": ((36, 150), (56, 160), (-4, -40), (8, 0), -1, 0, -1),
    "walk2": ((50, 150), (40, 160), (26, 8), (-24, -10), 0, 0, 0),
    "walk3": ((44, 150), (48, 160), (8, 0), (-4, -40), -1, 0, -1),
    "jab": ((40, 150), (90, 90), (-16, -4), (18, 6), 0, 2, 0),
    "cross": ((90, 90), (30, 150), (-20, -4), (22, 10), 0, 3, 0),
    "upper": ((40, 150), (120, 172), (-20, -6), (20, 6), -1, 2, -1),
    "kick": ((10, 140), (-20, 120), (-6, 0), (84, 92), 0, -3, 0),
    "round": ((-20, 100), (30, 140), (-4, 0), (104, 122), 0, -5, 0),
    "spin": ((70, 100), (-50, 60), (6, 0), (116, 104), -1, -6, 0),
    "tuck": ((60, 150), (70, 160), (40, -80), (60, -60), 0, 2, 0),
    "jumpk": ((-40, 120), (-20, 150), (-30, -90), (86, 90), 0, -2, 0),
    "elbow": ((-40, 150), (36, 172), (-40, -70), (30, -80), 1, 5, 0),
    "backel": ((60, 150), (-76, 50), (-18, -4), (16, 4), 0, -2, 0),
    "grab": ((76, 104), (80, 100), (-14, -4), (16, 6), 0, 2, 0),
    "knee": ((76, 110), (80, 104), (-10, -2), (100, 6), -1, 2, -2),
    "throw": ((150, 170), (154, 176), (-22, -6), (24, 8), -1, -3, -1),
    "dodge": ((-60, 40), (70, 120), (16, -84), (82, 88), 0, 6, 8),
    "swing": ((-10, 140), (106, 116), (-18, -4), (22, 8), 0, 3, 0),
    "hit": ((-30, 20), (-20, 30), (-10, -4), (20, 4), 2, -4, 0),
    "getup": ((20, 120), (60, 100), (4, -90), (86, 0), 1, 3, 9),
    "draw": ((40, 150), (-60, -100), (-22, -6), (22, 8), 0, -2, 0),
    "strike": ((-30, 130), (96, 100), (-30, -10), (40, 20), 0, 4, 2),
    "victory": ((40, 150), (170, 180), (-14, -4), (14, 4), -1, 0, 0),
    "mask1": ((40, 150), (140, 200), (-14, -4), (14, 4), 0, 0, 0),
    "mask2": ((40, 150), (170, 160), (-14, -4), (14, 4), -1, 0, 0),
}


def _arm(cv, sh, a_up, a_low, far, sleeve_lines):
    k, hi, rim = ("A", "a", None) if far else ("a", "C", "g")
    a1, a2 = math.radians(a_up), math.radians(a_low)
    el = (sh[0] + 8 * math.sin(a1), sh[1] + 8 * math.cos(a1))
    hand = (el[0] + 8 * math.sin(a2), el[1] + 8 * math.cos(a2))
    cv.limb(sh, el, 2, k, hi, rim)
    cv.limb(el, hand, 2, k, hi, rim)
    if sleeve_lines and not far:
        for t in (0.3, 0.5, 0.7):
            cv.put(el[0] + (hand[0] - el[0]) * t, el[1] + (hand[1] - el[1]) * t, "B")
    cv.disc(hand[0], hand[1], 2, "A" if far else "a")
    cv.put(hand[0], hand[1] - 1, "c" if far else "C")
    return hand


def _leg(cv, hip, a1, a2, far):
    k, hi, rim = ("A", "a", None) if far else ("a", "c", "B")
    r1, r2 = math.radians(a1), math.radians(a2)
    knee = (hip[0] + 11 * math.sin(r1), hip[1] + 11 * math.cos(r1))
    foot = (knee[0] + 11 * math.sin(r2), knee[1] + 11 * math.cos(r2))
    cv.limb(hip, knee, 3, k, hi, rim)
    cv.limb(knee, foot, 2, k, hi, rim)
    cv.disc(knee[0], knee[1], 2, "A" if far else "c")
    toe = 1 if a2 > -60 else -1
    for dx in range(-2, 5):
        cv.put(foot[0] + dx * toe, foot[1] + 1, "A")
        cv.put(foot[0] + dx * toe, foot[1], "a")


FEET_Y = 52      # where the feet sit inside a figure surface (before the outline)
HX = 26          # body center inside a figure surface


def _figure(pal, head, pose, extra=None, sleeve_lines=True):
    far_arm, near_arm, far_leg, near_leg, bob, lean, drop = POSES[pose]
    cv = Canvas(64, 64)
    hip = 29 + drop
    _leg(cv, (HX - 3, hip), *far_leg, far=True)
    _arm(cv, (HX - 3 + lean, 22 + drop), *far_arm, far=True, sleeve_lines=sleeve_lines)
    cv.stamp(TORSO, HX - 9 + lean, 18 + drop)
    _leg(cv, (HX + 2, hip), *near_leg, far=False)
    cv.stamp(head, HX - 6 + lean, 5 + bob + drop)
    if extra:
        extra(cv, lean, bob + drop)
    _arm(cv, (HX + 6 + lean, 22 + drop), *near_arm, far=False, sleeve_lines=sleeve_lines)
    return outlined(cv.surface(pal))


def _place(s, face):
    if face < 0:
        s = pygame.transform.flip(s, True, False)
    return s


def victor(pose="idle0", masked=True, face=1):
    key = ("vic", pose, masked, face)
    if key not in _cache:
        s = _figure(VIC_PAL, HEAD_MASK if masked else HEAD_FACE, pose)
        _cache[key] = _place(s, face)
    return _cache[key]


def goon(kind, pose="idle0", face=-1):
    key = ("goon", kind, pose, face)
    if key not in _cache:
        pal = dict(VIC_PAL)
        pal.update(GOON_PALS[kind])
        shades = (lambda cv, lean, dy: cv.stamp(["kkkkk"], HX + 2 + lean, 10 + dy)) if kind == "security" else None
        if kind == "security":
            pal["w"] = pal["k"] = (20, 20, 24)
        _cache[key] = _place(_figure(pal, HEAD_FACE, pose, shades, sleeve_lines=False), face)
    return _cache[key]


def citizen(i, pose="walk0", face=1):
    key = ("cit", i, pose, face)
    if key not in _cache:
        pal = dict(VIC_PAL)
        pal.update(CITIZEN_PALS[i % len(CITIZEN_PALS)])
        _cache[key] = _place(_figure(pal, HEAD_FACE, pose, sleeve_lines=False), face)
    return _cache[key]


def lying(surf):
    key = ("lie", id(surf))
    if key not in _cache:
        _cache[key] = pygame.transform.rotate(surf, 90)
    return _cache[key]


def butler(frame=0, face=-1, throwing=False):
    """A chrome butler robot on one wheel: dome head, red eye, bow tie, white gloves, silver tray."""
    key = ("butler", frame % 2, face, throwing)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((34, 48), pygame.SRCALPHA)
    pygame.draw.circle(s, (40, 40, 48), (16, 42), 5)
    pygame.draw.circle(s, (150, 154, 166), (16, 42), 3)
    a = frame % 2 * math.pi / 4
    for k in range(2):
        pygame.draw.line(s, (60, 60, 70), (16, 42), (16 + math.cos(a + k * math.pi / 2) * 3, 42 + math.sin(a + k * math.pi / 2) * 3))
    pygame.draw.rect(s, (70, 72, 84), (14, 32, 4, 8))
    pygame.draw.ellipse(s, (150, 156, 170), (6, 16, 22, 20))
    pygame.draw.ellipse(s, (200, 206, 220), (9, 18, 10, 8))
    pygame.draw.rect(s, (24, 24, 30), (8, 22, 18, 12), border_radius=4)           # tailcoat
    pygame.draw.polygon(s, (240, 240, 244), [(15, 22), (19, 22), (17, 30)])
    pygame.draw.polygon(s, (24, 24, 30), [(13, 20), (17, 22), (13, 24)])          # bow tie
    pygame.draw.polygon(s, (24, 24, 30), [(21, 20), (17, 22), (21, 24)])
    pygame.draw.circle(s, (170, 176, 190), (17, 10), 8)
    pygame.draw.circle(s, (220, 226, 236), (14, 7), 3)
    pygame.draw.rect(s, (30, 30, 36), (16, 8, 9, 4), border_radius=2)
    pygame.draw.circle(s, (240, 50, 50), (22, 10), 2)
    if throwing:
        pygame.draw.line(s, (150, 156, 170), (24, 24), (31, 16), 2)
        pygame.draw.circle(s, (250, 250, 250), (31, 15), 2)
    else:
        pygame.draw.line(s, (150, 156, 170), (24, 24), (30, 26), 2)
        pygame.draw.circle(s, (250, 250, 250), (30, 26), 2)
        pygame.draw.ellipse(s, (210, 214, 226), (24, 22, 10, 3))                  # tray
    pygame.draw.line(s, (150, 156, 170), (9, 24), (5, 30), 2)
    pygame.draw.circle(s, (250, 250, 250), (5, 30), 2)
    s = outlined(s)
    if face < 0:
        s = pygame.transform.flip(s, True, False)
    _cache[key] = s
    return s


def tray():
    if "tray" not in _cache:
        s = pygame.Surface((10, 4), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (210, 214, 226), (0, 0, 10, 4))
        pygame.draw.line(s, (250, 250, 255), (2, 1), (6, 1))
        _cache["tray"] = outlined(s)
    return _cache["tray"]


def coin():
    if "coin" not in _cache:
        s = pygame.Surface((7, 7), pygame.SRCALPHA)
        pygame.draw.circle(s, GOLD[1], (3, 3), 3)
        pygame.draw.circle(s, GOLD[2], (3, 3), 2)
        s.set_at((2, 2), GOLD[3])
        _cache["coin"] = outlined(s)
    return _cache["coin"]


def mazee(frame=0, face=1, snarl=False):
    """Mazee for this game: bigger and fiercer, grey patches, spiked blue collar, eyes flashing blue."""
    key = ("mazee", frame % 2, face, snarl)
    if key in _cache:
        return _cache[key]
    rows = [
        "...........................ww.ww...",
        "..........................wwwwwww..",
        "..ww.....................wwggwwwww.",
        ".wwww...................wwwwwwwgEw.",
        ".wwwgw.................wwwwwwwwwwKK",
        "..wwgww..wwwwwwwwwwwwwwwwwwwwwwwnTT",
        "...wwwwwwwwwwggggwwwwwwwwwwbBbBwTT.",
        "....wwwwwwwgggggggwwwwwwwwwbBbBww..",
        ".....wwwwwwwggggggwwwwwwwwwwwwww...",
        ".....GwwwwwwwwwwwwwwwwwwwwwwGww....",
        "......GwwwwwwwwwwwwwwwwwwwwwGw.....",
    ]
    legs = [["......wwG.ww.........ww..wwG.......",
             ".....ww..ww...........ww..ww.......",
             "....ww...ww............ww..ww......",
             "...KK....KK.............KK..KK....."],
            ["......wwG..ww.......ww...wwG.......",
             ".......ww...ww.....ww...ww.........",
             "........ww...ww...ww...ww..........",
             ".........KK...KK.KK...KK..........."]]
    pal = {"w": (246, 246, 242), "g": (150, 150, 160), "G": (200, 200, 208), "K": (30, 30, 36),
           "E": BLUE[2] if snarl else (40, 30, 30), "n": (40, 30, 30), "T": (250, 250, 250),
           "b": BLUE[1], "B": (220, 224, 236)}
    cv = Canvas(36, 16)
    cv.stamp(rows + legs[frame % 2], 0, 0)
    s = outlined(pygame.transform.scale(cv.surface(pal), (54, 24)))
    if face < 0:
        s = pygame.transform.flip(s, True, False)
    _cache[key] = s
    return s


def trillion_heir(t=0.0, low=False, hat=False):
    """The Trillion Heir on his gold hover-throne: smoking jacket, ascot, monocle, smug grin."""
    s = pygame.Surface((76, 86), pygame.SRCALPHA)
    pygame.draw.rect(s, GOLD[1], (8, 6, 56, 54), border_radius=10)
    pygame.draw.rect(s, GOLD[2], (12, 10, 48, 6), border_radius=3)
    pygame.draw.rect(s, (120, 20, 40), (16, 18, 40, 38), border_radius=6)
    for x in range(20, 54, 6):
        pygame.draw.circle(s, (90, 10, 30), (x, 30), 1)
        pygame.draw.circle(s, (90, 10, 30), (x + 3, 42), 1)
    pygame.draw.circle(s, GOLD[3], (36, 4), 4)
    pygame.draw.rect(s, GOLD[1], (4, 56, 64, 10), border_radius=4)
    pygame.draw.rect(s, GOLD[2], (6, 56, 60, 3))
    if not low:
        for i, x in enumerate((14, 36, 58)):
            h = 6 + int(abs(math.sin(t * 20 + i)) * 6)
            pygame.draw.polygon(s, BLUE[2], [(x - 3, 66), (x + 3, 66), (x, 66 + h)])
            pygame.draw.line(s, BLUE[3], (x, 66), (x, 66 + h // 2))
    else:
        for i, x in enumerate((14, 36, 58)):
            if int(t * 12 + i) % 3 == 0:
                pygame.draw.circle(s, (120, 120, 130), (x, 70), 3)
    pygame.draw.rect(s, (90, 20, 60), (24, 30, 26, 22), border_radius=4)
    pygame.draw.rect(s, (130, 40, 90), (24, 30, 6, 22))
    pygame.draw.polygon(s, (230, 230, 236), [(33, 30), (41, 30), (37, 38)])
    pygame.draw.polygon(s, GOLD[2], [(35, 32), (39, 32), (37, 37)])
    pygame.draw.rect(s, (40, 30, 40), (26, 50, 24, 6))
    pygame.draw.line(s, (40, 30, 40), (48, 54), (60, 60), 5)
    pygame.draw.rect(s, (20, 14, 14), (58, 58, 8, 4))
    pygame.draw.circle(s, (240, 210, 180), (37, 22), 8)
    if hat:     # his first job
        pygame.draw.polygon(s, (250, 250, 250), [(28, 16), (46, 16), (44, 8), (30, 8)])
        pygame.draw.rect(s, (220, 50, 50), (29, 13, 16, 2))
    else:
        pygame.draw.ellipse(s, (240, 200, 90), (28, 12, 18, 8))
        pygame.draw.line(s, (240, 200, 90), (29, 16), (31, 22), 2)
    pygame.draw.circle(s, (30, 20, 20), (40, 22), 1)
    pygame.draw.circle(s, GOLD[3], (40, 22), 3, 1)
    pygame.draw.line(s, GOLD[2], (43, 23), (44, 30))
    if hat:
        pygame.draw.arc(s, (120, 40, 40), (33, 25, 10, 6), math.pi * 0.1, math.pi * 0.9, 1)
    else:
        pygame.draw.arc(s, (120, 40, 40), (33, 23, 10, 6), math.pi * 1.1, math.pi * 1.9, 1)
    pygame.draw.line(s, (240, 210, 180), (50, 38), (60, 34), 3)
    pygame.draw.circle(s, GOLD[2], (62, 32), 4)
    pygame.draw.circle(s, GOLD[3], (61, 31), 1)
    return outlined(s)


def weapon_img(kind, angle=0):
    key = ("weapon", kind, int(angle) // 45)
    if key not in _cache:
        s = pygame.Surface((24, 6), pygame.SRCALPHA)
        if kind == "bat":
            pygame.draw.polygon(s, (170, 120, 70), [(0, 2), (6, 2), (23, 0), (23, 5), (6, 4), (0, 4)])
            pygame.draw.line(s, (210, 160, 100), (6, 2), (22, 1))
            pygame.draw.rect(s, (40, 30, 30), (0, 2, 4, 2))
        else:
            pygame.draw.rect(s, (130, 134, 146), (0, 2, 22, 3))
            pygame.draw.line(s, (200, 204, 214), (0, 2), (21, 2))
            pygame.draw.rect(s, (90, 94, 104), (20, 1, 3, 5))
        s = outlined(s)
        _cache[key] = pygame.transform.rotate(s, -(int(angle) // 45) * 45)
    return _cache[key]


def token(t):
    """The glowing Tag Token: Mazee's face on a blue badge."""
    s = pygame.Surface((22, 22), pygame.SRCALPHA)
    r = 9 + int(abs(math.sin(t * 4)) * 2)
    pygame.draw.circle(s, BLUE[1] + (90,), (11, 11), r + 1)
    pygame.draw.circle(s, BLUE[2], (11, 11), 8)
    pygame.draw.circle(s, BLUE[3], (11, 11), 8, 1)
    head = pygame.transform.scale(mazee(0), (27, 12)).subsurface((14, 0, 13, 10))
    s.blit(head, (5, 6))
    return outlined(s)


def stars(surf, x, y, t):
    for k in range(3):
        a = t * 6 + k * 2.1
        surf.fill((255, 230, 120), (int(x + math.cos(a) * 8), int(y + math.sin(a) * 3), 2, 2))


def spark(surf, x, y, big=False):
    r = 6 if big else 4
    pygame.draw.circle(surf, (255, 250, 220), (int(x), int(y)), r)
    pygame.draw.circle(surf, BLUE[3], (int(x), int(y)), r - 2)
    for a in range(0, 360, 60):
        dx, dy = math.cos(math.radians(a)) * (r + 3), math.sin(math.radians(a)) * (r + 3)
        surf.set_at((int(x + dx), int(y + dy)), (255, 255, 255))


def shadow(surf, x, y, w=26):
    key = ("shadow", w)
    sh = _cache.get(key)
    if sh is None:
        sh = _cache[key] = pygame.Surface((w, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 110), (0, 0, w, 6))
    surf.blit(sh, (int(x - w // 2), int(y - 3)))


def bubble(surf, msg, x, y):
    img = font(15).render(msg, False, (20, 20, 30))
    r = pygame.Rect(0, 0, img.get_width() + 10, img.get_height() + 6)
    r.midbottom = (int(x), int(y))
    r.clamp_ip(pygame.Rect(2, 2, W - 4, H - 4))
    pygame.draw.rect(surf, OUT, r.inflate(2, 2), border_radius=5)
    pygame.draw.rect(surf, (250, 250, 246), r, border_radius=5)
    pygame.draw.polygon(surf, (250, 250, 246), [(r.centerx - 4, r.bottom - 1), (r.centerx + 4, r.bottom - 1),
                                                (r.centerx, r.bottom + 5)])
    surf.blit(img, (r.x + 5, r.y + 3))


# ------------------------------------------------------------------ portraits
def _fallback_portrait(masked=True):
    """A masked portrait drawn here, used when the private portraits are not on this device."""
    s = pygame.Surface((96, 96))
    for y in range(96):
        t = y / 95
        s.fill((int(20 + 26 * t), int(15 + 12 * t), int(40 + 34 * t)), (0, y, 96, 1))
    cowl = [(22, 6), (28, -2), (48, -6), (68, -2), (74, 6), (80, 20), (82, 36), (80, 50), (74, 62), (64, 76),
            (56, 81), (40, 81), (32, 76), (22, 62), (16, 50), (14, 36), (16, 20)]
    pygame.draw.polygon(s, SUIT[0], cowl)
    for sgn, ex in ((-1, 26), (1, 70)):
        pygame.draw.polygon(s, SUIT[0], [(ex - 8 * sgn, 14), (ex + sgn, 2), (ex + 9 * sgn, 8)])
        pygame.draw.polygon(s, BLUE[0], [(ex - 3 * sgn, 10), (ex + sgn, 5), (ex + 5 * sgn, 9)])
    pygame.draw.lines(s, SUIT[3], False, [(74, 6), (80, 20), (82, 36), (80, 50), (74, 62)])
    for sgn, cx in ((-1, 38), (1, 58)):
        pygame.draw.polygon(s, BLUE[2], [(cx - 6 * sgn, 40), (cx + 7 * sgn, 35), (cx + 6 * sgn, 40), (cx - 4 * sgn, 43)])
        pygame.draw.line(s, BLUE[3], (cx - 3 * sgn, 39), (cx + 4 * sgn, 37))
    pygame.draw.line(s, BLUE[1], (48, 0), (48, 52))
    pygame.draw.line(s, BLUE[1], (32, 50), (36, 62)); pygame.draw.line(s, BLUE[1], (64, 50), (60, 62))
    pygame.draw.polygon(s, SUIT[1], [(0, 96), (0, 84), (16, 78), (34, 80), (48, 88), (62, 80), (80, 78), (96, 84), (96, 96)])
    for k in range(3):
        pygame.draw.line(s, BLUE[2 - k // 2], (2, 88 + k * 3), (18, 81 + k * 3))
        pygame.draw.line(s, BLUE[2 - k // 2], (94, 88 + k * 3), (78, 81 + k * 3))
    pygame.draw.polygon(s, BLUE[2], [(45, 91), (48, 88), (51, 91), (48, 94)])
    return s


def portrait(masked=False):
    """Victor's 96x96 portrait from the private folder, or the drawn masked fallback."""
    key = ("portrait", masked)
    if key in _cache:
        return _cache[key]
    name = "victor_portrait_masked.png" if masked else "victor_portrait.png"
    img = None
    try:
        img = pygame.image.load(os.path.join(PRIVATE_DIR, name))
        if img.get_size() != (96, 96):
            img = pygame.transform.scale(img, (96, 96))
    except (pygame.error, FileNotFoundError, OSError):
        img = None
    if img is None:
        img = _fallback_portrait(True)
    _cache[key] = img
    return img


def heir_portrait():
    if "heir_p" not in _cache:
        s = pygame.Surface((96, 96))
        for y in range(96):
            s.fill((int(60 + 40 * y / 96), 20, int(40 + 20 * y / 96)), (0, y, 96, 1))
        pygame.draw.rect(s, (90, 20, 60), (14, 70, 68, 30), border_radius=10)
        pygame.draw.polygon(s, (230, 230, 236), [(40, 70), (56, 70), (48, 86)])
        pygame.draw.polygon(s, GOLD[2], [(44, 72), (52, 72), (48, 84)])
        pygame.draw.ellipse(s, (240, 210, 180), (26, 18, 44, 54))
        pygame.draw.ellipse(s, (240, 200, 90), (22, 10, 52, 22))
        pygame.draw.polygon(s, (240, 200, 90), [(24, 22), (30, 40), (34, 22)])
        pygame.draw.ellipse(s, (30, 20, 20), (36, 40, 6, 4))
        pygame.draw.ellipse(s, (30, 20, 20), (54, 40, 6, 4))
        pygame.draw.circle(s, GOLD[3], (57, 42), 7, 2)
        pygame.draw.line(s, GOLD[2], (63, 46), (66, 66))
        pygame.draw.arc(s, (120, 40, 40), (38, 52, 20, 10), math.pi * 1.1, math.pi * 1.95, 2)
        pygame.draw.line(s, (200, 160, 130), (48, 44), (46, 52))
        _cache["heir_p"] = s
    return _cache["heir_p"]


# ------------------------------------------------------------------ stages
def _gradient(top, bottom, h=H):
    s = pygame.Surface((W, h))
    for y in range(h):
        t = y / max(1, h - 1)
        s.fill(tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)), (0, y, W, 1))
    return s


def _towers(seed, base_col, light, h_range, width, y_base, lit):
    s = pygame.Surface((width, y_base), pygame.SRCALPHA)
    rng = random.Random(seed)
    x = 0
    while x < width:
        w = rng.randint(28, 56)
        h = rng.randint(*h_range)
        top = y_base - h
        pygame.draw.rect(s, base_col, (x, top, w, h))
        pygame.draw.line(s, tuple(min(255, c + 22) for c in base_col), (x, top), (x, y_base))
        if rng.random() < 0.3:
            pygame.draw.polygon(s, base_col, [(x, top), (x + w // 2, top - 14), (x + w, top)])
            pygame.draw.line(s, (240, 60, 60), (x + w // 2, top - 14), (x + w // 2, top - 20))
        for wy in range(top + 4, y_base - 4, 6):
            for wx in range(x + 3, x + w - 3, 5):
                if rng.random() < lit:
                    s.fill(light, (wx, wy, 2, 3))
        x += w + rng.randint(2, 10)
    return s


def _layers(morning=False):
    key = ("layers", morning)
    if key not in _cache:
        if morning:
            sky = _gradient((250, 170, 110), (255, 226, 170))
            far = _towers(1, (150, 120, 140), (255, 240, 200), (60, 110), 800, 140, 0.1)
            mid = _towers(2, (120, 96, 120), (255, 230, 170), (40, 90), 800, 150, 0.15)
        else:
            sky = _gradient((18, 14, 40), (58, 30, 86))
            rng = random.Random(4)
            for _ in range(60):
                sky.set_at((rng.randrange(W), rng.randrange(90)), (200, 200, 240))
            far = _towers(1, (40, 34, 72), (255, 210, 122), (60, 110), 800, 140, 0.25)
            mid = _towers(2, (30, 26, 52), (242, 169, 59), (40, 90), 800, 150, 0.35)
        _cache[key] = (sky, far, mid)
    return _cache[key]


FLOOR_TOP = 156      # top of the walkable band (feet y)
FLOOR_BOTTOM = 230


def _street_floor(s, cam, morning):
    base = (70, 64, 86) if morning else (52, 46, 70)
    pygame.draw.rect(s, base, (0, 146, W, 10))
    for x in range(-int(cam) % 32 - 32, W, 32):
        pygame.draw.line(s, tuple(c - 16 for c in base), (x, 146), (x - 6, 156))
    for y in range(156, H):
        t = (y - 156) / (H - 156)
        col = (int(70 + 30 * t), int(64 + 20 * t), int(80 + 14 * t)) if morning else \
              (int(34 + 20 * t), int(30 + 14 * t), int(46 + 16 * t))
        s.fill(col, (0, y, W, 1))
    for row, y in enumerate(range(160, H, 10)):
        off = (row % 2) * 9 - int(cam) % 18
        for x in range(off - 18, W, 18):
            pygame.draw.line(s, (26, 22, 36) if not morning else (80, 70, 96), (x, y), (x + 14, y))
            pygame.draw.line(s, (70, 62, 92) if not morning else (140, 130, 156), (x + 1, y + 1), (x + 8, y + 1))


def _lamp(s, x, morning):
    if not morning:
        glow = _cache.get("lampglow")
        if glow is None:
            glow = _cache["lampglow"] = pygame.Surface((120, 60), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255, 200, 110, 46), (0, 0, 120, 60))
            cone = _cache["lampcone"] = pygame.Surface((40, 90), pygame.SRCALPHA)
            pygame.draw.polygon(cone, (255, 220, 140, 26), [(16, 0), (24, 0), (40, 90), (0, 90)])
        s.blit(glow, (x - 60, 168))
        s.blit(_cache["lampcone"], (x - 8, 76))
    pygame.draw.rect(s, (24, 22, 30), (x - 2, 70, 4, 86))
    pygame.draw.rect(s, (24, 22, 30), (x - 2, 70, 16, 3))
    pygame.draw.rect(s, (255, 220, 140) if not morning else (200, 200, 190), (x + 9, 73, 6, 3))


STREET_LEN = 1500
LOBBY_LEN = 760


def street(s, cam, t=0.0, morning=False):
    """Tower Row: shops and lamps, a chain-link lot, then the Trillion Tower lobby doors."""
    sky, far, mid = _layers(morning)
    s.blit(sky, (0, 0))
    pygame.draw.circle(s, (250, 240, 210) if not morning else (255, 250, 220), (330, 34), 12 if not morning else 18)
    for layer, k, y in ((far, 0.2, 0), (mid, 0.5, 8)):
        x = -int(cam * k) % 800
        s.blit(layer, (x - 800, y))
        s.blit(layer, (x, y))
    # foreground buildings scroll with the street
    for bx, bw, kind in ((0, 160, "pharmacy"), (180, 150, "diner"), (560, 220, "lot"), (820, 200, "bank"),
                         (1060, 440, "tower")):
        x = bx - int(cam)
        if x > W or x + bw < 0:
            continue
        if kind == "lot":
            pygame.draw.rect(s, (40, 36, 50), (x, 110, bw, 40))
            for fx in range(x, x + bw, 6):
                pygame.draw.line(s, (120, 124, 136), (fx, 104), (fx + 6, 146))
                pygame.draw.line(s, (120, 124, 136), (fx + 6, 104), (fx, 146))
            pygame.draw.line(s, (150, 154, 166), (x, 104), (x + bw, 104), 2)
            continue
        col = {"pharmacy": (46, 40, 70), "diner": (60, 36, 50), "bank": (48, 48, 66), "tower": (24, 30, 48)}[kind]
        if morning:
            col = tuple(min(255, c + 70) for c in col)
        top = 40 if kind == "tower" else 70
        pygame.draw.rect(s, col, (x, top, bw, 146 - top))
        if kind == "tower":
            for gx in range(x + 6, x + bw - 4, 24):
                pygame.draw.rect(s, (40, 60, 96) if not morning else (120, 160, 200), (gx, 56, 20, 70))
                pygame.draw.line(s, (90, 130, 190), (gx + 2, 58), (gx + 8, 58))
            pygame.draw.rect(s, GOLD[1], (x, 128, bw, 4))
            pygame.draw.rect(s, GOLD[1], (x, 40, bw, 3))
            pygame.draw.rect(s, (16, 12, 20), (x + 150, 44, 140, 12))
            sign = font(14).render("TRILLION TOWER" if not morning else "TOWER ROW LIBRARY  OPEN LATE", False,
                                   GOLD[3] if not morning else (60, 40, 20))
            s.blit(sign, (x + 220 - sign.get_width() // 2, 46))
            pygame.draw.rect(s, (60, 40, 20), (x + 360, 92, 44, 54))
            pygame.draw.rect(s, GOLD[2], (x + 360, 92, 44, 54), 1)
            pygame.draw.line(s, GOLD[2], (x + 382, 92), (x + 382, 146))
            continue
        for wx in range(x + 8, x + bw - 10, 22):
            for wy in (80, 104):
                pygame.draw.rect(s, (255, 210, 122) if (wx + wy) % 3 else (60, 50, 80), (wx, wy, 12, 14))
        label = {"pharmacy": ("24H PHARMACY", (224, 64, 122)), "diner": ("DINER", (79, 180, 255)),
                 "bank": ("FIRST VAULT BANK", GOLD[2])}[kind]
        if morning and kind == "pharmacy":
            label = ("FREE CLINIC", (60, 170, 90))
        img = font(14).render(label[0], False, label[1])
        pygame.draw.rect(s, (16, 12, 22), (x + bw // 2 - img.get_width() // 2 - 4, top + 4, img.get_width() + 8, 13))
        s.blit(img, (x + bw // 2 - img.get_width() // 2, top + 6))
        pygame.draw.rect(s, (30, 24, 36), (x + bw // 2 - 10, 120, 20, 26))
    _street_floor(s, cam, morning)
    for lx in range(80, STREET_LEN, 260):
        x = lx - int(cam)
        if -60 < x < W + 60:
            _lamp(s, x, morning)


def lobby(s, cam, t=0.0):
    """The Trillion Tower lobby: marble, gold columns, a chandelier and Grandfather's portrait."""
    s.fill((60, 44, 40))
    for y in range(0, 146):
        s.fill((70 - y // 8, 52 - y // 10, 46 - y // 12), (0, y, W, 1))
    for cx in range(40, LOBBY_LEN, 120):
        x = cx - int(cam * 1.0)
        if -30 < x < W + 30:
            pygame.draw.rect(s, (230, 222, 206), (x - 8, 20, 16, 128))
            pygame.draw.line(s, (255, 250, 236), (x - 6, 20), (x - 6, 146))
            pygame.draw.line(s, (180, 170, 150), (x + 6, 20), (x + 6, 146))
            pygame.draw.rect(s, GOLD[1], (x - 11, 18, 22, 6))
            pygame.draw.rect(s, GOLD[1], (x - 11, 140, 22, 6))
    px_ = 260 - int(cam)
    if -100 < px_ < W:
        pygame.draw.rect(s, GOLD[1], (px_, 34, 84, 96))
        pygame.draw.rect(s, (60, 30, 30), (px_ + 6, 40, 72, 84))
        pygame.draw.ellipse(s, (230, 200, 170), (px_ + 24, 54, 36, 44))
        pygame.draw.rect(s, (30, 26, 40), (px_ + 14, 96, 56, 28))
        pygame.draw.ellipse(s, (230, 230, 230), (px_ + 22, 48, 40, 14))
        pygame.draw.line(s, (240, 240, 240), (px_ + 30, 88), (px_ + 54, 88), 3)       # stern moustache
        pygame.draw.circle(s, GOLD[3], (px_ + 50, 72), 5, 1)
        img = font(12).render("GRANDFATHER", False, GOLD[3])
        s.blit(img, (px_ + 42 - img.get_width() // 2, 126))
    for cx in (140, 460):
        x = cx - int(cam * 0.9)
        if -40 < x < W + 40:
            pygame.draw.line(s, GOLD[1], (x, 0), (x, 12))
            pygame.draw.polygon(s, GOLD[2], [(x - 20, 14), (x + 20, 14), (x + 12, 24), (x - 12, 24)])
            for k in range(-16, 18, 6):
                pygame.draw.circle(s, (255, 250, 220), (x + k, 26), 2)
    ex = 640 - int(cam)
    if -80 < ex < W:
        pygame.draw.rect(s, GOLD[1], (ex, 60, 70, 88))
        pygame.draw.rect(s, (150, 140, 120), (ex + 5, 68, 60, 80))
        pygame.draw.line(s, (90, 84, 70), (ex + 35, 68), (ex + 35, 148))
        pygame.draw.polygon(s, GOLD[3], [(ex + 30, 56), (ex + 40, 56), (ex + 35, 50)])
    for y in range(146, H):
        t2 = (y - 146) / (H - 146)
        s.fill((int(210 - 60 * t2), int(200 - 60 * t2), int(190 - 60 * t2)), (0, y, W, 1))
    for row, y in enumerate(range(150, H, 14)):
        off = (row % 2) * 16 - int(cam) % 32
        for x in range(off - 32, W, 32):
            pygame.draw.rect(s, (40, 36, 40), (x, y, 16, 14))
    pygame.draw.rect(s, GOLD[1], (0, 146, W, 3))


def elevator(s, floor, t=0.0, doors=0.0):
    """Inside the glass elevator: the city sinks away behind as the floors climb."""
    sky, far, mid = _layers(False)
    s.blit(sky, (0, 0))
    rise = floor * 3
    for layer, k, y in ((far, 0.6, 40), (mid, 1.0, 80)):
        s.blit(layer, (-40, y + rise * k))
        s.blit(layer, (-440, y + rise * k))
    for gx in range(0, W, 80):
        pygame.draw.rect(s, GOLD[1], (gx, 0, 4, 150))
    pygame.draw.rect(s, GOLD[1], (0, 0, W, 6))
    pygame.draw.rect(s, (40, 30, 26), (0, 146, W, H - 146))
    for y in range(150, H, 12):
        pygame.draw.line(s, (60, 46, 40), (0, y), (W, y))
    pygame.draw.rect(s, GOLD[1], (0, 146, W, 4))
    for side in (0, W - 30):            # the doors at both ends slide open at each stop
        pygame.draw.rect(s, (90, 80, 70), (side, 20, 30, 128))
        gap = int(doors * 14)
        pygame.draw.rect(s, (140, 130, 110), (side + (0 if side == 0 else 0), 20, 30, 128))
        if gap:
            pygame.draw.rect(s, (20, 16, 20), (side + 15 - gap, 24, gap * 2, 124))
    panel = pygame.Rect(W // 2 - 26, 10, 52, 18)
    pygame.draw.rect(s, OUT, panel.inflate(2, 2))
    pygame.draw.rect(s, (20, 10, 10), panel)
    img = font(20).render("%02d" % int(floor), False, (255, 80, 60))
    s.blit(img, (panel.centerx - img.get_width() // 2, panel.y + 2))
    pygame.draw.polygon(s, (255, 80, 60), [(panel.right - 8, panel.y + 12), (panel.right - 4, panel.y + 6),
                                           (panel.right - 12, panel.y + 6)])


def penthouse(s, t=0.0, vault_open=0.0, morning=False):
    """The rooftop garden at the top of Trillion Tower, with the family vault in the wall."""
    sky, far, mid = _layers(morning)
    s.blit(sky, (0, 0))
    s.blit(far, (-60, 120))
    s.blit(mid, (-200, 150))
    pygame.draw.rect(s, (54, 44, 60) if not morning else (150, 130, 140), (230, 20, 170, 126))
    pygame.draw.rect(s, GOLD[1], (230, 20, 170, 4))
    vx, vy = 316, 82
    pygame.draw.circle(s, GOLD[0], (vx, vy), 42)
    pygame.draw.circle(s, GOLD[1], (vx, vy), 38)
    pygame.draw.circle(s, GOLD[2], (vx, vy), 30, 3)
    for a in range(0, 360, 45):
        pygame.draw.line(s, GOLD[0], (vx, vy), (vx + math.cos(math.radians(a + t * 20)) * 16,
                                                 vy + math.sin(math.radians(a + t * 20)) * 16), 2)
    pygame.draw.circle(s, GOLD[3], (vx, vy), 5)
    if vault_open < 1:
        for k in range(-36, 40, 8):            # the heavy chain across the vault
            pygame.draw.ellipse(s, (150, 120, 50), (vx + k - 3, vy - 2 + int(abs(k) * 0.1), 8, 5), 2)
    for tx in (30, 120, 200):                  # dollar-shaped topiary
        pygame.draw.rect(s, (110, 80, 50), (tx + 6, 124, 12, 22))
        pygame.draw.circle(s, (40, 110, 60), (tx + 12, 112), 13)
        img = font(20).render("$", False, (70, 150, 80))
        s.blit(img, (tx + 12 - img.get_width() // 2, 103))
    pygame.draw.rect(s, GOLD[1], (0, 138, 230, 3))
    for x in range(0, 230, 12):
        pygame.draw.line(s, GOLD[1], (x, 138), (x, 146), 2)
    for y in range(146, H):
        t2 = (y - 146) / (H - 146)
        s.fill((int(120 - 40 * t2), int(100 - 30 * t2), int(90 - 30 * t2)), (0, y, W, 1))
    for row, y in enumerate(range(150, H, 12)):
        off = (row % 2) * 12
        for x in range(off - 24, W, 24):
            pygame.draw.line(s, (80, 64, 56), (x, y), (x + 20, y))


# ------------------------------------------------------------------ cutscene pieces
def rift(surf, x, y, size, t):
    """A tear in the air showing the starlit water of the Ninth Dominion."""
    if size <= 0:
        return
    h = int(70 * size)
    w = max(2, int(22 * size))
    pts = []
    for k in range(9):
        yy = y - h // 2 + k * h / 8
        wob = math.sin(t * 9 + k) * 2
        width = w * math.sin(math.pi * k / 8)
        pts.append((x - width + wob, yy))
    pts += [(2 * x - px_, py_) for px_, py_ in reversed(pts)]
    pygame.draw.polygon(surf, BLUE[3], [(px_ - 2 if px_ < x else px_ + 2, py_) for px_, py_ in pts])
    pygame.draw.polygon(surf, (8, 10, 36), pts)
    rng = random.Random(7)
    for _ in range(int(30 * size)):
        sx = x + rng.uniform(-w * 0.7, w * 0.7)
        sy = y + rng.uniform(-h * 0.4, h * 0.4)
        surf.set_at((int(sx), int(sy)), (220, 230, 255) if rng.random() < 0.7 else BLUE[2])
    pygame.draw.line(surf, (40, 70, 140), (x - w * 0.6, y + h * 0.2), (x + w * 0.6, y + h * 0.2))


def katana(surf, base, angle, length=40):
    x, y = base
    ex, ey = x + math.cos(angle) * length, y + math.sin(angle) * length
    pygame.draw.line(surf, OUT, (x, y), (ex, ey), 4)
    pygame.draw.line(surf, (220, 236, 255), (x, y), (ex, ey), 2)
    pygame.draw.line(surf, (255, 255, 255), (x, y), ((x + ex) / 2, (y + ey) / 2), 1)
    hx, hy = x - math.cos(angle) * 9, y - math.sin(angle) * 9
    pygame.draw.line(surf, (30, 30, 60), (x, y), (hx, hy), 3)
    pygame.draw.circle(surf, BLUE[2], (int(x), int(y)), 3)


def newspaper(surf, headline, sub, t):
    k = min(1.0, t / 0.6)
    w, h = int(260 * k), int(150 * k)
    if w < 10:
        return
    paper = pygame.Surface((260, 150))
    paper.fill((236, 230, 214))
    img = font(26).render("THE CONFLUENCE CALL", False, (30, 30, 30))
    paper.blit(img, (130 - img.get_width() // 2, 8))
    pygame.draw.line(paper, (30, 30, 30), (10, 30), (250, 30), 2)
    y = 36
    for line in headline:
        img = font(28).render(line, False, (20, 20, 20))
        paper.blit(img, (130 - img.get_width() // 2, y))
        y += 24
    img = font(16).render(sub, False, (60, 60, 60))
    paper.blit(img, (130 - img.get_width() // 2, y + 4))
    for ly in range(y + 24, 146, 6):
        pygame.draw.line(paper, (150, 146, 136), (12, ly), (120, ly))
        pygame.draw.line(paper, (150, 146, 136), (140, ly), (248, ly))
    paper = pygame.transform.rotozoom(paper, (1 - k) * 200, k)
    surf.blit(paper, paper.get_rect(center=(W // 2, H // 2)))


def bus(surf, x, y):
    pygame.draw.rect(surf, OUT, (x - 1, y - 1, 78, 32), border_radius=5)
    pygame.draw.rect(surf, (250, 200, 40), (x, y, 76, 30), border_radius=5)
    for wx in range(x + 6, x + 64, 12):
        pygame.draw.rect(surf, (120, 170, 210), (wx, y + 5, 9, 9))
    img = font(12).render("SCHOOL", False, (30, 30, 30))
    surf.blit(img, (x + 38 - img.get_width() // 2, y + 18))
    for wx in (x + 14, x + 60):
        pygame.draw.circle(surf, OUT, (wx, y + 30), 6)
        pygame.draw.circle(surf, (130, 130, 140), (wx, y + 30), 2)
