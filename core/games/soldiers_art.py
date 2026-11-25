"""Art for Soldiers vs Spies: NES-style figures, terrain kits, vehicles, bosses and the story scenes.

Figures are assembled from parts (head, torso, arms with the rifle at any of
four aims, and legs posed by joint angles), drawn pixel by pixel and given a
dark outline, so Miles, Felix and every spy share one look. All of it is drawn
once and cached. Everything here is original art.
"""
import math
import random

import pygame

from . import pixart as px

OUT = (18, 14, 22)
W, H = 400, 240
GROUND = 206

_cache = {}
_fonts = {}


def font(size):
    f = _fonts.get(size)
    if f is None:
        f = _fonts[size] = pygame.font.Font(None, size)
        from . import common
        common.FONT_SIZES[id(f)] = size
    return f


def plain(surf, msg, pos, size, col):
    """Words with no outline (on paper): sharp when the game asks for sharp lettering."""
    from . import common
    if common.sharp(surf):
        common.sharp_add(msg, pos, size, col)
    else:
        surf.blit(font(size).render(msg, False, col), pos)


def say(surf, msg, pos, size=18, col=(255, 255, 255), center=True, outline=OUT):
    px.outlined_text(surf, font(size), msg, pos, col, outline=outline, center=center)


def outlined(surf, col=OUT):
    """A one-pixel dark outline around everything drawn, like NES sprites."""
    w, h = surf.get_size()
    out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
    sil = pygame.mask.from_surface(surf).to_surface(setcolor=col + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(sil, (dx, dy))
    out.blit(surf, (1, 1))
    return out


def white(surf):
    key = ("white", id(surf))
    s = _cache.get(key)
    if s is None:
        s = _cache[key] = pygame.mask.from_surface(surf).to_surface(setcolor=(255, 255, 255, 255),
                                                                    unsetcolor=(0, 0, 0, 0))
    return s


# ---------------------------------------------------------------- pixel canvas
class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = {}

    def put(self, x, y, k):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[(x, y)] = k

    def stamp(self, rows, ox, oy):
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch not in ". ":
                    self.put(ox + x, oy + y, ch)

    def blob(self, x, y, k, size):
        r0 = -(size // 2)
        for dy in range(r0, r0 + size):
            for dx in range(r0, r0 + size):
                self.put(x + dx, y + dy, k)

    def line(self, a, b, k, size=1):
        (x0, y0), (x1, y1) = a, b
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(int(round(n)) + 1):
            t = i / n
            self.blob(int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t)), k, size)

    def surface(self, pal):
        s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        for (x, y), k in self.px.items():
            if k in pal:
                s.set_at((x, y), pal[k])
        return s


# ---------------------------------------------------------------- figures
COMMON = {"h": (250, 218, 112), "H": (206, 160, 60), "s": (246, 198, 158), "S": (206, 146, 110),
          "K": (26, 22, 30), "e": (64, 46, 34), "E": (230, 196, 80), "o": (74, 54, 42), "O": (40, 28, 24),
          "g": (156, 160, 172), "G": (66, 68, 80), "w": (255, 255, 236), "x": (240, 240, 240),
          "t": (200, 30, 40), "n": (44, 32, 30), "m": (90, 96, 104), "M": (60, 64, 72)}

HERO_LOOK = {
    "miles": {"b": (224, 40, 40), "B": (150, 20, 24), "v": (42, 42, 50), "V": (84, 86, 96),
              "p": (52, 68, 118), "P": (34, 44, 80), "c": (72, 92, 146)},
    "felix": {"b": (40, 116, 236), "B": (20, 62, 150), "v": (96, 112, 58), "V": (132, 148, 82),
              "p": (184, 160, 112), "P": (136, 116, 80), "c": (120, 98, 58)},
}
GUARD_LOOK = {      # spy guards wear the colors of each mission
    "carrier": {"v": (96, 104, 120), "V": (130, 138, 152), "p": (76, 82, 96), "P": (56, 60, 72), "m": (70, 76, 90)},
    "base": {"v": (120, 104, 70), "V": (150, 132, 92), "p": (96, 82, 56), "P": (72, 62, 42), "m": (90, 78, 50)},
    "airfield": {"v": (120, 120, 132), "V": (156, 156, 168), "p": (90, 90, 100), "P": (66, 66, 76), "m": (80, 80, 90)},
    "snow": {"v": (226, 230, 238), "V": (250, 252, 255), "p": (190, 196, 210), "P": (150, 156, 172), "m": (200, 206, 220)},
    "island": {"v": (90, 120, 70), "V": (120, 150, 92), "p": (70, 96, 56), "P": (50, 70, 40), "m": (70, 96, 56)},
}
SPY_LOOK = {"v": (32, 32, 40), "V": (70, 70, 84), "p": (32, 32, 40), "P": (20, 20, 26)}

HEADS = {
    "hero": ["......hhhh........",
             "....hhhhhhhh......",
             "...hHhhhhhhhh.....",
             ".bbbbbbbbbbbbb....",
             "b.bBBbbbbbbbb.....",
             "b..HHhssssKs......",
             "....Hsssssssss....",
             ".....SsssssS......"],
    "helmet": ["......mmmm........",
               "....mmmmmmmm......",
               "...mmMmmmmmmm.....",
               "...mmmmmmmmmmm....",
               "...MMMMMMMMMMMMM..",
               ".....SsssKss......",
               ".....sssssssss....",
               ".....SsssssS......"],
    "spy": ["......nnnn........",
            "....nnnnnnnn......",
            "...nnnnnnnnnn.....",
            "...nnnnnnnnnnn....",
            "...nnSsssssss.....",
            "...nnsKKKKKKKK....",
            "....Sssssssss.....",
            ".....SsssssS......"],
}
TORSOS = {
    "hero": ["........sS........",
             ".....vvvvvvv......",
             "....svvvvvvvs.....",
             "....svVvvvvvs.....",
             "....ssvVvvvvs.....",
             ".....svvVvvv......",
             ".....vvvvvvv......",
             ".....eeEeeee......",
             ".....ppppppp......"],
    "guard": ["........sS........",
              ".....vvvvvvv......",
              "....vvvVvvvvv.....",
              "....vvvvVvvvv.....",
              "....vvVvvvvvv.....",
              ".....vvvvVvv......",
              ".....vvvvvvv......",
              ".....eeEeeee......",
              ".....ppppppp......"],
    "spy": ["........sS........",
            ".....vvxxvvv......",
            "....vvvxtxvvv.....",
            "....vVvxtvvvv.....",
            "....vvVxxVvvv.....",
            ".....vvvvvvv......",
            ".....vvvvvvv......",
            ".....vvvvvvv......",
            ".....ppppppp......"],
}
AIMS = {"fwd": (1.0, 0.0), "up": (0.0, -1.0), "dup": (0.75, -0.75), "ddn": (0.75, 0.75)}
# legs as (thigh, shin) angles in degrees from straight down; positive points forward
LEG_POSES = {
    "stand": ((4, 0), (-6, 0)),
    "run0": ((32, 6), (-26, -52)),
    "run1": ((12, -2), (4, -74)),
    "run2": ((-26, -52), (32, 6)),
    "run3": ((4, -74), (12, -2)),
    "fall": ((26, -30), (-10, 4)),
    "kneel": ((84, 0), (4, -90)),
}
RUN = ("run0", "run1", "run2", "run3")
PAD = 10
HX = 9


