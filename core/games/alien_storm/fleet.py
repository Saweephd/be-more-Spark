"""The strike group seen from the side, at full screen resolution, for the cutscenes."""
import math
import random

import pygame

_c = {}
GREY, HI, DK, RED = (128, 134, 146), (170, 176, 188), (70, 76, 88), (150, 40, 44)


def _mk(w, h):
    return pygame.Surface((w * 2, h * 2), pygame.SRCALPHA)


def _fin(s):
    return pygame.transform.smoothscale(s, (s.get_width() // 2, s.get_height() // 2))


def _P(s, col, pts):
    pygame.draw.polygon(s, col, [(x * 2, y * 2) for x, y in pts])


def _R(s, col, x, y, w, h):
    pygame.draw.rect(s, col, (x * 2, y * 2, w * 2, h * 2))


def _L(s, col, a, b, w=1):
    pygame.draw.line(s, col, (a[0] * 2, a[1] * 2), (b[0] * 2, b[1] * 2), w * 2)


def carrier():
    """Nimitz class, bow to the right, 620 x 150. The waterline is at y = 132."""
    if "carrier" in _c:
        return _c["carrier"]
    s = _mk(620, 150)
    _P(s, RED, [(40, 132), (560, 132), (552, 146), (52, 146)])                          # below the waterline
    _P(s, GREY, [(18, 92), (604, 92), (590, 104), (566, 132), (40, 132), (30, 112)])    # hull
    _P(s, DK, [(30, 112), (590, 104), (588, 108), (32, 116)])
    _P(s, HI, [(4, 84), (616, 84), (612, 92), (10, 92)])                                # flight deck edge
    _P(s, DK, [(4, 84), (616, 84), (616, 86), (4, 86)])
    for x in (120, 250, 420):                                                           # elevators and sponsons
        _R(s, DK, x, 96, 54, 10)
    f = pygame.font.Font(None, 60)
    n = f.render("68", True, (236, 236, 228))
    s.blit(n, (520 * 2, 104 * 2))
    # island, toward the stern on this side
    _P(s, GREY, [(196, 84), (198, 44), (262, 44), (268, 84)])
    _P(s, HI, [(202, 52), (258, 52), (258, 58), (202, 58)])
    _R(s, (60, 110, 160), 204, 46, 52, 4)
    _R(s, GREY, 212, 26, 30, 18)
    _R(s, DK, 216, 30, 22, 3)
    _L(s, DK, (228, 26), (228, 2), 1)
    _L(s, DK, (218, 10), (238, 10), 1)
    _L(s, DK, (244, 44), (244, 14), 1)
    pygame.draw.ellipse(s, HI, (232 * 2, 16 * 2, 24 * 2, 9 * 2))                        # radar
    # aircraft parked on deck: little tails and noses
    rng = random.Random(3)
    for x in list(range(300, 500, 34)) + list(range(60, 180, 36)):
        _P(s, (150, 156, 166), [(x, 84), (x + 26, 84), (x + 22, 79), (x + 6, 78)])
        _P(s, (150, 156, 166), [(x + 2, 79), (x + 8, 79), (x + 5, 70), (x + 1, 70)])
        _R(s, (236, 190, 90), x + 16, 78, 5, 2)
    for _ in range(26):                                                                 # deck crew
        x = rng.randrange(20, 600)
        col = rng.choice(((240, 200, 60), (60, 160, 80), (220, 60, 60), (80, 120, 220), (240, 240, 240)))
        _R(s, col, x, 79, 2, 5)
    for x in range(60, 560, 16):
        _R(s, DK, x, 120, 5, 2)
    _c["carrier"] = out = _fin(s)
    return out


def destroyer():
    """Bow to the right, 300 x 90. Waterline at y = 78."""
    if "destroyer" in _c:
        return _c["destroyer"]
    s = _mk(300, 90)
    _P(s, RED, [(18, 78), (272, 78), (266, 86), (24, 86)])
    _P(s, GREY, [(6, 56), (150, 56), (296, 48), (276, 78), (16, 78)])
    _P(s, DK, [(8, 62), (284, 60), (282, 63), (9, 65)])
    _P(s, HI, [(96, 56), (100, 30), (176, 30), (184, 56)])                              # superstructure
    _P(s, GREY, [(108, 30), (112, 16), (160, 16), (166, 30)])
    _R(s, (60, 110, 160), 114, 20, 44, 4)
    _P(s, DK, [(126, 16), (130, 2), (140, 2), (144, 16)])                               # mast
    _L(s, DK, (120, 6), (150, 6), 1)
    _P(s, DK, [(66, 56), (70, 36), (88, 36), (92, 56)])                                 # funnel
    pygame.draw.ellipse(s, HI, (228 * 2, 40 * 2, 22 * 2, 14 * 2))                       # gun
    _L(s, DK, (244, 46), (274, 40), 2)
    _R(s, DK, 190, 50, 30, 6)                                                           # forward missile cells
    _R(s, DK, 28, 50, 30, 6)                                                            # aft missile cells
    f = pygame.font.Font(None, 30)
    s.blit(f.render("91", True, (236, 236, 228)), (252 * 2, 62 * 2))
    _c["destroyer"] = out = _fin(s)
    return out


def battleship():
    """An old battleship called back to sea, bow to the right, 520 x 130. Waterline at y = 116."""
    if "battleship" in _c:
        return _c["battleship"]
    s = _mk(520, 130)
    _P(s, RED, [(24, 116), (486, 116), (476, 126), (34, 126)])
    _P(s, GREY, [(8, 86), (300, 88), (516, 72), (492, 116), (22, 116)])
    _P(s, DK, [(10, 94), (504, 88), (502, 92), (11, 98)])
    _P(s, HI, [(170, 88), (176, 52), (300, 52), (310, 88)])                             # superstructure
    _P(s, GREY, [(196, 52), (200, 26), (262, 26), (268, 52)])
    _R(s, (60, 110, 160), 204, 32, 54, 5)
    _P(s, DK, [(222, 26), (226, 2), (238, 2), (242, 26)])
    _L(s, DK, (212, 10), (252, 10), 1)
    for x in (140, 276):
        _P(s, DK, [(x, 52), (x + 4, 30), (x + 22, 30), (x + 26, 52)])                   # funnels
    for x, d in ((350, 1), (410, 1), (84, -1)):                                         # three turrets
        _P(s, HI, [(x - 24, 88 if d > 0 else 87), (x - 20, 70), (x + 20, 70), (x + 24, 86)])
    f = pygame.font.Font(None, 34)
    s.blit(f.render("64", True, (236, 236, 228)), (462 * 2, 92 * 2))
    _c["battleship"] = out = _fin(s)
    return out


BB_GUNS = ((370, 76, 1), (430, 74, 1), (64, 76, -1))        # barrel roots on the battleship picture, and direction


def sub():
    """Submarine, bow to the right, 360 x 70. Waterline at about y = 46."""
    if "sub" in _c:
        return _c["sub"]
    s = _mk(360, 70)
    c1, c2 = (30, 34, 42), (56, 62, 74)
    pygame.draw.ellipse(s, c1, (8 * 2, 34 * 2, 344 * 2, 34 * 2))
    pygame.draw.ellipse(s, c2, (40 * 2, 36 * 2, 280 * 2, 10 * 2))
    _P(s, c1, [(190, 38), (194, 8), (232, 8), (240, 38)])                               # sail
    _P(s, c2, [(196, 12), (230, 12), (230, 15), (196, 15)])
    _L(s, c1, (206, 8), (206, -2), 1)
    _L(s, c1, (216, 8), (216, 0), 1)
    _P(s, c1, [(2, 28), (22, 44), (2, 52)])                                             # rudder
    for x in range(60, 180, 14):
        _R(s, (20, 22, 28), x, 37, 7, 3)                                                # missile hatches
    _c["sub"] = out = _fin(s)
    return out


def sky(top, bottom, w=800, h=480):
    key = ("sky", top, bottom, w, h)
    if key not in _c:
        s = pygame.Surface((1, h))
        for y in range(h):
            u = y / (h - 1)
            s.set_at((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * u) for i in range(3)))
        _c[key] = pygame.transform.scale(s, (w, h))
    return _c[key]


def waves(screen, y0, t, base, crest, h=480, drift=30.0):
    """Sea from y0 down to the bottom of the screen, with rows of moving crests that get bigger up close."""
    pygame.draw.rect(screen, base, (0, y0, 800, h - y0))
    rng = random.Random(1)
    rows = 14
    for r in range(rows):
        u = r / (rows - 1)
        y = y0 + 4 + int(u * u * (h - y0 - 10))
        n = 7 - int(u * 3)
        length = 14 + int(u * 60)
        for i in range(n):
            x = (rng.uniform(0, 800) + t * drift * (0.4 + u)) % 880 - 40
            yy = y + int(math.sin(t * 1.6 + i + r) * (1 + u * 3))
            pygame.draw.line(screen, crest, (int(x), yy), (int(x) + length, yy), 1 + int(u * 2))
