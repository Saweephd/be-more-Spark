"""Pixel-art helpers made in code: terrain textures, scenery, explosions, medals.

Everything is drawn once into surfaces (deterministic, from a seed) and then
blitted, so it costs nothing per frame on BMO's Pi. All art is original.
"""
import math
import random

import pygame


def shade(col, f):
    return tuple(max(0, min(255, int(v * f))) for v in col)


def wrap_draw(size, draw, *args):
    """Draw something at an offset and its wrapped copies, so the texture tiles seamlessly."""
    w, h = size
    for dx in (-w, 0, w):
        for dy in (-h, 0, h):
            draw(dx, dy, *args)


# ---------- fills (what is under a ledge) ----------
def boulders(size, base, seed, count=9):
    """Contra-style rock: rounded boulders with a light top-left edge and dark seams."""
    w, h = size
    s = pygame.Surface(size)
    s.fill(shade(base, 0.45))
    rng = random.Random(seed)
    for _ in range(count):
        cx, cy = rng.randrange(w), rng.randrange(h)
        bw, bh = rng.randint(14, 26), rng.randint(10, 18)
        tone = rng.uniform(0.85, 1.12)

        def one(dx, dy):
            r = pygame.Rect(cx + dx - bw // 2, cy + dy - bh // 2, bw, bh)
            pygame.draw.rect(s, shade(base, 0.35 * tone), r.inflate(2, 2), border_radius=6)
            pygame.draw.rect(s, shade(base, tone), r, border_radius=6)
            pygame.draw.rect(s, shade(base, 0.72 * tone), (r.x + 2, r.centery, r.w - 3, r.h // 2 - 1), border_radius=4)
            pygame.draw.line(s, shade(base, 1.35 * tone), (r.x + 3, r.y + 1), (r.right - 5, r.y + 1))
            pygame.draw.line(s, shade(base, 1.35 * tone), (r.x + 1, r.y + 3), (r.x + 1, r.centery))
            for _ in range(3):
                px, py = r.x + rng.randrange(max(1, r.w)), r.y + rng.randrange(max(1, r.h))
                s.set_at(((px) % w, (py) % h), shade(base, 0.5))
        wrap_draw(size, lambda dx, dy: one(dx, dy))
    return s


def hull_plates(size, base, seed):
    w, h = size
    s = pygame.Surface(size)
    s.fill(base)
    rng = random.Random(seed)
    for y in range(0, h, 16):
        pygame.draw.line(s, shade(base, 0.6), (0, y), (w, y))
        pygame.draw.line(s, shade(base, 1.25), (0, y + 1), (w, y + 1))
        off = 8 if (y // 16) % 2 else 0
        for x in range(off, w, 24):
            pygame.draw.line(s, shade(base, 0.6), (x, y), (x, y + 15))
            for ry in (y + 3, y + 12):
                s.set_at((x + 3, ry), shade(base, 1.4))
                s.set_at((x + 3, ry + 1), shade(base, 0.6))
    for _ in range(2):
        px, py = rng.randrange(8, w - 8), rng.randrange(8, h - 8)
        pygame.draw.circle(s, shade(base, 0.5), (px, py), 4)
        pygame.draw.circle(s, (120, 170, 210), (px, py), 3)
        s.set_at((px - 1, py - 1), (230, 240, 255))
    for _ in range(6):     # rust streaks
        x = rng.randrange(w)
        y = rng.randrange(h)
        pygame.draw.line(s, (130, 90, 70), (x, y), (x, min(h - 1, y + rng.randint(3, 9))))
    return s


def blocks(size, base, seed):
    w, h = size
    s = pygame.Surface(size)
    s.fill(base)
    rng = random.Random(seed)
    for y in range(0, h, 10):
        off = 10 if (y // 10) % 2 else 0
        pygame.draw.line(s, shade(base, 0.55), (0, y), (w, y))
        for x in range(off, w, 20):
            pygame.draw.line(s, shade(base, 0.55), (x, y), (x, y + 9))
            pygame.draw.line(s, shade(base, 1.2), (x + 1, y + 1), (x + 18, y + 1))
    for _ in range(14):
        s.set_at((rng.randrange(w), rng.randrange(h)), shade(base, rng.choice((0.7, 1.25))))
    return s


def corrugated(size, seed):
    w, h = size
    s = pygame.Surface(size)
    rng = random.Random(seed)
    colors = [(170, 70, 50), (60, 110, 150), (190, 150, 60), (80, 120, 80)]
    y = 0
    while y < h:
        col = rng.choice(colors)
        bh = 18
        pygame.draw.rect(s, col, (0, y, w, bh))
        for x in range(0, w, 3):
            pygame.draw.line(s, shade(col, 0.72), (x, y + 2), (x, y + bh - 3))
        pygame.draw.line(s, shade(col, 1.3), (0, y + 1), (w, y + 1))
        pygame.draw.line(s, shade(col, 0.4), (0, y + bh - 1), (w, y + bh - 1))
        y += bh
    return s


# ---------- tops (the walking surface) ----------
def grass_top(width, seed):
    s = pygame.Surface((width, 12), pygame.SRCALPHA)
    rng = random.Random(seed)
    pygame.draw.rect(s, (40, 150, 40), (0, 3, width, 7))
    pygame.draw.rect(s, (20, 90, 30), (0, 9, width, 3))
    for x in range(0, width, 2):
        hgt = rng.randint(0, 3)
        pygame.draw.line(s, (110, 220, 60), (x, 3 - hgt), (x, 5))
        if rng.random() < 0.35:
            s.set_at((x, 6 + rng.randint(0, 2)), (190, 240, 90))
    for x in range(0, width, 5):     # blades hanging over the edge
        pygame.draw.line(s, (30, 120, 30), (x, 10), (x + 1, 11 + rng.randint(0, 1)))
    return s


def hazard_top(width, seed):
    s = pygame.Surface((width, 10), pygame.SRCALPHA)
    pygame.draw.rect(s, (150, 154, 162), (0, 0, width, 3))
    pygame.draw.line(s, (220, 224, 232), (0, 0), (width, 0))
    for x in range(-10, width, 10):
        pygame.draw.polygon(s, (230, 190, 40), [(x, 3), (x + 5, 3), (x + 10, 9), (x + 5, 9)])
        pygame.draw.polygon(s, (30, 30, 34), [(x + 5, 3), (x + 10, 3), (x + 15, 9), (x + 10, 9)])
    return s


def sandbag_top(width, seed):
    s = pygame.Surface((width, 12), pygame.SRCALPHA)
    rng = random.Random(seed)
    for row, y in enumerate((5, 0)):
        off = 6 if row else 0
        for x in range(-12 + off, width, 12):
            col = shade((196, 172, 120), rng.uniform(0.9, 1.08))
            pygame.draw.ellipse(s, shade(col, 0.55), (x - 1, y - 1, 14, 9))
            pygame.draw.ellipse(s, col, (x, y, 12, 7))
            pygame.draw.line(s, shade(col, 1.2), (x + 3, y + 1), (x + 8, y + 1))
    return s


def grate_top(width, seed):
    s = pygame.Surface((width, 8), pygame.SRCALPHA)
    pygame.draw.rect(s, (120, 124, 132), (0, 0, width, 8))
    for x in range(0, width, 4):
        pygame.draw.line(s, (60, 62, 70), (x, 2), (x, 6))
    pygame.draw.line(s, (200, 204, 214), (0, 0), (width, 0))
    pygame.draw.line(s, (40, 42, 48), (0, 7), (width, 7))
    return s


def snow_top(width, seed):
    s = pygame.Surface((width, 14), pygame.SRCALPHA)
    rng = random.Random(seed)
    pygame.draw.rect(s, (236, 242, 252), (0, 2, width, 6))
    for x in range(0, width, 7):
        r = rng.randint(3, 5)
        pygame.draw.circle(s, (246, 250, 255), (x + 3, 4), r)
        pygame.draw.circle(s, (200, 214, 236), (x + 3, 7), r - 1)
    for x in range(2, width, rng.randint(6, 11)):    # icicles
        pygame.draw.polygon(s, (190, 220, 250), [(x, 8), (x + 3, 8), (x + 1, 8 + rng.randint(3, 6))])
    return s


# ---------- background layers ----------
def sky(size, top, bottom):
    w, h = size
    s = pygame.Surface(size)
    for y in range(h):
        t = y / float(h - 1)
        s.fill(tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)), (0, y, w, 1))
    return s


def jungle_layer(width, height, seed):
    """Dark trunks with light stripes and a canopy of fronds, like the classic jungle stage."""
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    rng = random.Random(seed)
    s.fill((48, 30, 22, 255), (0, 30, width, height - 30))
    x = 0
    while x < width:
        tw = rng.randint(7, 11)
        col = (rng.randint(56, 74), rng.randint(36, 46), 28)
        pygame.draw.rect(s, col, (x, 20, tw, height))
        for y in range(30, height, rng.randint(9, 14)):
            pygame.draw.line(s, shade(col, 1.5), (x + 1, y), (x + tw - 2, y + 2))
        pygame.draw.line(s, shade(col, 0.55), (x + tw - 1, 20), (x + tw - 1, height))
        x += tw + rng.randint(4, 10)
    for i in range(0, width, 26):     # fronds
        cx, cy = i + rng.randint(0, 10), rng.randint(6, 22)
        for a in range(200, 345, 18):
            for k in range(0, 18, 2):
                px = cx + int(math.cos(math.radians(a)) * k * 1.4)
                py = cy - int(math.sin(math.radians(a)) * k * 0.7) + k // 3
                col = (40, 150, 40) if k % 4 else (150, 220, 70)
                pygame.draw.circle(s, col, (px % width, py), 2)
        pygame.draw.circle(s, (24, 90, 30), (cx, cy), 4)
    return s


def mountains(width, height, base, snow, seed, peaks=6, top=60):
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    rng = random.Random(seed)
    step = width // peaks
    for i in range(-1, peaks + 1):
        x = i * step + rng.randint(-10, 10)
        py = top + rng.randint(-15, 25)
        bw = step + rng.randint(10, 40)
        pygame.draw.polygon(s, base, [(x - bw // 2, height), (x, py), (x + bw // 2, height)])
        pygame.draw.polygon(s, shade(base, 0.75), [(x, py), (x + bw // 2, height), (x + bw // 6, height)])
        if snow:
            pygame.draw.polygon(s, snow, [(x - 10, py + 18), (x, py), (x + 10, py + 18), (x + 3, py + 14), (x - 4, py + 20)])
    return s


def pines(width, height, seed, snowy=False):
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    rng = random.Random(seed)
    x = 0
    while x < width:
        h = rng.randint(30, 50)
        base_y = height
        for k in range(4):
            yy = base_y - 8 - k * (h // 5)
            half = 12 - k * 2
            pygame.draw.polygon(s, (30, 70, 50), [(x - half, yy), (x, yy - h // 3), (x + half, yy)])
            if snowy:
                pygame.draw.line(s, (236, 242, 252), (x - half + 2, yy - 1), (x, yy - h // 3 + 2))
        pygame.draw.rect(s, (70, 50, 40), (x - 2, base_y - 8, 4, 8))
        x += rng.randint(16, 30)
    return s


def ships_layer(width, height, seed):
    """Distant warships and the carrier's island tower on a bright sea."""
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    rng = random.Random(seed)
    for i in range(3):
        x = i * width // 3 + rng.randint(0, 40)
        y = height - 40
        pygame.draw.polygon(s, (100, 110, 124), [(x, y), (x + 90, y), (x + 80, y + 10), (x + 6, y + 10)])
        pygame.draw.rect(s, (110, 120, 134), (x + 30, y - 14, 24, 14))
        pygame.draw.rect(s, (90, 98, 110), (x + 38, y - 24, 6, 10))
        pygame.draw.line(s, (90, 98, 110), (x + 41, y - 24), (x + 41, y - 34))
    tx = width // 2
    ty = height - 18
    pygame.draw.rect(s, (120, 126, 138), (tx, ty - 70, 40, 70))
    for wy in range(ty - 62, ty - 10, 10):
        pygame.draw.rect(s, (60, 90, 120), (tx + 4, wy, 32, 4))
    pygame.draw.rect(s, (100, 104, 116), (tx + 14, ty - 92, 12, 22))
    pygame.draw.circle(s, (170, 176, 188), (tx + 20, ty - 96), 8, 2)
    pygame.draw.line(s, (90, 94, 104), (tx + 20, ty - 104), (tx + 20, ty - 124))
    text_col = (220, 224, 232)
    for k, ch in enumerate("74"):
        pygame.draw.rect(s, text_col, (tx + 8 + k * 14, ty - 54, 9, 12), 2)
    return s


def buildings_layer(width, height, seed, kind):
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    rng = random.Random(seed)
    x = 0
    while x < width:
        if kind == "base":
            bw, bh = rng.randint(50, 80), rng.randint(36, 60)
            y = height - bh
            pygame.draw.rect(s, (126, 100, 80), (x, y, bw, bh))
            pygame.draw.polygon(s, (90, 64, 54), [(x - 4, y), (x + bw // 2, y - 16), (x + bw + 4, y)])
            for wx in range(x + 6, x + bw - 8, 14):
                pygame.draw.rect(s, (250, 220, 120), (wx, y + 10, 7, 8))
                pygame.draw.rect(s, (60, 46, 40), (wx, y + 10, 7, 8), 1)
            if rng.random() < 0.4:       # watchtower
                tx = x + bw + 8
                pygame.draw.line(s, (90, 70, 50), (tx, height), (tx + 4, height - 80), 2)
                pygame.draw.line(s, (90, 70, 50), (tx + 18, height), (tx + 14, height - 80), 2)
                pygame.draw.rect(s, (110, 86, 60), (tx - 2, height - 92, 22, 14))
                pygame.draw.polygon(s, (80, 60, 44), [(tx - 4, height - 92), (tx + 9, height - 102), (tx + 22, height - 92)])
                bw += 30
        else:
            bw, bh = rng.randint(90, 130), rng.randint(46, 64)
            y = height - bh
            pygame.draw.rect(s, (150, 152, 162), (x, y + 14, bw, bh - 14))
            pygame.draw.ellipse(s, (130, 134, 146), (x, y, bw, 30))
            for lx in range(x + 4, x + bw, 6):
                pygame.draw.line(s, (116, 120, 132), (lx, y + 4), (lx, y + 26))
            pygame.draw.rect(s, (50, 52, 60), (x + bw // 4, y + 26, bw // 2, bh - 26))
            for k in range(3):
                pygame.draw.line(s, (90, 92, 100), (x + bw // 4, y + 30 + k * 10), (x + 3 * bw // 4, y + 30 + k * 10))
            if rng.random() < 0.35:      # control tower
                tx = x + bw + 10
                pygame.draw.rect(s, (170, 172, 180), (tx, height - 96, 14, 96))
                pygame.draw.rect(s, (60, 110, 150), (tx - 6, height - 108, 26, 12))
                pygame.draw.rect(s, (200, 60, 50), (tx + 5, height - 116, 4, 8))
                bw += 34
        x += bw + rng.randint(10, 30)
    return s


def fence_layer(width, height):
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    for x in range(0, width, 40):
        pygame.draw.line(s, (90, 90, 96), (x, height - 36), (x, height), 2)
    for x in range(0, width, 6):
        pygame.draw.line(s, (130, 130, 136), (x, height - 32), (x + 6, height - 26))
        pygame.draw.line(s, (130, 130, 136), (x + 6, height - 32), (x, height - 26))
    for y in (height - 36, height - 33):
        for x in range(0, width, 4):
            s.set_at((x, y + (x // 4) % 2), (160, 160, 168))
    return s


def sea_strip(width, height, seed):
    s = pygame.Surface((width, height))
    s.fill((30, 90, 160))
    rng = random.Random(seed)
    for y in range(0, height, 5):
        for _ in range(width // 18):
            x = rng.randrange(width)
            pygame.draw.line(s, (120, 190, 240), (x, y), (x + rng.randint(4, 10), y))
    return s


# ---------- effects and HUD ----------
def explosion_frames(size=26, seed=3):
    rng = random.Random(seed)
    frames = []
    for i in range(6):
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        r = 3 + i * 2
        cols = [(255, 255, 255), (255, 240, 140), (255, 170, 50), (220, 70, 30), (120, 60, 50), (90, 90, 90)]
        for k in range(4):
            rr = max(1, r - k * 2 - (i > 3) * 2)
            col = cols[min(5, i + k)]
            pygame.draw.circle(s, col, (c + rng.randint(-1, 1), c + rng.randint(-1, 1)), rr)
        for _ in range(8 + i * 2):
            a = rng.uniform(0, math.tau)
            d = rng.uniform(r * 0.6, r + 3)
            s.set_at((int(c + math.cos(a) * d), int(c + math.sin(a) * d)), cols[min(5, i + 1)])
        frames.append(s)
    return frames


def medal():
    s = pygame.Surface((7, 12), pygame.SRCALPHA)
    pygame.draw.rect(s, (40, 70, 200), (1, 0, 5, 5))
    pygame.draw.line(s, (240, 240, 255), (3, 0), (3, 4))
    pygame.draw.circle(s, (120, 120, 140), (3, 8), 3)
    pygame.draw.circle(s, (220, 224, 240), (3, 8), 2)
    s.set_at((2, 7), (255, 255, 255))
    return s


def capsule_frames():
    frames = []
    for i in range(4):
        s = pygame.Surface((20, 12), pygame.SRCALPHA)
        flap = [0, 2, 4, 2][i]
        pygame.draw.ellipse(s, (120, 124, 136), (3, 2, 14, 8))
        pygame.draw.ellipse(s, (210, 214, 224), (4, 3, 12, 4))
        pygame.draw.polygon(s, (200, 60, 50), [(3, 6), (0, 2 + flap), (2, 7)])
        pygame.draw.polygon(s, (200, 60, 50), [(17, 6), (20, 2 + flap), (18, 7)])
        frames.append(s)
    return frames


def outlined_text(surf, font, msg, pos, col, outline=(20, 16, 24), center=True):
    img = font.render(msg, False, col)
    edge = font.render(msg, False, outline)
    x, y = pos
    if center:
        x -= img.get_width() // 2
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (2, 2), (-1, 1), (1, -1)):
        surf.blit(edge, (x + dx, y + dy))
    surf.blit(img, (x, y))