def _build_figure(look, style, thigh, shin, pose, aim, armed=True, swing=0):
    pal = dict(COMMON)
    pal.update(look)
    cv = Canvas(36, PAD + 8 + 8 + thigh + shin + 6)
    muzzle_at = (HX + 8, PAD + 10)
    torso_top = PAD + 8
    hip = torso_top + 8
    legs = LEG_POSES[pose]
    feet = []
    for i, (a1, a2) in enumerate(reversed(legs)):         # far leg first
        near = i == 1
        hx = HX + (1 if near else -1)
        knee = (hx + thigh * math.sin(math.radians(a1)), hip + thigh * math.cos(math.radians(a1)))
        foot = (knee[0] + shin * math.sin(math.radians(a2)), knee[1] + shin * math.cos(math.radians(a2)))
        col = "p" if near else "P"
        cv.line((hx, hip), knee, col, 3)
        cv.line(knee, foot, col, 3)
        fx, fy = int(round(foot[0])), int(round(foot[1]))
        boot = "o" if near else "O"
        toe = 1 if a2 > -60 else -1
        for dx in range(-1, 3):
            cv.put(fx + dx * toe, fy, boot)
            cv.put(fx + dx * toe, fy + 1, "O")
        cv.put(fx - toe, fy - 1, boot)
        cv.put(fx, fy - 1, boot)
        feet.append(fy + 1)
    if "c" in pal:          # camouflage blotches on the trousers
        for (x, y), k in list(cv.px.items()):
            if k in "pP" and ((x * 7 + y * 13) % 11) < 3:
                cv.px[(x, y)] = "c"
    tstyle = {"hero": "hero", "helmet": "guard", "spy": "spy"}[style]
    cv.stamp(TORSOS[tstyle], 0, torso_top)
    cv.stamp(HEADS[style], 0, PAD)
    sleeve = "s" if style == "hero" else "v"
    if armed:
        dx, dy = AIMS[aim]
        sh = (HX + 3, torso_top + 2)
        if aim == "up":
            sh = (HX + 4, torso_top + 1)
        hand = (sh[0] + dx * 5, sh[1] + dy * 5)
        back = (HX - 2, torso_top + 3)
        cv.line(back, (hand[0] - dx * 2 + (1 if aim == "up" else 0), hand[1] - dy * 2), "S" if style == "hero" else "V", 2)
        g0 = (hand[0] - dx * 3, hand[1] - dy * 3)
        g1 = (hand[0] + dx * 10, hand[1] + dy * 10)
        perp = (0, 1) if aim == "fwd" else ((1, 0) if aim == "up" else (0, 1))
        cv.line((g0[0] + perp[0], g0[1] + perp[1]), (g1[0] - dx * 3 + perp[0], g1[1] - dy * 3 + perp[1]), "G", 1)
        cv.line(g0, g1, "g", 1)
        cv.put(int(round(g1[0])), int(round(g1[1])), "w")
        muzzle_at = (int(round(g1[0])), int(round(g1[1])))
        if aim in ("fwd", "ddn"):        # magazine
            cv.line((hand[0] + 2, hand[1] + 1), (hand[0] + 1, hand[1] + 4), "G", 2)
        cv.line(sh, hand, sleeve, 2)
        cv.blob(int(round(hand[0])), int(round(hand[1])), "s", 2)
    else:                       # running spy guard swinging his arms
        for k, a in (("V", -55 * swing), ("m", 55 * swing)):
            sh = (HX + (3 if k == "m" else -2), torso_top + 2)
            end = (sh[0] + 7 * math.sin(math.radians(a)), sh[1] + 7 * math.cos(math.radians(a)))
            cv.line(sh, end, k, 2)
            cv.blob(int(round(end[0])), int(round(end[1])), "s", 2)
    s = cv.surface(pal)
    bottom = max(feet)
    top = PAD - 8
    s = s.subsurface((0, top, s.get_width(), bottom - top + 1)).copy()
    # +1 everywhere: the outline shifts the picture by a pixel. The muzzle is kept as (x, height above the feet).
    return outlined(s), HX + 1, (muzzle_at[0] + 1, bottom - muzzle_at[1])


def figure(kind, pose="stand", aim="fwd", face=1, theme="carrier", swing=0):
    """kind: 'miles', 'felix', 'guard' or 'spy'. Returns (surface, anchor x of the feet)."""
    return _figure(kind, pose, aim, face, theme, swing)[:2]


def muzzle_offset(kind, pose, aim, face):
    """Where the bullets leave the rifle: (dx from the feet, height above the feet)."""
    s, ax, (mx, my) = _figure(kind, pose, aim, face, "carrier", 0)
    return mx - ax, my


def _figure(kind, pose, aim, face, theme, swing):
    key = ("fig", kind, pose, aim, face, theme if kind == "guard" else "", swing)
    hit = _cache.get(key)
    if hit:
        return hit
    if kind == "miles":
        s, ax, mz = _build_figure(HERO_LOOK["miles"], "hero", 7, 8, pose, aim)
    elif kind == "felix":
        s, ax, mz = _build_figure(HERO_LOOK["felix"], "hero", 5, 5, pose, aim)
    elif kind == "guard":
        s, ax, mz = _build_figure(GUARD_LOOK[theme], "helmet", 4, 5, pose, aim, armed=False, swing=swing)
    else:
        s, ax, mz = _build_figure(SPY_LOOK, "spy", 4, 5, pose, aim)
    if face < 0:
        s = pygame.transform.flip(s, True, False)
        ax = s.get_width() - 1 - ax
        mz = (s.get_width() - 1 - mz[0], mz[1])
    _cache[key] = (s, ax, mz)
    return s, ax, mz


def tuck(kind, frame, face=1):
    """The somersault ball for a jumping hero, four turning frames."""
    key = ("tuck", kind, frame % 4, face)
    if key in _cache:
        return _cache[key]
    pal = dict(COMMON)
    pal.update(HERO_LOOK[kind])
    cv = Canvas(15, 15)
    for y in range(15):
        for x in range(15):
            d = math.hypot(x - 7, y - 7)
            if d <= 6.4:
                cv.put(x, y, "p" if (x + y) > 13 else "v")
                if d > 5.2 and x > 7 and y < 7:
                    cv.put(x, y, "V")
    cv.stamp(["..hhh", ".hhhhh", "bbbbbb", "Hhss"], 2, 1)
    cv.stamp(["oo", "oo"], 11, 9)
    cv.stamp(["oo", "oO"], 9, 11)
    cv.stamp(["ss", "ss"], 6, 6)
    s = outlined(cv.surface(pal))
    s = pygame.transform.rotate(s, -90 * (frame % 4))
    if face < 0:
        s = pygame.transform.flip(s, True, False)
    _cache[key] = s
    return s


