"""Black Warrior cast for Levels 2 to 6: enemies, guests and bosses. All original art drawn in code."""
import math

import pygame

from . import bw_art as A
from .bw_art import BLUE, GOLD, OUT, SUIT, _cache, outlined

LIGHT = {"s": (226, 182, 140), "S": (186, 140, 104), "L": (240, 200, 160), "l": (250, 216, 182)}
TAN = {"s": (200, 150, 116), "S": (150, 104, 80), "L": (220, 172, 136), "l": (236, 190, 156)}
BROWN = {"s": (124, 80, 52), "S": (90, 56, 38), "L": (150, 100, 68), "l": (176, 122, 86)}
DEEP = {"s": (96, 58, 40), "S": (66, 40, 28), "L": (120, 76, 52), "l": (146, 96, 66)}

HEAD_HAT = [
    "...yyyyyyy.....",
    "..yyyyyyyyy....",
    ".yYyyyyyyyyy...",
    "yyyyyyyyyyyyyy.",
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
HEAD_GASMASK = [
    "....hhhhhhh....",
    "..hhhhhhhhhhh..",
    ".hhhhhhhhHHhhh.",
    ".hhhhhhhhhhHhh.",
    ".hhhLlllllhhh..",
    ".hhLlllqqqqqh..",
    ".hsLLsLqQqQqs..",
    "SsssLssqqqqqsS.",
    "SsssLsssqqqqqqq",
    ".SssssssqqqqqqQ",
    ".SssssssqqqqLs.",
    "..Sssssssqss...",
    "...SSsssssS....",
    ".....SSSSS.....",
]
HEAD_BALD = [       # Uncle T: balding top with a shine, thin face, sunglasses
    "....sssssss....",
    "..sLlllllsssS..",
    ".sLlGGllllsssS.",
    ".hsLlllllllsSh.",
    ".hhLlllllllsh..",
    ".hhLkkkkkkkkh..",
    ".hsLkkkkkkkks..",
    "SsssLsssslllsS.",
    "SsssLsssslsssss",
    ".SssssssssLsss.",
    ".SssssssmmmLs..",
    "..Sssssssmss...",
    "...SSssssS.....",
    ".....SSSS......",
]
HEAD_BANDANA = [
    "....hhhhhhh....",
    "..hhhhhhhhhhh..",
    ".hhhhhhhhHHhhh.",
    "rrrrrrrrrrrrrr.",
    "r.RRrrrrrrrrr..",
    "r.hLllllkklhh..",
    ".hsLLsLlwkkLs..",
    "SsssLssslllssS.",
    "SsssLsssslsssss",
    ".SssssssssLsss.",
    ".SssssssmmmLs..",
    "..Sssssssmss...",
    "...SSsssssS....",
    ".....SSSSS.....",
]
HEAD_GOGGLES = [    # Pops: short dark hair, goggles pushed up, a mustache
    "....hhhhhhh....",
    "..hhhhhhhhhhh..",
    ".hhhhhhhhHHhhh.",
    ".qqqQQqqqQQqq..",
    ".hqQwwQqQwwQq..",
    ".hhLllllkklhh..",
    ".hsLLsLlwkkLs..",
    "SsssLssslllssS.",
    "SsssLsssslsssss",
    ".SssssshhhhLs..",
    ".SssssssmmmLs..",
    "..Sssssssmss...",
    "...SSsssssS....",
    ".....SSSSS.....",
]
HEAD_MIC = [
    "....hhhhhhh....",
    "..hhhhhhhhhhh..",
    ".hhhhhhhhHHhhh.",
    ".hhhhhhhhhhHhh.",
    ".hhhLlllllhhh..",
    ".hhLllllkklhh..",
    "khsLLsLlwkkLs..",
    "kSssLssslllssS.",
    "kSssLsssslsssss",
    ".kssssssssLsss.",
    "..kkkkkkqmmLs..",
    "..Sssssssmss...",
    "...SSsssssS....",
    ".....SSSSS.....",
]

GOON_LOOKS = {
    # kind: (palette, head, sunglasses)
    "biller": ({"a": (40, 120, 120), "A": (24, 84, 84), "c": (70, 160, 160), "C": (240, 240, 240), "b": (40, 120, 120),
                "B": (240, 240, 240), "g": (220, 60, 60), "G": (250, 250, 250), "h": (60, 40, 30), "H": (90, 60, 40)} | LIGHT,
               A.HEAD_FACE, False),
    "collector": ({"a": (90, 40, 110), "A": (60, 24, 76), "c": (130, 70, 150), "C": (200, 170, 220), "b": (90, 40, 110),
                   "B": GOLD[2], "g": GOLD[2], "G": GOLD[3], "h": (20, 16, 16), "H": (50, 44, 44)} | DEEP, A.HEAD_FACE, True),
    "picker": ({"a": (50, 90, 160), "A": (34, 60, 110), "c": (80, 130, 200), "C": (240, 160, 40), "b": (50, 90, 160),
                "B": (240, 160, 40), "g": (240, 160, 40), "G": (255, 220, 120), "h": (80, 50, 30), "H": (110, 70, 40)} | TAN,
               A.HEAD_FACE, False),
    "foreman": ({"a": (220, 110, 30), "A": (160, 70, 20), "c": (250, 150, 60), "C": (250, 250, 210), "b": (220, 110, 30),
                 "B": (250, 250, 210), "g": (250, 250, 210), "G": (255, 255, 255), "y": (250, 200, 40), "Y": (255, 240, 150),
                 "h": (40, 30, 26), "H": (70, 54, 46)} | BROWN, HEAD_HAT, False),
    "demo": ({"a": (240, 200, 40), "A": (180, 140, 20), "c": (255, 230, 100), "C": (90, 90, 90), "b": (240, 200, 40),
              "B": (90, 90, 90), "g": (250, 120, 30), "G": (255, 200, 120), "y": (250, 120, 30), "Y": (255, 190, 110),
              "h": (100, 70, 40), "H": (130, 96, 60)} | LIGHT, HEAD_HAT, False),
    "repo": ({"a": (30, 30, 36), "A": (18, 18, 22), "c": (60, 60, 70), "C": (110, 110, 124), "b": (30, 30, 36),
              "B": (230, 230, 236), "g": (200, 40, 50), "G": (240, 240, 240), "h": (24, 20, 20), "H": (54, 48, 48)} | TAN,
             A.HEAD_FACE, True),
    "bailiff": ({"a": (110, 80, 50), "A": (76, 54, 34), "c": (150, 110, 70), "C": (240, 220, 160), "b": (110, 80, 50),
                 "B": GOLD[2], "g": GOLD[2], "G": GOLD[3], "h": (150, 150, 150), "H": (190, 190, 190)} | LIGHT,
                A.HEAD_FACE, False),
    "millhand": ({"a": (90, 96, 104), "A": (60, 64, 70), "c": (130, 136, 146), "C": (190, 196, 206), "b": (90, 96, 104),
                  "B": (250, 160, 60), "g": (250, 160, 60), "G": (255, 220, 140), "q": (50, 54, 60), "Q": (140, 150, 160),
                  "h": (40, 34, 30), "H": (70, 60, 54)} | BROWN, HEAD_GASMASK, False),
    "spin": ({"a": (30, 50, 110), "A": (20, 34, 76), "c": (60, 90, 160), "C": (220, 60, 60), "b": (30, 50, 110),
              "B": (220, 60, 60), "g": (250, 250, 250), "G": (255, 255, 255), "q": (60, 60, 70), "h": (200, 170, 90),
              "H": (230, 200, 120)} | LIGHT, HEAD_MIC, False),
}


def goon(kind, pose="idle0", face=-1):
    if kind in A.GOON_PALS:
        return A.goon(kind, pose, face)
    key = ("goon2", kind, pose, face)
    if key not in _cache:
        look, head, shades = GOON_LOOKS[kind]
        pal = dict(A.VIC_PAL)
        pal.update(look)
        if shades:
            pal["w"] = pal["k"] = (20, 20, 24)
        extra = (lambda cv, lean, dy: cv.stamp(["kkkkk"], A.HX + 2 + lean, 10 + dy)) if shades else None
        s = A._figure(pal, head, pose, extra, sleeve_lines=False)
        _cache[key] = A._place(s, face)
    return _cache[key]


def robot(kind, frame=0, face=-1, throwing=False):
    """Throwing robots: the butler, a delivery gigbot with a parcel, a smogbot with a soot pot."""
    if kind == "butler":
        return A.butler(frame, face, throwing)
    key = ("robot", kind, frame % 2, face, throwing)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((34, 48), pygame.SRCALPHA)
    body = {"gigbot": (60, 150, 220), "smogbot": (90, 80, 70), "bailiff": (110, 80, 50)}[kind]
    pygame.draw.circle(s, (40, 40, 48), (16, 42), 5)
    pygame.draw.circle(s, (150, 154, 166), (16, 42), 3)
    a = (frame % 2) * math.pi / 4
    pygame.draw.line(s, (60, 60, 70), (16, 42), (16 + math.cos(a) * 3, 42 + math.sin(a) * 3))
    pygame.draw.rect(s, tuple(c // 2 for c in body), (8, 16, 18, 22), border_radius=4)
    pygame.draw.rect(s, body, (9, 17, 16, 18), border_radius=4)
    pygame.draw.rect(s, tuple(min(255, c + 60) for c in body), (11, 19, 5, 10), border_radius=2)
    pygame.draw.rect(s, (30, 30, 36), (10, 4, 16, 12), border_radius=4)
    pygame.draw.rect(s, (80, 220, 140) if kind == "gigbot" else (250, 120, 40), (13, 8, 10, 3))
    if kind == "gigbot":
        pygame.draw.rect(s, (200, 150, 90), (22 if not throwing else 24, 18 if not throwing else 10, 10, 9))
        pygame.draw.line(s, (150, 100, 60), (22, 22), (31, 22))
    else:
        pygame.draw.circle(s, (40, 36, 34), (28, 24 if not throwing else 14), 5)
        pygame.draw.circle(s, (120, 110, 100), (26, 22 if not throwing else 12), 1)
    s = outlined(s)
    if face < 0:
        s = pygame.transform.flip(s, True, False)
    _cache[key] = s
    return s


def flyer(kind, t):
    """Prior Authorizer clipboard drones and fake-news drones."""
    flap = int(t * 20) % 2
    key = ("flyer", kind, flap)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((30, 22), pygame.SRCALPHA)
    if kind == "authdrone":
        pygame.draw.rect(s, (170, 130, 80), (8, 5, 14, 15))
        pygame.draw.rect(s, (245, 245, 240), (10, 8, 10, 11))
        for y in (10, 13, 16):
            pygame.draw.line(s, (120, 120, 130), (11, y), (18, y))
        pygame.draw.rect(s, (150, 154, 166), (12, 3, 6, 4))
        img = A.font(10).render("NO", False, (220, 40, 40))
        s.blit(img, (11, 10))
    else:
        pygame.draw.rect(s, (40, 40, 48), (7, 6, 16, 12), border_radius=2)
        pygame.draw.rect(s, (200, 210, 230) if flap else (150, 160, 190), (9, 8, 12, 8))
        for k in range(4):
            pygame.draw.line(s, (90, 90, 100), (9, 9 + k * 2), (20, 9 + k * 2 + (k % 2)))
        pygame.draw.circle(s, (230, 40, 40), (19, 16), 1)
    for x in (2, 27):
        pygame.draw.line(s, (220, 224, 232), (x - 3 + flap * 2, 2), (x + 3 - flap * 2, 2))
        pygame.draw.line(s, (90, 92, 104), (x, 2), (x, 6))
    pygame.draw.line(s, (90, 92, 104), (2, 6), (27, 6))
    s = outlined(s)
    _cache[key] = s
    return s


def puff(t, hurt=False):
    """A smoke-cloud minion: lumpy soot with two angry eyes."""
    k = int(t * 6) % 3
    key = ("puff", k, hurt)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((32, 26), pygame.SRCALPHA)
    col = (250, 250, 250) if hurt else (70, 66, 64)
    for i, (x, y, r) in enumerate(((10, 15, 8), (18, 11, 9), (24, 16, 7), (16, 18, 8))):
        pygame.draw.circle(s, col, (x + (k - 1) * (i % 2), y), r)
    pygame.draw.circle(s, (110, 104, 100), (15, 9), 4)
    for x in (13, 21):
        pygame.draw.line(s, (250, 120, 40), (x - 2, 13), (x + 2, 15), 2)
    s = outlined(s)
    _cache[key] = s
    return s


# ------------------------------------------------------------------ guests
GUEST_LOOKS = {
    "uncle_t": ({"a": (40, 30, 30), "A": (26, 20, 20), "c": (80, 60, 56), "C": (130, 110, 100), "b": (40, 30, 30),
                 "B": (200, 200, 210), "g": (200, 200, 210), "G": (240, 240, 250), "h": (120, 100, 80), "H": (150, 130, 110),
                 "k": (20, 20, 26), "w": (20, 20, 26)} | LIGHT, HEAD_BALD),
    "stephen": ({"a": (60, 110, 160), "A": (40, 76, 116), "c": (100, 150, 200), "C": (240, 160, 40), "b": (60, 110, 160),
                 "B": (240, 160, 40), "g": (240, 160, 40), "G": (255, 220, 120), "y": (250, 200, 40), "Y": (255, 240, 150),
                 "h": (250, 214, 108), "H": (214, 176, 70)} | LIGHT, HEAD_HAT),
    "miles": ({"a": (42, 42, 50), "A": (28, 28, 34), "c": (84, 86, 96), "C": (140, 140, 150), "b": (52, 68, 118),
               "B": (90, 110, 160), "g": (52, 68, 118), "G": (120, 140, 190), "r": (224, 40, 40), "R": (150, 20, 24),
               "h": (250, 218, 112), "H": (206, 160, 60)} | LIGHT, HEAD_BANDANA),
    "felix": ({"a": (96, 112, 58), "A": (66, 78, 40), "c": (132, 148, 82), "C": (184, 160, 112), "b": (184, 160, 112),
               "B": (136, 116, 80), "g": (184, 160, 112), "G": (220, 200, 150), "r": (40, 116, 236), "R": (20, 62, 150),
               "h": (250, 218, 112), "H": (206, 160, 60)} | LIGHT, HEAD_BANDANA),
    "pops": ({"a": (34, 38, 60), "A": (22, 24, 40), "c": (58, 64, 98), "C": (240, 240, 244), "b": (34, 38, 60),
              "B": (190, 40, 50), "g": (190, 40, 50), "G": (250, 120, 120), "q": (60, 60, 70), "Q": (150, 200, 230),
              "h": (24, 20, 20), "H": (60, 54, 54)} | BROWN, HEAD_GOGGLES),
}


def guest_fig(kind, pose="idle0", face=1):
    key = ("guestfig", kind, pose, face)
    if key in _cache:
        return _cache[key]
    look, head = GUEST_LOOKS[kind]
    pal = dict(A.VIC_PAL)
    pal.update(look)
    extra = None
    if kind == "pops":          # the spray tank on his back
        def extra(cv, lean, dy):
            for y in range(20, 32):
                for x in range(A.HX - 13 + lean, A.HX - 8 + lean):
                    cv.put(x, y + dy, "C" if x == A.HX - 12 + lean else "g")
    s = A._figure(pal, head, pose, extra, sleeve_lines=False)
    if kind == "felix":         # Felix stands a little shorter than Miles
        w, h = s.get_size()
        s = pygame.transform.scale(s, (w, int(h * 0.9)))
        pad = pygame.Surface((w, h), pygame.SRCALPHA)
        pad.blit(s, (0, h - s.get_height()))
        s = pad
    s = A._place(s, face)
    _cache[key] = s
    return s


def car(t, rider=False):
    """Uncle T's little compact car, original design."""
    key = ("car", int(t * 12) % 2, rider)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((80, 40), pygame.SRCALPHA)
    pygame.draw.polygon(s, (190, 40, 46), [(2, 24), (8, 16), (20, 14), (30, 4), (56, 4), (66, 14), (78, 18), (78, 30), (2, 30)])
    pygame.draw.polygon(s, (230, 80, 80), [(30, 5), (56, 5), (62, 12), (26, 12)])
    pygame.draw.polygon(s, (150, 200, 230), [(32, 6), (44, 6), (44, 13), (27, 13)])
    pygame.draw.polygon(s, (150, 200, 230), [(46, 6), (55, 6), (61, 13), (46, 13)])
    pygame.draw.rect(s, (250, 240, 170), (74, 20, 4, 4))
    pygame.draw.rect(s, (220, 40, 40), (2, 20, 3, 4))
    spin = int(t * 12) % 2
    for wx in (18, 62):
        pygame.draw.circle(s, (20, 20, 24), (wx, 31), 7)
        pygame.draw.circle(s, (160, 160, 170), (wx, 31), 3)
        pygame.draw.line(s, (90, 90, 100), (wx - 2 + spin * 4, 29), (wx + 2 - spin * 4, 33))
    s = outlined(s)
    if rider:
        q = A.hero("idle0", True, 1)
        s2 = pygame.Surface((80, 74), pygame.SRCALPHA)
        s2.blit(q, (10, 0))
        s2.blit(s, (0, 34))
        s = s2
    _cache[key] = s
    return s


def girder(length=60, angle=0):
    key = ("girder", length, int(angle) // 10)
    if key not in _cache:
        s = pygame.Surface((length, 8), pygame.SRCALPHA)
        pygame.draw.rect(s, (200, 70, 50), (0, 0, length, 8))
        pygame.draw.rect(s, (230, 110, 80), (0, 0, length, 2))
        for x in range(4, length - 4, 8):
            pygame.draw.line(s, (150, 50, 36), (x, 2), (x + 4, 6))
            pygame.draw.line(s, (150, 50, 36), (x + 4, 2), (x, 6))
        _cache[key] = pygame.transform.rotate(outlined(s), -(int(angle) // 10) * 10)
    return _cache[key]


def swatter(on=False):
    key = ("swatter", on)
    if key not in _cache:
        s = pygame.Surface((16, 24), pygame.SRCALPHA)
        pygame.draw.line(s, (40, 40, 48), (8, 23), (8, 12), 2)
        pygame.draw.ellipse(s, (60, 60, 70), (1, 0, 14, 13), 2)
        for k in range(3, 13, 3):
            pygame.draw.line(s, (120, 120, 130), (3, k), (13, k))
        if on:
            pygame.draw.ellipse(s, (180, 240, 255), (0, -1, 16, 15), 1)
        _cache[key] = outlined(s)
    return _cache[key]


def spray_cloud(surf, x, y, r, t):
    for i in range(7):
        a = t * 2 + i * 0.9
        cx, cy = x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.25
        c = pygame.Surface((r, r // 2 + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(c, (200, 240, 200, 90), (0, 0, r, r // 2 + 4))
        surf.blit(c, (int(cx - r / 2), int(cy - r / 4)))


def door(open_=1.0):
    s = pygame.Surface((26, 50), pygame.SRCALPHA)
    pygame.draw.rect(s, (90, 60, 40), (0, 0, 26, 50))
    pygame.draw.rect(s, (20, 14, 14), (3, 3, 20, 47))
    w = int(20 * (1 - open_))
    if w > 0:
        pygame.draw.rect(s, (150, 100, 60), (3, 3, w, 47))
    return outlined(s)


def rope(surf, x, y0, y1):
    for y in range(int(y0), int(y1), 3):
        surf.fill((200, 180, 120), (int(x), y, 2, 2))


# ------------------------------------------------------------------ bosses
def capitalist_pig(t, state="walk", flash=False, ticket=False):
    """A huge pig in a top hat and three-piece suit, a gold pen and a giant DENIED stamp."""
    s = pygame.Surface((84, 92), pygame.SRCALPHA)
    pink, pink2, pink3 = (240, 160, 170), (210, 120, 135), (255, 200, 206)
    bob = int(math.sin(t * 8) * 2) if state == "walk" else 0
    lean = 8 if state == "charge" else 0
    for i, lx in enumerate((26, 46)):     # legs
        off = int(math.sin(t * 10 + i * 3) * 4) if state in ("walk", "charge") else 0
        pygame.draw.rect(s, (30, 30, 40), (lx + off, 66, 12, 22))
        pygame.draw.rect(s, (20, 14, 14), (lx + off - 2, 86, 16, 5))
    pygame.draw.ellipse(s, (30, 30, 40), (12 + lean, 28 + bob, 60, 46))         # suit
    pygame.draw.ellipse(s, (60, 60, 76), (16 + lean, 30 + bob, 22, 30))
    pygame.draw.polygon(s, (240, 240, 244), [(38 + lean, 30 + bob), (52 + lean, 30 + bob), (45 + lean, 52 + bob)])
    pygame.draw.polygon(s, (110, 30, 40), [(43 + lean, 32 + bob), (47 + lean, 32 + bob), (46 + lean, 46 + bob), (44 + lean, 46 + bob)])
    pygame.draw.rect(s, (140, 110, 70), (20 + lean, 52 + bob, 46, 12), border_radius=4)  # vest
    pygame.draw.line(s, GOLD[2], (30 + lean, 56 + bob), (50 + lean, 58 + bob))       # watch chain
    pygame.draw.ellipse(s, pink, (26 + lean, 4 + bob, 40, 32))                      # head
    pygame.draw.ellipse(s, pink3, (30 + lean, 6 + bob, 14, 8))
    pygame.draw.polygon(s, pink2, [(30 + lean, 8 + bob), (24 + lean, 0 + bob), (36 + lean, 4 + bob)])     # ears
    pygame.draw.polygon(s, pink2, [(58 + lean, 6 + bob), (66 + lean, 0 + bob), (62 + lean, 10 + bob)])
    pygame.draw.ellipse(s, pink2, (52 + lean, 16 + bob, 18, 13))                    # snout
    pygame.draw.circle(s, (120, 60, 70), (57 + lean, 22 + bob), 2)
    pygame.draw.circle(s, (120, 60, 70), (64 + lean, 22 + bob), 2)
    pygame.draw.circle(s, (20, 20, 24), (48 + lean, 14 + bob), 2)
    pygame.draw.line(s, (20, 20, 24), (44 + lean, 10 + bob), (51 + lean, 12 + bob), 2)     # angry brow
    pygame.draw.arc(s, (120, 40, 50), (40 + lean, 22 + bob, 14, 8), math.pi * 1.1, math.pi * 1.9, 2)
    pygame.draw.rect(s, (20, 20, 24), (32 + lean, -8 + bob + 8, 24, 4))           # top hat
    pygame.draw.rect(s, (20, 20, 24), (36 + lean, -10 + bob, 16, 8))
    pygame.draw.rect(s, (150, 30, 40), (36 + lean, -4 + bob, 16, 2))
    if ticket:
        pygame.draw.rect(s, (250, 250, 240), (60, 40, 18, 10))
        img = A.font(10).render("9999", False, (30, 30, 30))
        s.blit(img, (61, 41))
    else:   # the giant stamp
        sy = 30 + bob if state != "stamp" else 10
        pygame.draw.rect(s, (120, 70, 40), (66, sy, 6, 20))
        pygame.draw.rect(s, (160, 30, 40), (60, sy + 18, 20, 9))
        img = A.font(10).render("NO", False, (255, 220, 220))
        s.blit(img, (64, sy + 18))
    s = outlined(s)
    return A.white(s) if flash else s


def mister_poverty(t, state="walk", flash=False, fade=0.0):
    """A gaunt grey giant in a patched long coat, dragging chains of overdue bills."""
    s = pygame.Surface((70, 104), pygame.SRCALPHA)
    coat, coat2, skin = (96, 96, 106), (70, 70, 80), (170, 170, 176)
    sway = int(math.sin(t * 2) * 2)
    pygame.draw.polygon(s, coat2, [(18, 30), (52, 30), (60, 100), (10, 100)])
    pygame.draw.polygon(s, coat, [(20, 30), (40, 30), (36, 100), (12, 100)])
    for px_, py_ in ((22, 60), (40, 78), (16, 86)):
        pygame.draw.rect(s, (120, 110, 90), (px_, py_, 8, 7))
        pygame.draw.line(s, (60, 50, 40), (px_, py_), (px_ + 8, py_ + 7))
    pygame.draw.rect(s, (40, 40, 46), (24, 96, 8, 6))
    pygame.draw.rect(s, (40, 40, 46), (40, 96, 8, 6))
    pygame.draw.ellipse(s, skin, (24 + sway, 4, 22, 30))
    pygame.draw.ellipse(s, (130, 130, 140), (26 + sway, 20, 6, 10))
    pygame.draw.ellipse(s, (130, 130, 140), (38 + sway, 20, 6, 10))
    pygame.draw.circle(s, (20, 24, 40), (31 + sway, 16), 3)
    pygame.draw.circle(s, (20, 24, 40), (40 + sway, 16), 3)
    pygame.draw.circle(s, (120, 180, 255), (31 + sway, 16), 1)
    pygame.draw.circle(s, (120, 180, 255), (40 + sway, 16), 1)
    pygame.draw.line(s, (80, 80, 90), (30 + sway, 28), (40 + sway, 28))
    pygame.draw.rect(s, (60, 60, 70), (18 + sway, 0, 34, 6))           # battered hat
    pygame.draw.rect(s, (60, 60, 70), (24 + sway, -6, 22, 8))
    arm = 30 if state == "whip" else 0
    pygame.draw.line(s, coat, (48, 36), (60, 56 - arm), 6)
    pygame.draw.circle(s, skin, (61, 57 - arm), 3)
    s = outlined(s)
    if fade > 0:
        s = s.copy()
        s.fill((255, 255, 255, int(255 * (1 - fade))), special_flags=pygame.BLEND_RGBA_MULT)
    return A.white(s) if flash else s


def bills_chain(surf, x0, y0, x1, y1, t):
    n = max(2, int(math.hypot(x1 - x0, y1 - y0) // 8))
    for i in range(n):
        u = i / (n - 1)
        x = x0 + (x1 - x0) * u
        y = y0 + (y1 - y0) * u + math.sin(t * 10 + i) * 2
        pygame.draw.ellipse(surf, (150, 150, 160), (int(x) - 3, int(y) - 2, 7, 5), 2)
        if i % 3 == 0:
            pygame.draw.rect(surf, (240, 236, 220), (int(x) - 3, int(y) + 2, 7, 9))
            pygame.draw.line(surf, (200, 40, 40), (int(x) - 2, int(y) + 5), (int(x) + 2, int(y) + 5))


def madame_eviction(t, state="cab", flash=False, notice=False):
    """Madame Eviction: steel heels, a fur collar, a clipboard of notices, a lot of attitude."""
    s = pygame.Surface((44, 70), pygame.SRCALPHA)
    kick = state == "kick"
    pygame.draw.line(s, (40, 40, 48), (18, 50), (16 if not kick else 32, 66 if not kick else 52), 4)
    pygame.draw.line(s, (40, 40, 48), (26, 50), (28, 66), 4)
    for hx, hy in (((14, 66) if not kick else (34, 51)), (28, 66)):
        pygame.draw.line(s, (180, 184, 196), (hx, hy), (hx + 4, hy), 2)
    pygame.draw.polygon(s, (140, 20, 60), [(12, 24), (32, 24), (36, 52), (8, 52)])
    pygame.draw.ellipse(s, (240, 230, 220), (8, 18, 28, 12))                      # fur collar
    pygame.draw.circle(s, (232, 196, 170), (22, 12), 8)
    pygame.draw.ellipse(s, (60, 20, 30), (12, 0, 22, 12))                         # tall hair
    pygame.draw.ellipse(s, (60, 20, 30), (14, -6, 16, 12))
    pygame.draw.line(s, (20, 20, 24), (18, 11), (21, 12), 2)
    pygame.draw.line(s, (20, 20, 24), (24, 12), (27, 11), 2)
    pygame.draw.arc(s, (190, 30, 60), (18, 14, 9, 6), math.pi * 1.1, math.pi * 1.9, 2)
    if notice:
        pygame.draw.rect(s, (250, 250, 240), (26, 28, 14, 18))
        pygame.draw.line(s, (220, 40, 40), (28, 32), (38, 32), 2)
    else:
        pygame.draw.rect(s, (170, 130, 80), (30, 30, 10, 14))
        pygame.draw.rect(s, (250, 250, 240), (31, 32, 8, 10))
    s = outlined(s)
    return A.white(s) if flash else s


def crane(surf, x, top, cab_x):
    pygame.draw.rect(surf, (200, 160, 40), (x - 6, top, 12, 150 - top))
    for y in range(top, 146, 10):
        pygame.draw.line(surf, (150, 110, 20), (x - 6, y), (x + 6, y + 10))
    pygame.draw.rect(surf, (200, 160, 40), (x - 100, top - 6, 220, 8))
    for xx in range(x - 100, x + 120, 10):
        pygame.draw.line(surf, (150, 110, 20), (xx, top - 6), (xx + 10, top + 2))
    pygame.draw.rect(surf, (220, 180, 60), (cab_x - 14, top + 2, 28, 20))
    pygame.draw.rect(surf, (150, 200, 230), (cab_x - 10, top + 6, 20, 8))


def wrecking_ball(surf, x, y, anchor):
    pygame.draw.line(surf, (60, 60, 66), anchor, (x, y - 12), 2)
    pygame.draw.circle(surf, OUT, (int(x), int(y)), 14)
    pygame.draw.circle(surf, (60, 60, 70), (int(x), int(y)), 13)
    pygame.draw.circle(surf, (110, 110, 124), (int(x) - 4, int(y) - 4), 4)


def baron_smog(t, state="walk", flash=False, bike=False):
    """Baron Smog in his soot-belching mech suit, a vacuum arm and a top hat on the cockpit."""
    s = pygame.Surface((96, 100), pygame.SRCALPHA)
    if bike:
        pygame.draw.circle(s, (30, 30, 36), (30, 88), 10, 2)
        pygame.draw.circle(s, (30, 30, 36), (66, 88), 10, 2)
        pygame.draw.lines(s, (40, 140, 90), False, [(30, 88), (46, 72), (66, 88)], 3)
        pygame.draw.line(s, (40, 140, 90), (46, 72), (60, 70), 3)
        pygame.draw.ellipse(s, (60, 50, 50), (36, 46, 20, 28))
        pygame.draw.circle(s, (236, 200, 170), (46, 40), 8)
        pygame.draw.rect(s, (20, 20, 24), (38, 26, 16, 8))
        return outlined(s)
    vent = state == "vent"
    for lx in (22, 58):
        pygame.draw.rect(s, (70, 64, 60), (lx, 64, 16, 30))
        pygame.draw.rect(s, (40, 36, 34), (lx - 4, 90, 24, 8))
    pygame.draw.rect(s, (90, 80, 74), (14, 26, 68, 42), border_radius=8)
    pygame.draw.rect(s, (120, 108, 100), (18, 30, 30, 8), border_radius=3)
    for k in range(3):
        pygame.draw.rect(s, (240, 120, 40) if vent and int(t * 10 + k) % 2 else (60, 54, 50), (54, 32 + k * 10, 22, 6))
    pygame.draw.circle(s, (150, 200, 230), (40, 22), 13)
    pygame.draw.circle(s, (236, 200, 170), (40, 24), 7)
    pygame.draw.line(s, (40, 30, 30), (34, 26), (46, 26), 2)                        # moustache
    pygame.draw.rect(s, (20, 20, 24), (32, 4, 16, 10))
    pygame.draw.rect(s, (20, 20, 24), (28, 13, 24, 3))
    for i, sx in enumerate((20, 70)):                                               # smokestacks
        pygame.draw.rect(s, (60, 54, 50), (sx, 0, 8, 28))
        pygame.draw.circle(s, (80, 76, 74), (sx + 4 + int(math.sin(t * 6 + i) * 2), -2), 5)
    arm_x = 90 if state == "vacuum" else 84
    pygame.draw.line(s, (110, 100, 92), (80, 46), (arm_x, 56), 7)
    pygame.draw.circle(s, (40, 36, 34), (arm_x, 58), 8)
    pygame.draw.circle(s, (10, 10, 12), (arm_x, 58), 5)
    s = outlined(s)
    return A.white(s) if flash else s


def big_lie(t, state="float", flash=False, small=False, shield=False):
    """The Big Lie: a towering figure with a television for a head and a megaphone for a mouth."""
    if small:
        s = pygame.Surface((24, 22), pygame.SRCALPHA)
        pygame.draw.rect(s, (60, 60, 70), (2, 2, 20, 16), border_radius=3)
        pygame.draw.rect(s, (150, 160, 180), (4, 4, 16, 10))
        pygame.draw.polygon(s, (200, 60, 60), [(12, 14), (18, 20), (6, 20)])
        return outlined(s)
    s = pygame.Surface((84, 120), pygame.SRCALPHA)
    pygame.draw.polygon(s, (40, 40, 56), [(22, 46), (62, 46), (70, 116), (14, 116)])
    pygame.draw.polygon(s, (60, 60, 80), [(24, 46), (42, 46), (38, 116), (18, 116)])
    pygame.draw.polygon(s, (200, 40, 50), [(38, 46), (46, 46), (44, 80), (40, 80)])
    pygame.draw.rect(s, (60, 60, 70), (14, 6, 56, 42), border_radius=6)
    pygame.draw.rect(s, (30, 30, 36), (18, 10, 48, 32), border_radius=4)
    rng_seed = int(t * 20)
    for y in range(12, 40, 2):
        for x in range(20, 64, 4):
            v = ((x * 31 + y * 17 + rng_seed * 13) % 7) * 30
            s.fill((v, v, min(255, v + 20)), (x, y, 4, 2))
    pygame.draw.circle(s, (240, 60, 60), (32, 22), 3)
    pygame.draw.circle(s, (240, 60, 60), (52, 22), 3)
    pygame.draw.polygon(s, (200, 200, 210), [(36, 32), (48, 32), (60, 42), (24, 42)])   # megaphone mouth
    pygame.draw.line(s, (90, 90, 100), (30, 6), (22, -2), 2)
    pygame.draw.line(s, (90, 90, 100), (54, 6), (62, -2), 2)
    s = outlined(s)
    if shield:
        sh = pygame.Surface((96, 128), pygame.SRCALPHA)
        sh.blit(s, (6, 4))
        pygame.draw.ellipse(sh, (180, 120, 255, 90), (0, 0, 96, 128), 4)
        s = sh
    return A.white(s) if flash else s
