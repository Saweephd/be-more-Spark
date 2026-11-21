"""Art for The Big Move and Momma Rose's Air Hockey. Everything is drawn in code and original."""
import math

import pygame

OUT = (22, 18, 28)
PEOPLE = {
    "whitney": dict(skin=(238, 196, 160), shade=(206, 156, 124), hair=(84, 50, 30), hair_hi=(120, 76, 46),
                    top=(236, 110, 150), top_sh=(190, 70, 112), legs=(70, 96, 170), shoe=(250, 250, 250), long=14),
    "lucas": dict(skin=(198, 142, 100), shade=(160, 106, 70), hair=(60, 36, 22), hair_hi=(96, 60, 36),
                  top=(70, 160, 120), top_sh=(40, 116, 86), legs=(60, 60, 74), shoe=(200, 60, 50), long=9),
}


def _outline(img):
    """A dark one pixel outline round whatever is drawn on img."""
    mask = pygame.mask.from_surface(img)
    w, h = img.get_size()
    out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
    sil = mask.to_surface(setcolor=OUT + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(sil, (dx, dy))
    out.blit(img, (1, 1))
    return out


def person(kind, frame=0, facing="down", carrying=False):
    """Whitney or Lucas, 18 x 30. facing: down (towards us), up (away), left, right."""
    p = PEOPLE[kind]
    s = pygame.Surface((16, 28), pygame.SRCALPHA)
    step = (frame % 2) * 2 - 1
    if facing != "up":                      # long hair hangs behind the shoulders
        pygame.draw.rect(s, p["hair"], (2, 2, 12, p["long"]), border_radius=3)
    # legs and shoes
    for i, x in enumerate((4, 9)):
        lift = 1 if (i == 0) == (step > 0) else 0
        pygame.draw.rect(s, p["legs"], (x, 19, 3, 6 - lift))
        pygame.draw.rect(s, p["shoe"], (x - (1 if facing == "left" else 0), 25 - lift, 4, 2))
    # torso
    pygame.draw.rect(s, p["top"], (3, 11, 10, 9), border_radius=2)
    pygame.draw.rect(s, p["top_sh"], (3, 17, 10, 3), border_bottom_left_radius=2, border_bottom_right_radius=2)
    if kind == "lucas":
        pygame.draw.line(s, (240, 240, 230), (8, 12), (8, 18))          # open overshirt
    else:
        pygame.draw.line(s, (255, 190, 210), (5, 13), (10, 13))         # neckline trim
    # arms
    if carrying:
        pygame.draw.rect(s, p["skin"], (1, 5, 2, 8))
        pygame.draw.rect(s, p["skin"], (13, 5, 2, 8))
    else:
        pygame.draw.rect(s, p["top"], (1, 12, 2, 4))
        pygame.draw.rect(s, p["top"], (13, 12, 2, 4))
        pygame.draw.rect(s, p["skin"], (1, 16 + (step > 0), 2, 3))
        pygame.draw.rect(s, p["skin"], (13, 16 + (step < 0), 2, 3))
    # head
    if facing != "up":
        hx = {"down": 4, "left": 3, "right": 5}[facing]
        pygame.draw.rect(s, p["skin"], (hx, 3, 8, 8), border_radius=3)
        pygame.draw.rect(s, p["shade"], (hx + 1, 10, 6, 1))
        # fringe and side locks
        pygame.draw.rect(s, p["hair"], (hx, 2, 8, 3), border_radius=2)
        pygame.draw.line(s, p["hair_hi"], (hx + 2, 2), (hx + 5, 2))
        eyes = {"down": (hx + 2, hx + 5), "left": (hx + 1, hx + 3), "right": (hx + 4, hx + 6)}[facing]
        for ex in eyes:
            s.set_at((ex, 7), OUT)
        pygame.draw.line(s, (190, 80, 80), (eyes[0] + 1, 9), (eyes[1] - 1, 9))
        if kind == "lucas":                                              # a little stubble beard
            pygame.draw.line(s, p["hair"], (hx + 1, 10), (hx + 6, 10))
        lock = 15 if kind == "whitney" else 11                           # locks framing the face
        pygame.draw.line(s, p["hair"], (hx - 1, 4), (hx - 1, lock))
        pygame.draw.line(s, p["hair"], (hx + 8, 4), (hx + 8, lock))
    else:
        pygame.draw.rect(s, p["hair"], (3, 2, 10, p["long"]), border_radius=3)
        pygame.draw.line(s, p["hair_hi"], (6, 3), (6, 2 + p["long"] - 3))
        pygame.draw.line(s, p["hair_hi"], (9, 4), (9, 2 + p["long"] - 4))
    return _outline(s)


def _box(s, r, col, hi, sh):
    pygame.draw.rect(s, col, r, border_radius=2)
    pygame.draw.rect(s, hi, (r[0], r[1], r[2], 2), border_radius=2)
    pygame.draw.rect(s, sh, (r[0], r[1] + r[3] - 2, r[2], 2), border_radius=2)


def item(kind):
    """Household goods, drawn to be recognised at a glance."""
    if kind == "box":
        s = pygame.Surface((14, 12), pygame.SRCALPHA)
        _box(s, (0, 0, 14, 12), (196, 150, 96), (222, 180, 124), (160, 116, 70))
        pygame.draw.line(s, (236, 222, 180), (0, 5), (13, 5), 2)        # packing tape
        pygame.draw.line(s, (120, 86, 50), (7, 0), (7, 4))
    elif kind == "lamp":
        s = pygame.Surface((12, 18), pygame.SRCALPHA)
        pygame.draw.polygon(s, (250, 226, 150), [(3, 0), (8, 0), (11, 8), (0, 8)])
        pygame.draw.polygon(s, (226, 190, 110), [(8, 0), (11, 8), (8, 8), (6, 0)])
        pygame.draw.rect(s, (120, 120, 130), (5, 8, 2, 7))
        pygame.draw.ellipse(s, (90, 90, 100), (2, 14, 8, 4))
    elif kind == "tv":
        s = pygame.Surface((20, 14), pygame.SRCALPHA)
        pygame.draw.rect(s, (40, 40, 50), (0, 0, 20, 12), border_radius=2)
        pygame.draw.rect(s, (90, 170, 230), (2, 2, 16, 8))
        pygame.draw.polygon(s, (170, 220, 250), [(3, 9), (9, 2), (12, 2), (6, 9)])
        pygame.draw.rect(s, (60, 60, 70), (7, 12, 6, 2))
    elif kind == "table":
        s = pygame.Surface((26, 14), pygame.SRCALPHA)
        for x in (2, 21):
            pygame.draw.rect(s, (120, 76, 40), (x, 5, 3, 9))
        pygame.draw.rect(s, (96, 60, 30), (5, 6, 16, 2))
        _box(s, (0, 0, 26, 6), (176, 116, 62), (208, 150, 90), (140, 88, 46))
    elif kind == "bed":
        s = pygame.Surface((34, 16), pygame.SRCALPHA)
        pygame.draw.rect(s, (120, 76, 40), (0, 0, 4, 16), border_radius=1)          # headboard
        pygame.draw.rect(s, (120, 76, 40), (2, 11, 32, 3))
        pygame.draw.rect(s, (96, 60, 30), (4, 14, 3, 2)); pygame.draw.rect(s, (96, 60, 30), (30, 14, 3, 2))
        _box(s, (4, 4, 30, 8), (240, 240, 246), (255, 255, 255), (200, 204, 220))   # mattress
        pygame.draw.rect(s, (110, 150, 220), (14, 4, 20, 8), border_radius=2)       # blanket
        pygame.draw.line(s, (150, 186, 240), (14, 5), (33, 5))
        pygame.draw.rect(s, (255, 250, 236), (5, 5, 7, 5), border_radius=2)         # pillow
    else:  # sofa
        s = pygame.Surface((36, 18), pygame.SRCALPHA)
        _box(s, (2, 0, 32, 10), (196, 70, 70), (226, 104, 100), (156, 48, 54))      # back
        pygame.draw.rect(s, (214, 86, 84), (4, 8, 28, 6), border_radius=2)          # seat
        pygame.draw.line(s, (156, 48, 54), (18, 8), (18, 13))
        pygame.draw.line(s, (156, 48, 54), (18, 1), (18, 7))
        for x in (0, 30):
            _box(s, (x, 5, 6, 10), (180, 60, 62), (220, 96, 94), (140, 40, 48))     # arms
        for x in (3, 30):
            pygame.draw.rect(s, (70, 44, 30), (x, 15, 3, 3))
    return _outline(s)


def vehicle(kind, col=(220, 60, 60), face=1):
    """Side-on traffic. face 1 drives right."""
    if kind == "car":
        s = pygame.Surface((34, 18), pygame.SRCALPHA)
        dark = tuple(max(0, c - 50) for c in col)
        pygame.draw.rect(s, col, (0, 7, 34, 8), border_radius=3)
        pygame.draw.polygon(s, col, [(7, 8), (11, 1), (24, 1), (29, 8)])
        pygame.draw.polygon(s, (170, 220, 250), [(10, 7), (12, 3), (17, 3), (17, 7)])
        pygame.draw.polygon(s, (170, 220, 250), [(19, 7), (19, 3), (23, 3), (26, 7)])
        pygame.draw.rect(s, dark, (0, 13, 34, 2))
        pygame.draw.rect(s, (255, 240, 150), (32, 9, 2, 3)); pygame.draw.rect(s, (230, 50, 50), (0, 9, 2, 3))
        for x in (5, 23):
            pygame.draw.circle(s, (26, 26, 32), (x + 3, 15), 3); pygame.draw.circle(s, (170, 170, 180), (x + 3, 15), 1)
    elif kind == "truck":
        s = pygame.Surface((62, 24), pygame.SRCALPHA)
        _box(s, (0, 0, 44, 19), (236, 236, 240), (255, 255, 255), (196, 198, 210))
        pygame.draw.rect(s, col, (4, 6, 36, 6))
        pygame.draw.rect(s, col, (45, 5, 17, 14), border_radius=3)
        pygame.draw.rect(s, (170, 220, 250), (51, 7, 9, 6))
        pygame.draw.rect(s, (255, 240, 150), (60, 14, 2, 3))
        pygame.draw.rect(s, (60, 60, 70), (0, 19, 62, 2))
        for x in (6, 16, 50):
            pygame.draw.circle(s, (26, 26, 32), (x + 3, 21), 3); pygame.draw.circle(s, (170, 170, 180), (x + 3, 21), 1)
    elif kind == "pickup":                       # the family's white pickup, parked
        s = pygame.Surface((58, 24), pygame.SRCALPHA)
        pygame.draw.rect(s, (244, 244, 248), (0, 10, 58, 9), border_radius=3)
        pygame.draw.polygon(s, (244, 244, 248), [(30, 11), (34, 2), (46, 2), (51, 11)])
        pygame.draw.polygon(s, (170, 220, 250), [(34, 10), (36, 4), (40, 4), (40, 10)])
        pygame.draw.polygon(s, (170, 220, 250), [(42, 10), (42, 4), (45, 4), (48, 10)])
        pygame.draw.rect(s, (200, 204, 216), (0, 17, 58, 2))
        pygame.draw.rect(s, (214, 216, 226), (1, 8, 28, 3))             # bed rail
        pygame.draw.rect(s, (255, 240, 150), (56, 12, 2, 3)); pygame.draw.rect(s, (230, 50, 50), (0, 12, 2, 3))
        for x in (7, 41):
            pygame.draw.circle(s, (26, 26, 32), (x + 4, 19), 4); pygame.draw.circle(s, (170, 170, 180), (x + 4, 19), 2)
    else:  # bike with rider
        s = pygame.Surface((24, 24), pygame.SRCALPHA)
        for x in (5, 18):
            pygame.draw.circle(s, (30, 30, 36), (x, 18), 5, 1)
        pygame.draw.lines(s, col, False, [(5, 18), (10, 11), (16, 11), (18, 18)], 2)
        pygame.draw.line(s, col, (10, 11), (12, 18), 1)
        pygame.draw.line(s, (60, 60, 70), (16, 11), (17, 8))
        pygame.draw.rect(s, (250, 210, 70), (8, 4, 6, 7), border_radius=2)            # jersey
        pygame.draw.circle(s, (226, 180, 140), (13, 3), 3)
        pygame.draw.arc(s, (60, 130, 220), (10, -1, 7, 6), 0, math.pi, 2)             # helmet
        pygame.draw.line(s, (40, 40, 60), (10, 10), (12, 16), 2)
    s = _outline(s)
    return s if face > 0 else pygame.transform.flip(s, True, False)


def cat(frame=0, face=1):
    """Peno?! An orange tabby trotting by."""
    s = pygame.Surface((18, 13), pygame.SRCALPHA)
    o, d, w = (236, 150, 60), (190, 104, 36), (252, 238, 214)
    pygame.draw.rect(s, o, (3, 5, 10, 5), border_radius=2)
    for x in (5, 8):
        pygame.draw.line(s, d, (x, 5), (x, 7))
    pygame.draw.rect(s, o, (11, 2, 6, 6), border_radius=2)
    pygame.draw.polygon(s, o, [(11, 3), (12, 0), (14, 2)]); pygame.draw.polygon(s, o, [(15, 2), (16, 0), (17, 3)])
    s.set_at((13, 4), OUT); s.set_at((16, 4), OUT); s.set_at((15, 6), (240, 120, 140))
    pygame.draw.rect(s, w, (12, 6, 2, 2))
    a = 1 if frame % 2 else 0
    for x, up in ((4, a), (6, 1 - a), (10, a), (12, 1 - a)):
        pygame.draw.line(s, o, (x, 10), (x, 12 - up))
    pygame.draw.lines(s, o, False, [(3, 6), (1, 4), (0 + a, 1)], 2)
    s = _outline(s)
    return s if face > 0 else pygame.transform.flip(s, True, False)


# ---------------------------------------------------------------- Momma Rose
def _paisley(s, rect, seed=3):
    import random
    rng = random.Random(seed)
    x0, y0, w, h = rect
    for k in range(int(w * h / 60)):
        gx, gy = k % (w // 8), k // (w // 8)
        x, y = x0 + gx * 8 + rng.randrange(6) + (4 if gy % 2 else 0), y0 + gy * 7 + rng.randrange(5)
        if not (0 <= x < s.get_width() and 0 <= y < s.get_height()):
            continue
        if s.get_at((x, y))[3] == 0:
            continue
        col = rng.choice(((250, 214, 110), (250, 250, 240), (240, 120, 150), (120, 220, 210)))
        r = rng.choice((2, 3))
        pygame.draw.circle(s, col, (x, y), r)                    # teardrop: a dot with a curled tail
        a = rng.uniform(0, 6.28)
        pygame.draw.line(s, col, (x, y), (x + int(math.cos(a) * (r + 2)), y + int(math.sin(a) * (r + 2))))
        s.set_at((x, y), (40, 60, 130))


def rose(mood="smile", lean=0):
    """Momma Rose from the hips up, 84 x 92: brunette, paisley top, jeans."""
    s = pygame.Surface((84, 92), pygame.SRCALPHA)
    skin, shade = (232, 186, 150), (202, 150, 118)
    hair, hi = (74, 44, 28), (116, 72, 44)
    cx = 42 + lean
    # hair behind
    pygame.draw.ellipse(s, hair, (cx - 21, 2, 42, 50))
    pygame.draw.ellipse(s, hair, (cx - 24, 24, 16, 34)); pygame.draw.ellipse(s, hair, (cx + 8, 24, 16, 34))
    # jeans at the hips
    pygame.draw.rect(s, (60, 96, 168), (12, 78, 60, 14), border_radius=6)
    pygame.draw.line(s, (40, 70, 130), (42, 80), (42, 92)); pygame.draw.rect(s, (200, 170, 90), (39, 78, 6, 3))
    # paisley top: curvy
    top = (44, 70, 150)
    pygame.draw.ellipse(s, top, (10, 44, 64, 30))                # shoulders and bust
    pygame.draw.polygon(s, top, [(16, 60), (68, 60), (62, 74), (70, 84), (14, 84), (22, 74)])   # waist to hips
    _paisley(s, (10, 44, 64, 40))
    pygame.draw.polygon(s, skin, [(34, 44), (50, 44), (42, 56)])  # neckline
    pygame.draw.rect(s, skin, (37, 38, 10, 8)); pygame.draw.line(s, shade, (37, 45), (46, 45))
    # arms
    for x in (6, 68):
        pygame.draw.ellipse(s, top, (x, 48, 12, 18))
        pygame.draw.ellipse(s, skin, (x + 1, 62, 10, 20))
    # face
    pygame.draw.ellipse(s, skin, (cx - 14, 8, 28, 34))
    pygame.draw.ellipse(s, hair, (cx - 16, 3, 32, 16))            # fringe swept to the side
    pygame.draw.polygon(s, hair, [(cx - 15, 12), (cx + 6, 8), (cx + 15, 22), (cx + 15, 10)])
    pygame.draw.arc(s, hi, (cx - 12, 4, 22, 12), 0.6, 2.4, 2)
    for ex in (cx - 6, cx + 6):
        pygame.draw.ellipse(s, (255, 255, 255), (ex - 3, 22, 6, 5))
        pygame.draw.circle(s, (70, 44, 24), (ex, 24), 2); s.set_at((ex + 1, 23), (255, 255, 255))
        pygame.draw.line(s, OUT, (ex - 3, 21), (ex + 3, 21))
        brow = -1 if mood == "smug" else (1 if mood == "oops" else 0)
        pygame.draw.line(s, hair, (ex - 4, 18 + (brow if ex < cx else -brow)), (ex + 4, 18 - (brow if ex < cx else -brow)), 2)
    pygame.draw.line(s, shade, (cx, 26), (cx - 1, 30))
    for bx in (cx - 9, cx + 9):
        pygame.draw.circle(s, (244, 160, 150), (bx, 31), 3)
    lip = (206, 60, 80)
    if mood == "oops":
        pygame.draw.ellipse(s, lip, (cx - 3, 33, 6, 6)); pygame.draw.ellipse(s, (120, 30, 40), (cx - 2, 34, 4, 4))
    elif mood == "smile":
        pygame.draw.polygon(s, lip, [(cx - 6, 33), (cx + 6, 33), (cx + 3, 38), (cx - 3, 38)])
        pygame.draw.rect(s, (255, 255, 255), (cx - 4, 34, 8, 2))
    else:                                    # smug: a sideways smirk
        pygame.draw.lines(s, lip, False, [(cx - 5, 36), (cx + 2, 36), (cx + 6, 33)], 2)
    pygame.draw.circle(s, (250, 214, 110), (cx - 14, 30), 2); pygame.draw.circle(s, (250, 214, 110), (cx + 14, 30), 2)
    return _outline(s)


_bubble_font = None


def bubble(surf, msg, cx, cy):
    """A speech bubble centred on (cx, cy), kept on screen."""
    global _bubble_font
    if _bubble_font is None:
        _bubble_font = pygame.font.Font(None, 15)
    im = _bubble_font.render(msg, False, (30, 30, 40))
    r = im.get_rect(center=(int(cx), int(cy))).inflate(10, 6)
    r.clamp_ip(surf.get_rect().inflate(-4, -4))
    pygame.draw.rect(surf, (255, 255, 255), r, border_radius=5)
    pygame.draw.rect(surf, (30, 30, 40), r, 1, border_radius=5)
    surf.blit(im, im.get_rect(center=r.center))


def rose_head():
    """Momma Rose's face, small, for the pickup's window."""
    big = rose("smile")
    return pygame.transform.smoothscale(big.subsurface((18, 2, 50, 44)), (15, 13))