def lying(kind, face=1):
    key = ("lie", kind, face)
    if key not in _cache:
        s, _ = figure(kind, "stand", "fwd", 1)
        s = pygame.transform.rotate(s, 90)
        if face > 0:
            s = pygame.transform.flip(s, True, False)
        _cache[key] = s
    return _cache[key]


def chute(colors=((236, 238, 242), (110, 130, 80))):
    key = ("chute", colors)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((34, 30), pygame.SRCALPHA)
    pygame.draw.ellipse(s, colors[0], (0, 0, 34, 22))
    for i in range(1, 7, 2):
        pygame.draw.polygon(s, colors[1], [(17, 1), (i * 34 // 7, 10), ((i + 1) * 34 // 7, 10)])
    for i in range(7):
        pygame.draw.polygon(s, colors[i % 2], [(i * 34 // 7, 10), ((i + 1) * 34 // 7, 10), ((i + 1) * 34 // 7 - 1, 13),
                                               (i * 34 // 7 + 1, 13)])
    s.fill((0, 0, 0, 0), (0, 12, 34, 18))
    for x in (2, 32):
        pygame.draw.line(s, (90, 90, 96), (x, 12), (17, 29))
    for x in (11, 23):
        pygame.draw.line(s, (90, 90, 96), (x, 12), (17, 29))
    s = outlined(s)
    _cache[key] = s
    return s


# ---------------------------------------------------------------- small things
def pickup_badge(kind, t):
    flap = int(t * 8) % 2
    key = ("badge", kind, flap)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((24, 14), pygame.SRCALPHA)
    wing = (210, 214, 224)
    for side in (-1, 1):
        cx = 12 + side * 6
        tip = 12 + side * 12
        pts = [(cx, 5), (tip, 2 + flap * 3), (tip - side * 2, 8), (cx, 10)]
        pygame.draw.polygon(s, wing, pts)
        pygame.draw.line(s, (150, 154, 166), (cx, 7), (tip - side * 2, 6))
    pygame.draw.polygon(s, (220, 40, 40), [(7, 1), (17, 1), (17, 8), (12, 13), (7, 8)])
    pygame.draw.polygon(s, (255, 230, 120), [(7, 1), (17, 1), (17, 2), (7, 2)])
    s = outlined(s)
    letter = font(14).render(kind if kind != "1UP" else "1", False, (255, 255, 255))
    s.blit(letter, (13 - letter.get_width() // 2, 1))
    _cache[key] = s
    return s


def capsule(t):
    frames = _cache.get("capsules")
    if frames is None:
        frames = _cache["capsules"] = [outlined(f) for f in px.capsule_frames()]
    return frames[int(t * 10) % 4]


def booms():
    if "booms" not in _cache:
        small = px.explosion_frames(26, seed=3)
        big = [pygame.transform.scale(f, (52, 52)) for f in px.explosion_frames(26, seed=7)]
        _cache["booms"] = (small, big)
    return _cache["booms"]


def medal():
    if "medal" not in _cache:
        _cache["medal"] = outlined(px.medal())
    return _cache["medal"]


def turret(angle, hurt=False):
    """A wall turret set into the rock: steel ring, dark socket and a barrel that tracks you."""
    step = int(round(angle / (math.pi / 6))) % 12
    key = ("turret", step, hurt)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((26, 26), pygame.SRCALPHA)
    c = 13
    pygame.draw.circle(s, (70, 72, 82), (c, c), 10)
    pygame.draw.circle(s, (150, 154, 166), (c, c), 9)
    pygame.draw.circle(s, (200, 204, 214), (c - 2, c - 2), 6)
    pygame.draw.circle(s, (40, 40, 48), (c, c), 6)
    pygame.draw.circle(s, (230, 60, 50) if not hurt else (255, 255, 255), (c, c), 3)
    s.set_at((c - 1, c - 1), (255, 220, 200))
    a = step * math.pi / 6
    end = (c + math.cos(a) * 12, c + math.sin(a) * 12)
    pygame.draw.line(s, (40, 40, 48), (c, c), end, 5)
    pygame.draw.line(s, (170, 174, 186), (c, c), end, 2)
    for b in range(4):
        ba = b * math.pi / 2 + math.pi / 4
        s.set_at((int(c + math.cos(ba) * 8), int(c + math.sin(ba) * 8)), (240, 240, 250))
    s = outlined(s)
    _cache[key] = s
    return s


def _veh(key, draw, size):
    if key not in _cache:
        s = pygame.Surface(size, pygame.SRCALPHA)
        draw(s)
        _cache[key] = outlined(s)
    return _cache[key]


def drone(t):
    def d(s):
        pygame.draw.rect(s, (70, 72, 84), (6, 5, 14, 6), border_radius=2)
        pygame.draw.rect(s, (110, 114, 128), (7, 5, 12, 2))
        pygame.draw.circle(s, (230, 60, 50), (13, 10), 2)
        for x in (3, 23):
            pygame.draw.line(s, (90, 92, 104), (x, 4), (x, 7))
        pygame.draw.line(s, (90, 92, 104), (3, 6), (23, 6))
    body = _veh("drone", d, (27, 14))
    out = body.copy()
    blade = int(t * 30) % 2
    for x in (4, 24):
        pygame.draw.line(out, (220, 224, 232), (x - 4 + blade * 2, 3), (x + 4 - blade * 2, 3), 1)
    return out


def jeep():
    def d(s):
        pygame.draw.polygon(s, (90, 104, 62), [(2, 12), (6, 6), (16, 6), (20, 2), (40, 2), (42, 12), (42, 18), (2, 18)])
        pygame.draw.rect(s, (120, 134, 86), (6, 7, 36, 3))
        pygame.draw.polygon(s, (150, 200, 230), [(8, 7), (14, 7), (17, 3), (12, 3)])
        pygame.draw.rect(s, (50, 56, 40), (26, 0, 4, 4))
        pygame.draw.line(s, (40, 40, 48), (28, 1), (16, 0), 2)
        for x in (10, 34):
            pygame.draw.circle(s, (28, 28, 34), (x, 18), 5)
            pygame.draw.circle(s, (130, 130, 140), (x, 18), 2)
        pygame.draw.rect(s, (250, 230, 120), (2, 12, 3, 2))
    return _veh("jeep", d, (44, 24))


def sled():
    def d(s):
        pygame.draw.polygon(s, (200, 40, 40), [(4, 4), (26, 4), (32, 10), (30, 14), (2, 14)])
        pygame.draw.rect(s, (240, 240, 250), (6, 6, 18, 2))
        pygame.draw.polygon(s, (150, 200, 230), [(8, 4), (12, 0), (16, 0), (14, 4)])
        pygame.draw.line(s, (40, 40, 48), (0, 17), (34, 17), 2)
        pygame.draw.line(s, (40, 40, 48), (34, 17), (36, 14), 2)
        pygame.draw.rect(s, (32, 32, 40), (18, 0, 6, 5))
        pygame.draw.rect(s, (246, 198, 158), (19, 0, 4, 2))
    return _veh("sled", d, (38, 20))


def boat():
    def d(s):
        pygame.draw.polygon(s, (70, 74, 86), [(2, 8), (46, 8), (40, 18), (8, 18)])
        pygame.draw.polygon(s, (110, 116, 130), [(2, 8), (46, 8), (45, 10), (3, 10)])
        pygame.draw.rect(s, (90, 96, 110), (18, 2, 14, 7))
        pygame.draw.rect(s, (150, 200, 230), (20, 3, 10, 3))
        pygame.draw.line(s, (40, 40, 48), (12, 6), (2, 3), 2)
        pygame.draw.rect(s, (200, 40, 40), (34, 4, 3, 4))
    return _veh("boat", d, (48, 20))


# ---------------------------------------------------------------- bosses
def boss_sprite(kind, t, hp_frac):
    if kind == "heli":
        def d(s):
            pygame.draw.ellipse(s, (64, 76, 58), (6, 12, 58, 24))
            pygame.draw.ellipse(s, (92, 108, 80), (10, 13, 48, 9))
            pygame.draw.polygon(s, (64, 76, 58), [(56, 18), (96, 20), (98, 26), (58, 28)])
            pygame.draw.polygon(s, (64, 76, 58), [(92, 12), (100, 12), (98, 26), (92, 24)])
            pygame.draw.polygon(s, (150, 210, 240), [(8, 22), (20, 14), (26, 14), (24, 24)])
            pygame.draw.line(s, (230, 250, 255), (12, 21), (20, 15))
            pygame.draw.rect(s, (40, 44, 40), (24, 32, 26, 6))
            pygame.draw.circle(s, (220, 60, 50), (28, 35), 2)
            pygame.draw.circle(s, (220, 60, 50), (46, 35), 2)
            pygame.draw.line(s, (50, 50, 56), (14, 44), (50, 44), 2)
            for x in (22, 42):
                pygame.draw.line(s, (50, 50, 56), (x, 36), (x - 2, 44), 2)
            pygame.draw.rect(s, (40, 44, 40), (30, 8, 10, 6))
            pygame.draw.line(s, (30, 30, 34), (6, 30), (-2, 32), 3)
        body = _veh("b_heli", d, (102, 48))
        out = body.copy()
        sweep = int(abs(math.sin(t * 30)) * 46)
        pygame.draw.line(out, (210, 214, 224), (36 - sweep, 8), (36 + sweep, 8), 2)
        pygame.draw.circle(out, (210, 214, 224), (98, 20), 4 + int(t * 40) % 3, 1)
        return out
    if kind == "truck":
        def d(s):
            pygame.draw.rect(s, (84, 96, 62), (4, 18, 84, 24), border_radius=3)
            pygame.draw.rect(s, (110, 124, 82), (4, 18, 84, 4))
            pygame.draw.polygon(s, (84, 96, 62), [(4, 18), (14, 6), (30, 6), (30, 18)])
            pygame.draw.polygon(s, (150, 200, 230), [(10, 16), (16, 9), (26, 9), (26, 16)])
            pygame.draw.rect(s, (60, 70, 46), (40, 6, 34, 12), border_radius=3)
            pygame.draw.rect(s, (110, 124, 82), (44, 8, 26, 3))
            pygame.draw.line(s, (40, 40, 48), (44, 10), (24, 2), 5)
            pygame.draw.line(s, (150, 154, 166), (44, 9), (24, 1), 2)
            for x in range(34, 86, 8):
                pygame.draw.line(s, (60, 70, 46), (x, 24), (x, 38))
            for x in (16, 50, 74):
                pygame.draw.circle(s, (28, 28, 34), (x, 42), 8)
                pygame.draw.circle(s, (120, 120, 130), (x, 42), 3)
        return _veh("b_truck", d, (92, 52))
    if kind == "jet":
        def d(s):
            pygame.draw.polygon(s, (176, 182, 194), [(0, 26), (12, 18), (120, 16), (136, 22), (136, 30), (10, 32)])
            pygame.draw.polygon(s, (210, 214, 224), [(12, 18), (120, 16), (124, 20), (14, 21)])
            pygame.draw.polygon(s, (60, 100, 140), [(10, 20), (24, 15), (34, 15), (30, 21)])
            pygame.draw.polygon(s, (150, 156, 168), [(60, 24), (96, 24), (120, 40), (100, 40)])
            pygame.draw.polygon(s, (150, 156, 168), [(108, 16), (118, 0), (130, 0), (128, 18)])
            pygame.draw.rect(s, (90, 94, 104), (100, 24, 28, 7))
            pygame.draw.circle(s, (40, 40, 48), (128, 27), 3)
            pygame.draw.rect(s, (200, 40, 40), (114, 4, 8, 4))
            for x in (20, 90):
                pygame.draw.line(s, (60, 60, 68), (x, 32), (x, 40), 2)
                pygame.draw.circle(s, (28, 28, 34), (x, 41), 3)
            pygame.draw.circle(s, (40, 40, 48), (8, 28), 3)
        return _veh("b_jet", d, (138, 46))
    if kind == "bunker":
        def d(s):
            pygame.draw.polygon(s, (150, 168, 196), [(0, 76), (6, 20), (40, 2), (80, 12), (96, 76)])
            pygame.draw.rect(s, (130, 132, 140), (8, 22, 80, 54))
            for y in range(26, 76, 10):
                pygame.draw.line(s, (100, 102, 112), (8, y), (88, y))
            pygame.draw.rect(s, (160, 162, 170), (8, 22, 80, 4))
            pygame.draw.polygon(s, (240, 244, 252), [(2, 22), (40, 4), (82, 14), (92, 22), (60, 26), (30, 24)])
            pygame.draw.rect(s, (70, 60, 52), (40, 56, 18, 20))
        return _veh("b_bunker", d, (98, 78))
    def d(s):              # gunboat
        pygame.draw.polygon(s, (70, 74, 86), [(0, 26), (120, 26), (108, 44), (10, 44)])
        pygame.draw.polygon(s, (110, 116, 130), [(0, 26), (120, 26), (118, 30), (2, 30)])
        pygame.draw.rect(s, (96, 100, 114), (40, 10, 42, 17))
        pygame.draw.rect(s, (150, 200, 230), (44, 14, 34, 4))
        pygame.draw.rect(s, (80, 84, 96), (54, 0, 6, 10))
        pygame.draw.rect(s, (60, 64, 74), (14, 18, 14, 9), border_radius=3)
        pygame.draw.line(s, (40, 40, 48), (18, 20), (2, 10), 5)
        pygame.draw.line(s, (150, 154, 166), (18, 19), (2, 9), 2)
        pygame.draw.rect(s, (200, 40, 40), (96, 18, 8, 9))
        for x in range(14, 110, 12):
            pygame.draw.circle(s, (150, 160, 170), (x, 36), 2)
    return _veh("b_gunboat", d, (122, 46))


def spymaster():
    def d(s):
        pygame.draw.rect(s, (32, 32, 40), (1, 7, 9, 10))
        pygame.draw.rect(s, (246, 198, 158), (2, 1, 7, 6))
        pygame.draw.rect(s, (26, 22, 30), (2, 3, 7, 2))
        pygame.draw.rect(s, (44, 32, 30), (1, 0, 9, 2))
        pygame.draw.rect(s, (240, 240, 240), (4, 7, 3, 4))
        pygame.draw.rect(s, (200, 30, 40), (5, 8, 1, 3))
    return _veh("spymaster", d, (11, 17))


# ---------------------------------------------------------------- terrain kits
def deck_top(width, seed):
    s = pygame.Surface((width, 10), pygame.SRCALPHA)
    pygame.draw.rect(s, (84, 88, 96), (0, 0, width, 10))
    pygame.draw.line(s, (150, 154, 162), (0, 0), (width, 0))
    for x in range(0, width, 36):
        pygame.draw.rect(s, (236, 206, 70), (x, 4, 18, 2))
    for x in range(0, width, 9):
        s.set_at((x, 8), (60, 62, 70))
    return s


def dirt_top(width, seed):
    s = pygame.Surface((width, 10), pygame.SRCALPHA)
    rng = random.Random(seed)
    pygame.draw.rect(s, (150, 120, 80), (0, 0, width, 10))
    pygame.draw.line(s, (196, 168, 120), (0, 0), (width, 0))
    for _ in range(width // 3):
        s.set_at((rng.randrange(width), rng.randrange(2, 10)), rng.choice(((120, 96, 64), (176, 146, 100))))
    for x in range(0, width, 22):
        pygame.draw.line(s, (110, 84, 56), (x, 5), (x + 6, 5))
    return s


def tarmac_top(width, seed):
    s = pygame.Surface((width, 10), pygame.SRCALPHA)
    pygame.draw.rect(s, (70, 72, 80), (0, 0, width, 10))
    pygame.draw.line(s, (130, 132, 140), (0, 0), (width, 0))
    for x in range(0, width, 40):
        pygame.draw.rect(s, (240, 240, 240), (x, 4, 20, 2))
    return s


def sand_top(width, seed):
    s = pygame.Surface((width, 10), pygame.SRCALPHA)
    rng = random.Random(seed)
    pygame.draw.rect(s, (226, 200, 140), (0, 0, width, 10))
    pygame.draw.line(s, (250, 230, 180), (0, 0), (width, 0))
    for _ in range(width // 4):
        s.set_at((rng.randrange(width), rng.randrange(1, 10)), (196, 170, 112))
    return s


def clouds(width, height, seed, n=6, col=(250, 250, 255), shadow=(200, 214, 236)):
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    rng = random.Random(seed)
    for i in range(n):
        x = i * width // n + rng.randint(0, 30)
        y = rng.randint(4, height - 20)
        k = rng.randint(3, 5)
        for j in range(k):
            r = rng.randint(6, 11)
            pygame.draw.circle(s, shadow, (x + j * 9, y + 4), r)
        for j in range(k):
            r = rng.randint(5, 9)
            pygame.draw.circle(s, col, (x + j * 9, y), r)
    return s


THEME_KIT = {
    "carrier": {"sky": ((96, 160, 226), (196, 226, 248)), "ground_top": deck_top, "ground_fill": ("hull", (110, 116, 128)),
                "ledge_top": px.hazard_top, "ledge_fill": ("hull", (128, 134, 148))},
    "base": {"sky": ((236, 110, 70), (252, 206, 130)), "ground_top": dirt_top, "ground_fill": ("rock", (140, 110, 80)),
             "ledge_top": px.sandbag_top, "ledge_fill": ("blocks", (150, 146, 136))},
    "airfield": {"sky": ((70, 140, 220), (186, 220, 246)), "ground_top": tarmac_top, "ground_fill": ("blocks", (90, 92, 100)),
                 "ledge_top": px.grate_top, "ledge_fill": ("crates", None)},
    "snow": {"sky": ((110, 130, 176), (210, 222, 242)), "ground_top": px.snow_top, "ground_fill": ("rock", (150, 170, 204)),
             "ledge_top": px.snow_top, "ledge_fill": ("rock", (132, 152, 190))},
    "island": {"sky": ((246, 120, 80), (255, 214, 140)), "ground_top": px.grass_top, "ground_fill": ("rock", (138, 144, 156)),
               "ledge_top": px.grass_top, "ledge_fill": ("rock", (146, 152, 166))},
}


def _fill(spec, size, seed):
    kind, col = spec
    if kind == "hull":
        return px.hull_plates(size, col, seed)
    if kind == "rock":
        return px.boulders(size, col, seed, count=14)
    if kind == "blocks":
        return px.blocks(size, col, seed)
    return px.corrugated(size, seed)


def kit(theme):
    key = ("kit", theme)
    if key in _cache:
        return _cache[key]
    t = THEME_KIT[theme]
    k = {"sky": px.sky((W, H), *t["sky"]),
         "gtop": t["ground_top"](256, 11), "gfill": _fill(t["ground_fill"], (128, 64), 12),
         "ltop": t["ledge_top"](256, 13), "lfill": _fill(t["ledge_fill"], (128, 96), 14), "layers": []}
    L = k["layers"]
    if theme == "carrier":
        L.append((clouds(800, 70, 1), 0.05, 14))
        L.append((px.sea_strip(800, 90, 2), 0.1, 130))
        L.append((px.ships_layer(800, 130, 3), 0.18, 70))
    elif theme == "base":
        L.append((clouds(800, 60, 4, col=(255, 226, 180), shadow=(236, 170, 120)), 0.04, 20))
        L.append((px.mountains(800, 120, (150, 96, 80), None, 5, top=20), 0.1, 70))
        L.append((px.buildings_layer(800, 120, 6, "base"), 0.3, 92))
        L.append((px.fence_layer(800, 40), 0.55, 168))
    elif theme == "airfield":
        L.append((clouds(800, 80, 7), 0.05, 10))
        L.append((px.mountains(800, 100, (110, 136, 170), (230, 238, 250), 8, top=20), 0.1, 80))
        L.append((px.buildings_layer(800, 120, 9, "airfield"), 0.3, 90))
    elif theme == "snow":
        L.append((px.mountains(800, 150, (150, 166, 200), (246, 250, 255), 10, top=10), 0.08, 40))
        L.append((px.mountains(800, 100, (110, 126, 164), (236, 242, 252), 11, peaks=8, top=30), 0.16, 100))
        L.append((px.pines(800, 70, 12, snowy=True), 0.35, 140))
    else:
        L.append((clouds(800, 60, 13, col=(255, 230, 190), shadow=(240, 170, 130)), 0.04, 16))
        L.append((px.sea_strip(800, 60, 14), 0.08, 120))
        L.append((px.jungle_layer(800, 150, 15), 0.4, 60))
    _cache[key] = k
    return k


def _tile(surf, tile, rect, world_x, world_y=0):
    """Fill rect with tile, lined up with the world so the texture scrolls with the camera."""
    tw, th = tile.get_size()
    clip = surf.get_clip()
    surf.set_clip(rect.clip(clip))
    x0 = rect.x - (world_x % tw)
    y0 = rect.y - (world_y % th)
    y = y0
    while y < rect.bottom:
        x = x0
        while x < rect.right:
            surf.blit(tile, (x, y))
            x += tw
        y += th
    surf.set_clip(clip)


def draw_backdrop(surf, theme, cam, t=0.0):
    k = kit(theme)
    surf.blit(k["sky"], (0, 0))
    if theme == "base":
        pygame.draw.circle(surf, (255, 236, 170), (300, 70), 22)
    elif theme == "island":
        pygame.draw.circle(surf, (255, 240, 180), (90, 90), 26)
        pygame.draw.circle(surf, (255, 250, 220), (90, 90), 20)
    for layer, speed, y in k["layers"]:
        lw = layer.get_width()
        x = -int(cam * speed + t * (4 if layer.get_height() < 90 and speed < 0.06 else 0)) % lw
        surf.blit(layer, (x - lw, y))
        surf.blit(layer, (x, y))
    if theme == "snow":
        for i in range(50):
            sx = (i * 47 + int(t * 18) - int(cam * 0.6)) % W
            sy = (i * 29 + int(t * (30 + i % 3 * 12))) % H
            surf.fill((255, 255, 255), (sx, sy, 2 if i % 4 == 0 else 1, 2 if i % 4 == 0 else 1))


def draw_ledge(surf, theme, sx, y, w, cam):
    k = kit(theme)
    top = k["ltop"]
    th = top.get_height()
    rock = pygame.Rect(sx, y + th - 3, w, GROUND - (y + th - 3))
    _tile(surf, k["lfill"], rock, int(cam + sx - (cam % 1)), y)
    pygame.draw.line(surf, OUT, rock.topleft, rock.bottomleft)
    pygame.draw.line(surf, OUT, rock.topright, rock.bottomright)
    shade = _cache.get(("edge", rock.h))
    if shade is None:
        shade = _cache[("edge", rock.h)] = pygame.Surface((4, max(1, rock.h)), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 70))
    surf.blit(shade, (rock.right - 4, rock.y))
    _tile(surf, top, pygame.Rect(sx, y - 2, w, th), int(cam + sx))


def draw_ground(surf, theme, cam):
    k = kit(theme)
    top = k["gtop"]
    _tile(surf, k["gfill"], pygame.Rect(0, GROUND + top.get_height() - 3, W, H), int(cam), GROUND)
    _tile(surf, top, pygame.Rect(0, GROUND - 2, W, top.get_height()), int(cam))


# ---------------------------------------------------------------- story scenes
def _soldier(surf, kind, x, feet, pose="stand", aim="fwd", face=1, scale=1, dark=False):
    s, ax = figure(kind, pose, aim, face)
    if scale != 1:
        s = pygame.transform.scale(s, (s.get_width() * scale, s.get_height() * scale))
        ax *= scale
    if dark:
        s = s.copy()
        s.fill((90, 90, 110), special_flags=pygame.BLEND_RGB_MULT)
    surf.blit(s, (int(x - ax), int(feet - s.get_height())))
    return s


def muzzle(surf, x, y, t):
    if int(t * 16) % 2 == 0:
        pygame.draw.circle(surf, (255, 240, 150), (int(x), int(y)), 4)
        pygame.draw.circle(surf, (255, 255, 255), (int(x), int(y)), 2)


def scene_select(surf, t, choice, heroes, start_level, unlocked, two):
    draw_backdrop(surf, "island", t * 12, t)
    shade = pygame.Surface((W, H), pygame.SRCALPHA)
    shade.fill((10, 10, 30, 90))
    surf.blit(shade, (0, 0))
    say(surf, "CHOOSE YOUR OPERATOR", (W // 2, 6), 28, (255, 220, 80))
    for i, who in enumerate(("miles", "felix")):
        cx = 110 + i * 180
        sel = who == choice
        base = 170
        if sel:          # searchlight behind the chosen hero
            beam = pygame.Surface((120, 150), pygame.SRCALPHA)
            pygame.draw.polygon(beam, (255, 250, 200, 60), [(50, 0), (70, 0), (120, 150), (0, 150)])
            surf.blit(beam, (cx - 60, base - 150))
        draw_ledge(surf, "island", cx - 56, base, 112, 0)
        aim = "dup" if sel else "fwd"
        s = _soldier(surf, who, cx, base, "stand", aim, 1 if i == 0 else -1, scale=3, dark=not sel)
        if sel:
            f = 1 if i == 0 else -1
            muzzle(surf, cx + f * 3 * 14, base - s.get_height() + 6 * 3, t)
        hero = heroes[who]
        plate = pygame.Rect(cx - 74, 182, 148, 30)
        pygame.draw.rect(surf, (20, 24, 30), plate, border_radius=4)
        pygame.draw.rect(surf, (255, 220, 80) if sel else (90, 96, 110), plate, 2, border_radius=4)
        say(surf, hero["name"].upper(), (cx, 184), 22, (255, 255, 255) if sel else (150, 150, 160))
        say(surf, hero["unit"], (cx, 200), 14, (190, 230, 190) if sel else (120, 130, 120))
    mission = ("MISSION %d of %d  (up / down)" % (start_level, unlocked)) if unlocked > 1 else "MISSION 1"
    say(surf, mission, (W // 2, 214), 16, (190, 220, 255))
    p2 = "PLAYER 2 READY!" if two else "Player 2: press A on the second gamepad"
    if two or int(t * 2) % 2 == 0:
        say(surf, p2, (W // 2, 227), 14, (255, 200, 120))


def _desk(surf):
    if "desk" not in _cache:
        s = pygame.Surface((W, H))
        s.fill((86, 54, 36))
        rng = random.Random(5)
        for y in range(0, H, 3):
            pygame.draw.line(s, (96 + rng.randint(-8, 8), 62, 40), (0, y), (W, y + rng.randint(-1, 1)))
        for _ in range(30):
            x, y = rng.randrange(W), rng.randrange(H)
            pygame.draw.arc(s, (70, 42, 28), (x, y, 30, 8), 0, 3.1)
        lamp = pygame.Surface((W, H), pygame.SRCALPHA)
        for r in range(180, 0, -20):
            pygame.draw.circle(lamp, (255, 220, 150, 10), (140, 80), r)
        s.blit(lamp, (0, 0))
        _cache["desk"] = s
    surf.blit(_cache["desk"], (0, 0))


MISSION_ICONS = ((14, 94), (50, 80), (84, 60), (66, 28), (116, 18))


def _mission_map(surf, rect, level, t):
    pygame.draw.rect(surf, (40, 30, 24), rect.move(3, 3))
    pygame.draw.rect(surf, (60, 120, 180), rect)
    rng = random.Random(9)
    for _ in range(40):
        x = rng.randrange(rect.x + 2, rect.right - 8)
        y = rng.randrange(rect.y + 2, rect.bottom - 2)
        pygame.draw.line(surf, (110, 170, 220), (x, y), (x + 5, y))
    land = [(rect.x + 70, rect.y + 70, 50, 30), (rect.x + 104, rect.y + 34, 46, 34), (rect.x + 120, rect.y + 6, 30, 20)]
    for lx, ly, lw, lh in land:
        pygame.draw.ellipse(surf, (196, 176, 120), (lx - 2, ly - 2, lw + 4, lh + 4))
        pygame.draw.ellipse(surf, (90, 150, 80), (lx, ly, lw, lh))
    pts = [(rect.x + x, rect.y + y) for x, y in MISSION_ICONS]
    for a, b in zip(pts, pts[1:]):
        n = int(math.hypot(b[0] - a[0], b[1] - a[1]) // 5)
        for i in range(0, n, 2):
            u = i / max(1, n)
            surf.fill((250, 250, 250), (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, 2, 2))
    for i, (x, y) in enumerate(pts):
        done = i < level
        cur = i == level
        r = 6 if cur else 4
        col = (90, 200, 90) if done else ((230, 50, 40) if cur and int(t * 4) % 2 == 0 else (250, 250, 250))
        pygame.draw.circle(surf, OUT, (x, y), r + 1)
        pygame.draw.circle(surf, col, (x, y), r)
        say(surf, str(i + 1), (x, y - 17), 14, (255, 255, 255))
    pygame.draw.rect(surf, (230, 220, 190), rect, 3)


def scene_briefing(surf, t, players, level, lines):
    _desk(surf)
    paper = pygame.Rect(16, 14, 228, 210)
    pygame.draw.rect(surf, (40, 26, 18), paper.move(4, 4))
    pygame.draw.rect(surf, (214, 170, 96), paper.inflate(10, 6))          # folder
    pygame.draw.rect(surf, (240, 232, 210), paper)
    for y in range(paper.y + 30, paper.bottom - 4, 15):
        pygame.draw.line(surf, (200, 210, 226), (paper.x + 6, y), (paper.right - 6, y))
    stamp = pygame.Surface((96, 22), pygame.SRCALPHA)
    pygame.draw.rect(stamp, (200, 40, 40), (0, 0, 96, 22), 2)
    img = font(20).render("TOP SECRET", False, (200, 40, 40))
    stamp.blit(img, (48 - img.get_width() // 2, 4))
    surf.blit(pygame.transform.rotate(stamp, 8), (150, 2))
    shown = int(t * 45)
    y = paper.y + 18
    for line in lines:
        part = line[:max(0, shown)]
        shown -= len(line)
        size = 20 if line == "ORDERS" else 15
        plain(surf, part, (paper.x + 10, y), size, (30, 30, 40))
        y += 15 if line else 8
    _mission_map(surf, pygame.Rect(256, 20, 136, 110), level, t)
    photo = pygame.Rect(270, 142, 64, 72)       # the spymaster's photo, clipped on
    pygame.draw.rect(surf, (30, 24, 20), photo.move(3, 3))
    pygame.draw.rect(surf, (250, 250, 246), photo)
    inner = photo.inflate(-8, -16).move(0, -4)
    pygame.draw.rect(surf, (90, 100, 120), inner)
    pygame.draw.ellipse(surf, (24, 24, 30), (inner.centerx - 18, inner.bottom - 22, 36, 30))
    pygame.draw.rect(surf, (230, 186, 150), (inner.centerx - 8, inner.y + 10, 16, 18))
    pygame.draw.rect(surf, (20, 20, 26), (inner.centerx - 9, inner.y + 15, 18, 5))
    pygame.draw.rect(surf, (40, 30, 30), (inner.centerx - 9, inner.y + 6, 18, 6))
    pygame.draw.rect(surf, (240, 240, 240), (inner.centerx - 3, inner.bottom - 16, 6, 10))
    pygame.draw.rect(surf, (200, 30, 40), (inner.centerx - 1, inner.bottom - 15, 2, 8))
    say(surf, "THE SPYMASTER", (photo.centerx, photo.bottom - 12), 12, (30, 30, 40), outline=(250, 250, 246))
    pygame.draw.rect(surf, (170, 174, 186), (photo.centerx - 4, photo.y - 5, 8, 12), 2)
    for i, p in enumerate(players):
        _soldier(surf, p["who"], 352 + i * 22, 222, "stand", "up" if t > 1.0 else "fwd", -1)
    if t > 1.0 and int(t * 2) % 2 == 0:
        say(surf, "BIG BUTTON: ACCEPT YOUR ORDERS", (W // 2, 226), 18, (255, 230, 90))


def cargo_plane(surf, x, y, t, ramp):
    if "plane" not in _cache:
        s = pygame.Surface((230, 90), pygame.SRCALPHA)
        body = (110, 122, 104)
        dark = (80, 90, 76)
        pygame.draw.polygon(s, body, [(10, 40), (30, 30), (200, 30), (224, 42), (224, 54), (200, 66), (40, 66), (20, 56)])
        pygame.draw.polygon(s, (140, 154, 132), [(30, 30), (200, 30), (210, 35), (32, 35)])
        pygame.draw.polygon(s, dark, [(40, 60), (200, 60), (200, 66), (40, 66)])
        pygame.draw.polygon(s, (150, 200, 230), [(206, 38), (218, 42), (218, 46), (206, 44)])
        for wx in range(70, 190, 14):
            pygame.draw.circle(s, (60, 70, 60), (wx, 42), 2)
        pygame.draw.polygon(s, body, [(16, 40), (0, 4), (16, 4), (44, 32)])
        pygame.draw.polygon(s, dark, [(2, 6), (14, 6), (16, 12), (6, 12)])
        pygame.draw.polygon(s, body, [(0, 34), (36, 30), (36, 36)])
        pygame.draw.rect(s, (210, 210, 220), (120, 40, 14, 14))       # original roundel: a white star in a ring
        pygame.draw.circle(s, (40, 70, 140), (127, 47), 9)
        star = [(127 + math.cos(math.radians(-90 + i * 36)) * (7 if i % 2 == 0 else 3),
                 47 + math.sin(math.radians(-90 + i * 36)) * (7 if i % 2 == 0 else 3)) for i in range(10)]
        pygame.draw.polygon(s, (250, 250, 250), star)
        pygame.draw.polygon(s, (126, 138, 118), [(90, 30), (170, 30), (160, 24), (96, 24)])     # high wing
        for ex in (106, 146):
            pygame.draw.rect(s, dark, (ex, 22, 18, 9), border_radius=3)
            pygame.draw.rect(s, (150, 154, 166), (ex + 15, 24, 4, 5))
        _cache["plane"] = outlined(s)
    s = _cache["plane"]
    surf.blit(s, (int(x), int(y)))
    for ex in (106, 146):       # spinning propellers
        bx, by = int(x) + ex + 21, int(y) + 27
        h = int(abs(math.sin(t * 40)) * 10) + 2
        pygame.draw.ellipse(surf, (200, 204, 214), (bx - 1, by - h, 3, h * 2))
    if ramp > 0:
        rx, ry = int(x) + 24, int(y) + 58
        end = (rx - 26 * ramp, ry + 18 * ramp)
        pygame.draw.polygon(surf, (70, 80, 66), [(rx, ry), (rx + 22, ry + 2), end, (end[0] - 4, end[1] - 4)])
        pygame.draw.line(surf, OUT, (rx, ry), end, 1)
        light = (90, 230, 90) if ramp >= 1 else (240, 60, 50)
        pygame.draw.circle(surf, light, (rx + 16, ry - 6), 2)


def scene_plane(surf, t, theme, level, name, players):
    k = kit(theme)
    surf.blit(k["sky"], (0, 0))
    far = k["layers"][1][0] if len(k["layers"]) > 1 else k["layers"][0][0]
    lw = far.get_width()
    x = -int(t * 30) % lw
    surf.blit(far, (x - lw, 150))
    surf.blit(far, (x, 150))
    for depth, speed, y, n in ((0, 80, 20, 5), (1, 260, 120, 4)):
        cl = _cache.get(("cl", depth))
        if cl is None:
            cl = _cache[("cl", depth)] = clouds(800, 80, 30 + depth, n=n)
        cx = -int(t * speed) % 800
        surf.blit(cl, (cx - 800, y))
        surf.blit(cl, (cx, y))
    bob = math.sin(t * 2.2) * 3
    px_, py_ = 120 + math.sin(t * 0.7) * 8, 40 + bob
    ramp = max(0.0, min(1.0, (t - 0.6) / 0.6))
    cargo_plane(surf, px_, py_, t, ramp)
    for i, p in enumerate(players):
        jt = t - 1.5 - i * 0.35
        if jt <= 0:
            continue
        jx = px_ + 24 - jt * 70
        jy = py_ + 60 + jt * jt * 40 + jt * 30
        if jt > 0.7:
            c = chute()
            surf.blit(c, (int(jx - c.get_width() // 2), int(jy - 50)))
            _soldier(surf, p["who"], jx, jy, "fall", "fwd", 1)
        else:
            s = tuck(p["who"], int(jt * 12))
            surf.blit(s, (int(jx - 7), int(jy - 15)))
    card = pygame.Rect(40, 178, W - 80, 50)
    pygame.draw.rect(surf, (16, 18, 24), card, border_radius=4)
    pygame.draw.rect(surf, (255, 220, 80), card, 2, border_radius=4)
    say(surf, "MISSION %d" % (level + 1), (W // 2, card.y + 4), 26, (255, 220, 80))
    say(surf, name.upper(), (W // 2, card.y + 28), 20, (255, 255, 255))


def scene_victory(surf, t, players):
    draw_backdrop(surf, "island", 0, t)
    draw_ground(surf, "island", 0)
    pygame.draw.rect(surf, (40, 110, 170), (0, 216, W, 24))
    for i in range(30):             # fireworks
        ft = (t * 0.6 + i * 0.37) % 2.0
        cx = 40 + (i * 71) % 320
        cy = 30 + (i * 37) % 70
        col = ((255, 220, 80), (120, 220, 255), (255, 120, 160), (140, 255, 140))[i % 4]
        if ft < 1.2:
            r = ft * 30
            for a in range(0, 360, 30):
                xx = cx + math.cos(math.radians(a + i * 7)) * r
                yy = cy + math.sin(math.radians(a + i * 7)) * r + ft * ft * 8
                surf.fill(col, (int(xx), int(yy), 2, 2))
    hx, hy = 300 + math.sin(t) * 6, 40 + math.sin(t * 1.7) * 4     # extraction helicopter
    heli = boss_sprite("heli", t, 1.0)
    heli = pygame.transform.flip(heli, True, False)
    heli = heli.copy()
    heli.fill((150, 170, 150), special_flags=pygame.BLEND_RGB_MULT)
    surf.blit(heli, (int(hx - 50), int(hy)))
    for k in range(int(hy + 46), 160, 4):
        pygame.draw.line(surf, (200, 180, 120), (int(hx) - 4, k), (int(hx) + 4, k))
    pygame.draw.line(surf, (150, 130, 90), (int(hx) - 4, int(hy) + 46), (int(hx) - 4, 160))
    pygame.draw.line(surf, (150, 130, 90), (int(hx) + 4, int(hy) + 46), (int(hx) + 4, 160))
    glow = 6 + int(abs(math.sin(t * 3)) * 4)
    pygame.draw.circle(surf, (255, 240, 150), (200, 186), glow + 6)
    pygame.draw.rect(surf, (230, 180, 40), (192, 178, 16, 12))
    pygame.draw.rect(surf, (255, 230, 120), (194, 180, 12, 3))
    pygame.draw.line(surf, OUT, (200, 178), (200, 190))
    for i, p in enumerate(players):
        x = 160 - i * 30 if i else 240
        _soldier(surf, p["who"], x, GROUND, "stand", "up", -1 if x > 200 else 1)
        muzzle(surf, x + (2 if x < 200 else -2) + (4 if x < 200 else -4), GROUND - p["hero"]["height"] - 12, t + i)
    say(surf, "MISSION ACCOMPLISHED", (W // 2, 112), 30, (255, 220, 80))
    say(surf, "The Golden Codebook is safe. Everyone comes home.", (W // 2, 140), 16, (255, 255, 255))
