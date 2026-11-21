"""Art for Alien Storm: Tom Cat Alley. Everything is drawn in code, at four times size,
then smoothed down once into cached sprites, so edges are clean and drawing costs nothing in play."""
import math
import random

import pygame

SS = 4                                  # supersampling factor
_cache = {}
_OX = 0.0                               # horizontal drawing offset, for layers wider than the frame


def _canvas(w, h):
    return pygame.Surface((w * SS, h * SS), pygame.SRCALPHA)


def _down(s):
    return pygame.transform.smoothscale(s, (s.get_width() // SS, s.get_height() // SS))


def _p(pts, ox=0.0, oy=0.0, mirror=None):
    out = [((x + ox) * SS, (y + oy) * SS) for x, y in pts]
    if mirror is not None:
        out = [((2 * mirror - x - ox) * SS + 0 * ox, (y + oy) * SS) for x, y in pts]
    return out


def poly(s, col, pts, mirror=None):
    pts = [(x + _OX, y) for x, y in pts]
    mirror = None if mirror is None else mirror + _OX
    pygame.draw.polygon(s, col, [(x * SS, y * SS) for x, y in pts])
    if mirror is not None:
        pygame.draw.polygon(s, col, [((2 * mirror - x) * SS, y * SS) for x, y in pts])


def line(s, col, a, b, w=1.0, mirror=None):
    a, b = (a[0] + _OX, a[1]), (b[0] + _OX, b[1])
    mirror = None if mirror is None else mirror + _OX
    pygame.draw.line(s, col, (a[0] * SS, a[1] * SS), (b[0] * SS, b[1] * SS), max(1, int(w * SS)))
    if mirror is not None:
        pygame.draw.line(s, col, ((2 * mirror - a[0]) * SS, a[1] * SS), ((2 * mirror - b[0]) * SS, b[1] * SS), max(1, int(w * SS)))


def oval(s, col, rect, mirror=None):
    x, y, w, h = rect
    x += _OX
    mirror = None if mirror is None else mirror + _OX
    pygame.draw.ellipse(s, col, (x * SS, y * SS, w * SS, h * SS))
    if mirror is not None:
        pygame.draw.ellipse(s, col, ((2 * mirror - x - w) * SS, y * SS, w * SS, h * SS))


def _rot(pts, pivot, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    px, py = pivot
    return [(px + (x - px) * ca - (y - py) * sa, py + (x - px) * sa + (y - py) * ca) for x, y in pts]


# ------------------------------------------------------------------ F-14 Tomcat
NAVY = dict(top=(142, 150, 160), hi=(176, 184, 194), sh=(98, 106, 118), dark=(58, 64, 76), line=(74, 80, 92),
            glass=(236, 190, 90), glass_hi=(255, 236, 170), nozzle=(54, 50, 56))
SQUADRONS = {1: ((214, 40, 50), (250, 220, 90)), 2: ((40, 90, 200), (255, 255, 255))}


def tomcat(sweep=1.0, squadron=1, missiles=4, burner=0.5, damage=0.0, crew=((90, 60, 40), (60, 40, 28))):
    """An F-14 seen from above, nose up, 56 x 72. sweep 0 = wings spread, 1 = swept back."""
    key = ("tomcat", round(sweep, 1), squadron, missiles, round(burner, 1), round(damage, 1), crew)
    if key in _cache:
        return _cache[key]
    W, H, cx = 56, 72, 28.0
    s = _canvas(W, H)
    c = NAVY
    trim, trim2 = SQUADRONS[squadron]
    # afterburners (behind everything)
    for ex in (cx - 6.2, cx + 6.2):
        L = 4 + 12 * burner
        poly(s, (255, 150, 40), [(ex - 2.4, 62), (ex + 2.4, 62), (ex, 62 + L)])
        poly(s, (255, 236, 150), [(ex - 1.3, 62), (ex + 1.3, 62), (ex, 62 + L * 0.6)])
        if burner > 0.6:
            poly(s, (150, 200, 255), [(ex - 0.8, 62), (ex + 0.8, 62), (ex, 62 + L * 0.3)])
    # horizontal stabilators
    poly(s, c["sh"], [(cx - 6, 54), (cx - 18, 63), (cx - 17, 67), (cx - 6, 64)], mirror=cx)
    # variable sweep wings: pivot in the glove, 20 degrees spread to 68 swept
    wing = [(cx - 9, 31), (cx - 27.5, 34), (cx - 27.5, 39), (cx - 9, 43)]
    wing = _rot(wing, (cx - 9, 36), -48 * sweep)
    poly(s, c["top"], wing, mirror=cx)
    poly(s, c["hi"], [wing[0], wing[1], ((wing[1][0] + wing[2][0]) / 2, (wing[1][1] + wing[2][1]) / 2),
                      ((wing[0][0] + wing[3][0]) / 2, (wing[0][1] + wing[3][1]) / 2)], mirror=cx)
    line(s, c["line"], wing[2], wing[3], 0.5, mirror=cx)
    # missiles under the gloves and tunnel: they vanish as they are fired
    slots = [(cx - 12.5, 34), (cx + 12.5, 34), (cx - 2.2, 44), (cx + 2.2, 44)]
    for i, (mx, my) in enumerate(slots[:missiles]):
        poly(s, (236, 236, 240), [(mx - 0.7, my), (mx + 0.7, my), (mx + 0.7, my + 8), (mx - 0.7, my + 8)])
        poly(s, (200, 60, 60), [(mx - 0.7, my), (mx + 0.7, my), (mx, my - 1.6)])
    # wing gloves and the wide body ("pancake") with the tunnel between the engines
    poly(s, c["top"], [(cx - 3.5, 20), (cx - 11, 29), (cx - 11.5, 46), (cx - 9.5, 62), (cx - 3, 62), (cx - 2, 50), (cx, 48)], mirror=cx)
    poly(s, c["sh"], [(cx - 2, 50), (cx - 3, 62), (cx + 3, 62), (cx + 2, 50), (cx, 48)])          # tunnel in shadow
    poly(s, c["hi"], [(cx - 4, 22), (cx - 10.5, 29.5), (cx - 10.5, 36), (cx - 6, 30)], mirror=cx)
    # intakes
    poly(s, c["dark"], [(cx - 9.6, 27), (cx - 6.2, 25.5), (cx - 6.2, 28.5), (cx - 9.6, 30)], mirror=cx)
    # engine nacelles and nozzles, widely spaced
    poly(s, c["top"], [(cx - 9.2, 44), (cx - 3.4, 44), (cx - 3.6, 60), (cx - 8.8, 60)], mirror=cx)
    line(s, c["hi"], (cx - 6.3, 45), (cx - 6.3, 58), 0.6, mirror=cx)
    oval(s, c["nozzle"], (cx - 8.8, 58.5, 5.2, 4.2), mirror=cx)
    oval(s, (255, 170, 60) if burner > 0.3 else (90, 80, 84), (cx - 7.6, 59.6, 2.8, 2.2), mirror=cx)
    # long nose and forward fuselage
    poly(s, c["top"], [(cx, 1), (cx - 1.6, 6), (cx - 3.2, 14), (cx - 3.8, 30), (cx, 34)], mirror=cx)
    poly(s, c["hi"], [(cx, 1), (cx - 1.0, 6), (cx - 1.2, 28), (cx, 30)])
    poly(s, c["dark"], [(cx, 1), (cx - 1.1, 5), (cx + 1.1, 5)])                                    # radome
    # the Vulcan cannon port, left side of the forward fuselage
    line(s, c["nozzle"], (cx - 3.0, 12.5), (cx - 3.3, 16.5), 0.8)
    # tandem canopy with both crew visible
    poly(s, (40, 44, 52), [(cx, 9.5), (cx - 2.4, 13), (cx - 2.6, 24), (cx, 26.5), (cx + 2.6, 24), (cx + 2.4, 13)])
    poly(s, c["glass"], [(cx, 10.5), (cx - 1.8, 13.5), (cx - 2.0, 23.5), (cx, 25.5), (cx + 2.0, 23.5), (cx + 1.8, 13.5)])
    poly(s, c["glass_hi"], [(cx - 0.2, 11), (cx - 1.5, 13.6), (cx - 1.6, 20), (cx - 0.6, 20)])
    for (hy, col) in ((14.2, crew[0]), (20.0, crew[1])):                                           # two helmets
        oval(s, (236, 236, 240), (cx - 1.5, hy, 3.0, 3.2))
        oval(s, col, (cx - 0.9, hy + 1.9, 1.8, 1.2))
    line(s, (40, 44, 52), (cx - 2.1, 18.2), (cx + 2.1, 18.2), 0.5)
    # twin vertical tails, canted outwards, with squadron art
    for sgn in (-1, 1):
        base = cx + sgn * 6.3
        poly(s, c["sh"], [(base - 0.9, 49), (base + 0.9, 49), (base + sgn * 2.2 + 0.9, 60), (base + sgn * 2.2 - 0.9, 60)])
        poly(s, trim, [(base - 0.9, 49), (base + 0.9, 49), (base + sgn * 0.7 + 0.9, 52.5), (base + sgn * 0.7 - 0.9, 52.5)])
        poly(s, trim2, [(base + sgn * 0.8 - 0.9, 53), (base + sgn * 0.8 + 0.9, 53), (base + sgn * 1.1 + 0.9, 54.4), (base + sgn * 1.1 - 0.9, 54.4)])
    # national insignia and panel lines
    oval(s, (60, 80, 150), (cx - 15.5 + 9 * sweep, 36.5 + 3 * sweep, 3, 3))
    oval(s, (240, 240, 244), (cx - 14.9 + 9 * sweep, 37.1 + 3 * sweep, 1.8, 1.8))
    line(s, c["line"], (cx - 3.8, 30), (cx - 11.2, 30), 0.4, mirror=cx)
    if damage > 0:                                                                                  # scorch and holes
        rng = random.Random(7)
        for k in range(int(3 + 9 * damage)):
            x, y = cx + rng.uniform(-10, 10), rng.uniform(22, 58)
            oval(s, (40, 36, 40), (x, y, rng.uniform(1.5, 3.5), rng.uniform(1.2, 2.6)))
    out = _cache[key] = _down(s)
    return out


# ------------------------------------------------------------------ the aliens
AL = dict(body=(18, 22, 34), hi=(40, 60, 110), edge=(70, 130, 230), glow=(120, 200, 255), star=(255, 50, 50), star_hi=(255, 170, 150))


def _star(s, x, y, r):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.42
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    oval(s, (255, 60, 60, 70), (x - r * 1.5, y - r * 1.5, r * 3, r * 3))
    poly(s, AL["star"], pts)
    oval(s, AL["star_hi"], (x - r * 0.25, y - r * 0.25, r * 0.5, r * 0.5))


def alien(kind):
    """Sleek black and blue craft with a glowing red star, seen from above, nose down (they fly at us)."""
    if ("alien", kind) in _cache:
        return _cache[("alien", kind)]
    if kind == "fighter":                      # a blade
        W, H, cx = 26, 34, 13.0
        s = _canvas(W, H)
        oval(s, (120, 200, 255, 120), (cx - 3, -2, 6, 8))
        poly(s, AL["glow"], [(cx - 1.4, 0), (cx + 1.4, 0), (cx, 5)])
        poly(s, AL["body"], [(cx, 34), (cx - 2.2, 20), (cx - 12, 6), (cx - 4, 8), (cx - 2, 2), (cx, 4)], mirror=cx)
        poly(s, AL["hi"], [(cx, 32), (cx - 1.4, 20), (cx - 3, 9), (cx, 7)])
        line(s, AL["edge"], (cx - 12, 6), (cx - 2.2, 20), 0.6, mirror=cx)
        line(s, AL["edge"], (cx - 2.2, 20), (cx, 34), 0.5, mirror=cx)
        _star(s, cx, 14, 2.6)
    elif kind == "interceptor":                # a forward swept dart
        W, H, cx = 30, 30, 15.0
        s = _canvas(W, H)
        for ex in (cx - 4, cx + 4):
            poly(s, AL["glow"], [(ex - 1.2, 0), (ex + 1.2, 0), (ex, 5)])
        poly(s, AL["body"], [(cx, 30), (cx - 3, 18), (cx - 14, 24), (cx - 9, 10), (cx - 5, 2), (cx, 6)], mirror=cx)
        poly(s, AL["hi"], [(cx, 28), (cx - 2, 16), (cx - 4, 6), (cx, 8)])
        line(s, AL["edge"], (cx - 14, 24), (cx - 9, 10), 0.6, mirror=cx)
        line(s, AL["edge"], (cx - 14, 24), (cx - 3, 18), 0.6, mirror=cx)
        _star(s, cx, 14, 2.4)
    elif kind == "bomber":                     # a large flying wing
        W, H, cx = 76, 40, 38.0
        s = _canvas(W, H)
        for ex in (cx - 14, cx - 6, cx + 6, cx + 14):
            poly(s, AL["glow"], [(ex - 1.6, 4), (ex + 1.6, 4), (ex, -1 + 0)])
            oval(s, (120, 200, 255, 110), (ex - 3, 0, 6, 7))
        poly(s, AL["body"], [(cx, 40), (cx - 10, 30), (cx - 37, 12), (cx - 30, 7), (cx - 18, 9), (cx - 12, 4), (cx, 8)], mirror=cx)
        poly(s, AL["hi"], [(cx, 37), (cx - 8, 28), (cx - 14, 12), (cx, 11)], mirror=cx)
        line(s, AL["edge"], (cx - 37, 12), (cx - 10, 30), 0.7, mirror=cx)
        line(s, AL["edge"], (cx - 10, 30), (cx, 40), 0.7, mirror=cx)
        for bx in (cx - 22, cx + 22):
            oval(s, (30, 40, 70), (bx - 3, 13, 6, 8))
            oval(s, AL["edge"], (bx - 1.2, 15.5, 2.4, 3))
        _star(s, cx, 20, 4.2)
    else:                                      # gunship: a heavy twin hull
        W, H, cx = 46, 46, 23.0
        s = _canvas(W, H)
        for ex in (cx - 11, cx + 11):
            poly(s, AL["glow"], [(ex - 1.8, 0), (ex + 1.8, 0), (ex, 6)])
        poly(s, AL["body"], [(cx - 11, 46), (cx - 16, 30), (cx - 15, 4), (cx - 7, 4), (cx - 6, 30)], mirror=cx)
        poly(s, AL["body"], [(cx - 7, 12), (cx + 7, 12), (cx + 5, 34), (cx, 40), (cx - 5, 34)])
        poly(s, AL["hi"], [(cx - 11, 42), (cx - 13, 30), (cx - 12, 6), (cx - 10, 6)], mirror=cx)
        line(s, AL["edge"], (cx - 16, 30), (cx - 11, 46), 0.7, mirror=cx)
        line(s, AL["edge"], (cx - 16, 30), (cx - 15, 4), 0.6, mirror=cx)
        oval(s, (255, 90, 90), (cx - 12.2, 38, 2.4, 2.4), mirror=cx)
        _star(s, cx, 22, 3.6)
    out = _cache[("alien", kind)] = _down(s)
    return out


# ------------------------------------------------------------------ Nimitz class carrier
def carrier(length=300):
    """A Nimitz class carrier from above, bow up: angled deck, island to starboard, four catapults,
    four wires, parked aircraft, crew in colored jerseys."""
    if ("carrier", length) in _cache:
        return _cache[("carrier", length)]
    k = length / 300.0
    W, H = int(104 * k), length
    s = pygame.Surface((W * 2, H * 2), pygame.SRCALPHA)       # 2x is plenty at this size

    def P(pts):
        return [(x * k * 2, y * k * 2) for x, y in pts]
    deck, deck_hi, hull = (70, 74, 82), (92, 96, 104), (120, 126, 136)
    outline = [(46, 0), (62, 4), (70, 30), (72, 100), (84, 110), (86, 190), (74, 204), (72, 280), (64, 298), (36, 298),
               (28, 280), (26, 232), (6, 196), (4, 130), (22, 96), (26, 30), (34, 4)]
    pygame.draw.polygon(s, hull, P([(x + (1.5 if x > 50 else -1.5), y + 2) for x, y in outline]))
    pygame.draw.polygon(s, deck, P(outline))
    pygame.draw.polygon(s, deck_hi, P([(30, 100), (68, 100), (68, 280), (32, 280)]))
    pygame.draw.polygon(s, deck, P([(34, 104), (64, 104), (64, 276), (36, 276)]))
    white, yellow = (236, 236, 228), (240, 200, 60)
    # angled landing area, running from the stern off to port
    pygame.draw.lines(s, white, False, P([(60, 292), (16, 130)]), 2)
    pygame.draw.lines(s, white, False, P([(38, 292), (6, 180)]), 2)
    for i in range(9):
        t = i / 9
        a = (49 - 38 * t, 292 - 137 * t)
        b = (49 - 38 * (t + 0.05), 292 - 137 * (t + 0.05))
        pygame.draw.line(s, yellow, *P([a, b]), 2)
    for i in range(4):                                         # four arresting wires
        y = 262 - i * 11
        pygame.draw.line(s, (20, 20, 24), *P([(34 - i * 2.4, y), (58 - i * 2.2, y - 3)]), 2)
    # four catapults: two on the bow, two on the waist, with steam
    for a, b in (((42, 96), (42, 8)), ((56, 96), (58, 10)), ((22, 196), (14, 134)), ((30, 200), (22, 138))):
        pygame.draw.line(s, (40, 42, 48), *P([a, b]), 3)
        pygame.draw.line(s, (150, 154, 160), *P([a, b]), 1)
        for j in range(3):
            t = 0.2 + j * 0.25
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            pygame.draw.circle(s, (240, 240, 240, 110), (int(x * k * 2), int(y * k * 2)), int(3 * k * 2))
    for jx, jy in ((42, 100), (56, 100)):                      # jet blast deflectors
        pygame.draw.rect(s, (50, 52, 60), (int((jx - 4) * k * 2), int(jy * k * 2), int(8 * k * 2), int(3 * k * 2)))
    pygame.draw.line(s, white, *P([(49, 6), (49, 94)]), 1)
    # island superstructure on the starboard side
    pygame.draw.rect(s, (40, 42, 50), (int(71 * k * 2), int(166 * k * 2), int(13 * k * 2), int(34 * k * 2)))
    pygame.draw.rect(s, (130, 136, 146), (int(70 * k * 2), int(164 * k * 2), int(12 * k * 2), int(32 * k * 2)))
    pygame.draw.rect(s, (170, 176, 186), (int(72 * k * 2), int(168 * k * 2), int(8 * k * 2), int(14 * k * 2)))
    pygame.draw.rect(s, (60, 110, 160), (int(72 * k * 2), int(166 * k * 2), int(8 * k * 2), int(2 * k * 2)))
    pygame.draw.circle(s, (200, 204, 212), (int(76 * k * 2), int(188 * k * 2)), int(3 * k * 2))
    pygame.draw.line(s, (220, 224, 230), *P([(76, 164), (76, 156)]), 1)
    # hull number on the bow
    f = pygame.font.Font(None, int(26 * k))
    num = pygame.transform.rotate(f.render("68", True, white), 0)
    s.blit(num, (int(46 * k * 2), int(20 * k * 2)))
    # parked aircraft (tiny Tomcats, wings swept) along the starboard side and the fantail
    mini = pygame.transform.smoothscale(tomcat(1.0, burner=0.0), (int(18 * k * 2), int(23 * k * 2)))
    for px, py, ang in ((60, 112, 30), (62, 130, 30), (62, 148, 30), (60, 212, -20), (60, 232, -20), (30, 108, -40), (62, 60, 25)):
        im = pygame.transform.rotate(mini, ang)
        s.blit(im, (int(px * k * 2) - im.get_width() // 2, int(py * k * 2) - im.get_height() // 2))
    # deck crew in colored jerseys
    rng = random.Random(4)
    for _ in range(46):
        x, y = rng.uniform(32, 66), rng.uniform(20, 285)
        col = rng.choice(((240, 200, 60), (60, 160, 80), (220, 60, 60), (80, 120, 220), (150, 90, 170), (240, 240, 240), (150, 90, 50)))
        pygame.draw.circle(s, col, (int(x * k * 2), int(y * k * 2)), max(1, int(0.9 * k * 2)))
    # the LSO platform, port side aft
    pygame.draw.rect(s, (240, 200, 60), (int(24 * k * 2), int(262 * k * 2), int(5 * k * 2), int(6 * k * 2)))
    out = _cache[("carrier", length)] = pygame.transform.smoothscale(s, (W, H))
    return out


# ------------------------------------------------------------------ portraits (full resolution)
SKIN = {"alex": ((176, 122, 84), (140, 92, 60)), "kj": ((120, 78, 52), (90, 56, 36)), "stephen": ((240, 200, 170), (210, 164, 134)),
        "heather": ((246, 208, 182), (220, 172, 146)), "poppa": ((128, 86, 58), (98, 62, 40))}


def portrait(who, mood="calm", size=200):
    """A large head and shoulders portrait. moods: calm, grin, alarm, flex (Alex), angry (Poppa)."""
    key = ("portrait", who, mood, size)
    if key in _cache:
        return _cache[key]
    W = H = 100
    s = pygame.Surface((W * SS, H * SS), pygame.SRCALPHA)
    skin, shade = SKIN[who]
    cx = 50.0
    bg = {"alex": (40, 70, 120), "kj": (30, 90, 100), "stephen": (110, 60, 40), "heather": (110, 50, 90), "poppa": (90, 80, 30)}[who]
    pygame.draw.rect(s, bg, (0, 0, W * SS, H * SS), border_radius=6 * SS)
    for i in range(6):                                          # sky stripes behind
        pygame.draw.rect(s, tuple(min(255, v + 10 + i * 6) for v in bg), (0, (8 + i * 9) * SS, W * SS, 4 * SS))
    global _OX
    pad = 20 if mood == "flex" else 0                            # room at the sides for raised arms
    back, s = s, pygame.Surface(((W + 2 * pad) * SS, H * SS), pygame.SRCALPHA)   # the figure goes on its own layer
    _OX = pad
    suit = (96, 110, 70) if who != "poppa" else (240, 200, 60)
    suit_sh = (70, 82, 50) if who != "poppa" else (200, 160, 40)
    # shoulders and flight suit
    poly(s, suit, [(8, 100), (14, 78), (36, 68), (64, 68), (86, 78), (92, 100)])
    poly(s, suit_sh, [(8, 100), (14, 78), (26, 74), (24, 100)])
    poly(s, suit_sh, [(40, 68), (50, 82), (60, 68), (56, 66), (44, 66)])
    if who == "poppa":
        poly(s, (230, 120, 40), [(14, 78), (36, 68), (40, 100), (20, 100)]); poly(s, (230, 120, 40), [(86, 78), (64, 68), (60, 100), (80, 100)])
    else:
        poly(s, (220, 190, 70), [(62, 80), (74, 80), (74, 85), (62, 85)])                 # wings badge
        poly(s, (40, 50, 110), [(26, 80), (36, 80), (36, 88), (26, 88)])                  # squadron patch
        oval(s, (220, 60, 60), (28.5, 81.5, 5, 5))
    if who == "alex" and mood == "flex":                         # front double biceps
        hi = (124, 140, 92)
        for sg in (-1, 1):
            X = lambda d: cx + sg * d
            L = lambda d, w: min(X(d), X(d + w))
            poly(s, suit, [(X(26), 70), (X(38), 60), (X(56), 58), (X(60), 70), (X(50), 80), (X(28), 84)])      # upper arm
            oval(s, suit, (L(34, 20), 46, 20, 22))                                                           # the bicep peak
            oval(s, hi, (L(38, 11), 48.5, 11, 6))
            line(s, suit_sh, (X(36), 69), (X(54), 67), 0.9)
            poly(s, suit, [(X(49), 60), (X(60), 60), (X(59.5), 49), (X(50), 49)])                            # rolled sleeve cuff
            line(s, suit_sh, (X(49.5), 50), (X(59.8), 50), 0.9)
            poly(s, skin, [(X(50.5), 50), (X(59), 50), (X(57.5), 33), (X(49.5), 34)])                        # forearm
            line(s, shade, (X(58.4), 49), (X(57), 34), 0.9)
            oval(s, skin, (L(46, 14), 20, 14, 15.5))                                                         # fist
            for ky in (24.5, 28, 31.5):
                line(s, shade, (X(47.5), ky), (X(53), ky), 0.6)
            oval(s, shade, (L(53.5, 5), 24, 5, 9)); oval(s, skin, (L(54.2, 4.3), 24.4, 4.3, 8))               # thumb
            for a0 in (-0.45, 0.0, 0.45):                                                                    # shine lines
                an = -math.pi / 2 + a0
                line(s, (255, 240, 150), (X(44) + math.cos(an) * 14, 56 + math.sin(an) * 14),
                     (X(44) + math.cos(an) * 19, 56 + math.sin(an) * 19), 0.8)
    # neck and head
    poly(s, shade, [(42, 58), (58, 58), (59, 70), (41, 70)])
    oval(s, skin, (31, 22, 38, 44))
    oval(s, skin, (27.5, 40, 6, 10)); oval(s, skin, (66.5, 40, 6, 10))                    # ears
    poly(s, shade, [(34, 52), (50, 66), (66, 52), (62, 60), (50, 67), (38, 60)])           # jaw shadow
    # hair
    if who == "alex":                                            # curly black high-top fade
        poly(s, (24, 20, 22), [(33, 30), (32.5, 15), (38, 11), (62, 11), (67.5, 15), (67, 30), (62, 24), (38, 24)])
        rng = random.Random(1)
        for _ in range(60):
            x, y = rng.uniform(34, 64), rng.uniform(12, 23)
            oval(s, (52, 46, 50), (x, y, 2.2, 2.2))
        poly(s, (60, 46, 40), [(31.5, 30), (33, 30), (33, 44), (31.5, 42)], mirror=cx)      # the fade
    elif who == "kj":                                            # low cut with a sharp line-up
        poly(s, (20, 16, 18), [(32, 34), (33, 20), (40, 15), (60, 15), (67, 20), (68, 34), (64, 26), (36, 26)])
        poly(s, (20, 16, 18), [(40, 58), (44, 64), (56, 64), (60, 58), (56, 61), (44, 61)])  # goatee
    elif who == "stephen":
        poly(s, (236, 200, 96), [(31, 36), (32, 18), (42, 11), (60, 11), (69, 18), (69, 36), (64, 24), (44, 22), (36, 28)])
        poly(s, (250, 226, 140), [(40, 13), (56, 12), (62, 20), (46, 19)])
    elif who == "heather":
        poly(s, (240, 208, 110), [(26, 80), (27, 26), (38, 12), (62, 12), (73, 26), (74, 80), (66, 76), (67, 34), (60, 22), (40, 22), (33, 34), (34, 76)])
        poly(s, (252, 232, 160), [(40, 14), (56, 13), (60, 20), (44, 20)])
        poly(s, (240, 208, 110), [(34, 34), (40, 22), (58, 22), (46, 28)])
    else:                                                        # Angry Poppa: bald-ish, grey-flecked beard, headset
        poly(s, (30, 26, 28), [(32, 34), (34, 22), (42, 17), (58, 17), (66, 22), (68, 34), (63, 27), (37, 27)])
        poly(s, (36, 32, 34), [(33, 46), (36, 62), (44, 70), (56, 70), (64, 62), (67, 46), (62, 56), (50, 59), (38, 56)])
        rng = random.Random(3)
        for _ in range(26):
            x, y = rng.uniform(37, 62), rng.uniform(58, 68)
            oval(s, (150, 150, 154), (x, y, 1.2, 1.2))
        pygame.draw.arc(s, (30, 30, 36), (28 * SS, 12 * SS, 44 * SS, 44 * SS), 0.2, math.pi - 0.2, 3 * SS)
        oval(s, (30, 30, 36), (24, 36, 9, 14)); oval(s, (30, 30, 36), (67, 36, 9, 14))
        line(s, (30, 30, 36), (27, 48), (40, 58), 1.0)
    # eyes: aviators for the player one crew, bare eyes otherwise
    if who in ("alex", "kj"):
        for ex in (41, 59):
            poly(s, (220, 180, 70), [(ex - 8.2, 36), (ex + 8.2, 36), (ex + 6.6, 47.5), (ex, 49.4), (ex - 6.6, 47.5)])
            poly(s, (24, 28, 40), [(ex - 7, 37.2), (ex + 7, 37.2), (ex + 5.6, 46.6), (ex, 48.2), (ex - 5.6, 46.6)])
            poly(s, (90, 130, 190), [(ex - 5.6, 38.2), (ex - 1, 38.2), (ex - 4.6, 44)])
            poly(s, (240, 150, 70), [(ex + 1, 44.5), (ex + 5.4, 40.5), (ex + 5, 45.4), (ex + 0.5, 47)])  # sunset glint
        line(s, (220, 180, 70), (47, 38), (53, 38), 1.0)
        line(s, (220, 180, 70), (33, 38), (28.5, 40), 0.8, mirror=cx)
    else:
        for ex in (41, 59):
            oval(s, (255, 255, 255), (ex - 4.5, 38.5, 9, 6.5))
            iris = {"stephen": (70, 130, 190), "heather": (80, 150, 120), "poppa": (60, 36, 20)}[who]
            oval(s, iris, (ex - 2.2, 39.2, 4.6, 5))
            oval(s, (16, 14, 16), (ex - 1.1, 40.4, 2.4, 2.6))
            oval(s, (255, 255, 255), (ex + 0.2, 40.2, 1.2, 1.2))
        browc = {"stephen": (190, 150, 70), "heather": (190, 150, 70), "poppa": (30, 26, 28)}[who]
        tilt = 3.2 if (who == "poppa" or mood == "angry") else (-1.5 if mood == "alarm" else 0)
        line(s, browc, (35.5, 35.5 - tilt * 0.2), (46, 35.5 + tilt), 1.4)
        line(s, browc, (64.5, 35.5 - tilt * 0.2), (54, 35.5 + tilt), 1.4)
        if who == "heather":
            line(s, (60, 40, 30), (36.5, 38.6), (45.5, 38.2), 0.6, mirror=cx)
    # nose and mouth
    poly(s, shade, [(49, 44), (46.5, 53), (53.5, 53)])
    lip = (150, 60, 60) if who != "heather" else (214, 70, 96)
    if mood in ("grin", "flex"):
        poly(s, (50, 24, 26), [(40, 56.5), (60, 56.5), (56, 63), (44, 63)])
        poly(s, (255, 255, 255), [(41.5, 57), (58.5, 57), (57, 60), (43, 60)])
        line(s, shade, (38.5, 55.5), (40.5, 57.5), 0.7, mirror=cx)
    elif mood == "alarm":
        oval(s, (50, 24, 26), (45, 55.5, 10, 9)); oval(s, (255, 255, 255), (46.5, 56, 7, 2.4))
    elif mood == "angry" or who == "poppa":
        poly(s, (50, 24, 26), [(42, 60), (58, 60), (56, 56.5), (44, 56.5)])
        poly(s, (255, 255, 255), [(43.5, 59.4), (56.5, 59.4), (55.4, 57.4), (44.6, 57.4)])
        line(s, (50, 24, 26), (47, 57), (47, 60), 0.4); line(s, (50, 24, 26), (50, 57), (50, 60), 0.4); line(s, (50, 24, 26), (53, 57), (53, 60), 0.4)
    else:
        line(s, lip, (43, 58), (57, 58), 1.2)
        line(s, lip, (57, 58), (59, 57), 1.0)
    if mood == "flex":                                           # pull back so the arms fit in frame
        k = 0.74
        s = pygame.transform.smoothscale(s, (int(s.get_width() * k), int(H * SS * k)))
    back.blit(s, ((W * SS - s.get_width()) // 2, H * SS - s.get_height()))
    s, _OX = back, 0.0
    pygame.draw.rect(s, (240, 240, 240), (0, 0, W * SS, H * SS), 2 * SS, border_radius=6 * SS)
    out = _cache[key] = pygame.transform.smoothscale(s, (size, size))
    return out
