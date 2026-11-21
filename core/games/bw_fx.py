"""Effects for Quick's charged specials: the charge aura, Sky Pound's quake,
Blue Roar's discharge ring and the Crimson Cyclone katana. All drawn in code."""
import math
import random

import pygame

from .bw_art import BLUE, OUT

GOLD = [(120, 80, 10), (220, 160, 30), (255, 220, 90), (255, 248, 200)]
RED = [(90, 0, 10), (190, 20, 30), (255, 60, 60), (255, 190, 180)]
LEVEL_COLS = {1: GOLD, 2: BLUE, 3: RED}
NAMES = {1: "SKY POUND", 2: "BLUE ROAR", 3: "CRIMSON CYCLONE"}


def _glow(surf, col, center, r, alpha):
    if r <= 0 or alpha <= 0:
        return
    g = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
    for k in range(4):                     # soft falloff: faint outside, brighter in the middle
        rr = int(r * (1 - k * 0.22))
        pygame.draw.circle(g, col + (int(alpha * 0.3),), (r + 1, r + 1), max(1, rr))
    surf.blit(g, (int(center[0] - r - 1), int(center[1] - r - 1)))


def aura(surf, x, y, level, t, front):
    """Flames of light rising round Quick while he charges. Drawn twice: behind (front=False) and in front."""
    cols = LEVEL_COLS[max(1, level)]
    cx, cy = x, y - 26
    if not front:
        _glow(surf, cols[2], (cx, cy), 30 + int(math.sin(t * 20) * 3), 70 + 15 * level)
    rng = random.Random(int(t * 30))
    for k in range(10 + 6 * level):
        side = rng.uniform(-1, 1)
        if (abs(side) < 0.45) != front:
            continue
        fx = cx + side * (16 + 4 * level)
        h = rng.uniform(10, 26 + 6 * level)
        y0 = y - rng.uniform(0, 44)
        pygame.draw.line(surf, cols[rng.choice((2, 3))], (fx, y0), (fx + rng.uniform(-2, 2), y0 - h), 1)
    if front and level >= 2:            # crackling arcs
        for k in range(level):
            a = rng.uniform(0, math.tau)
            pts = [(cx + math.cos(a) * 8, cy + math.sin(a) * 12)]
            for j in range(4):
                a += rng.uniform(-0.7, 0.7)
                r = 10 + j * 6
                pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r * 1.2))
            pygame.draw.lines(surf, cols[3], False, pts, 1)
    if front:
        ring = 22 + (t * 60) % 14
        pygame.draw.ellipse(surf, cols[2], (cx - ring, y - ring * 0.25, ring * 2, ring * 0.5), 1)


def burst(surf, x, y, level, k):
    """A flash when the charge climbs a level. k runs 0 to 1."""
    cols = LEVEL_COLS[level]
    r = int(8 + 40 * k)
    pygame.draw.circle(surf, cols[3], (int(x), int(y - 26)), r, max(1, int(4 * (1 - k))))
    for a in range(0, 360, 30):
        ra = math.radians(a + 15 * k)
        pygame.draw.line(surf, cols[2], (x + math.cos(ra) * r * 0.6, y - 26 + math.sin(ra) * r * 0.6),
                         (x + math.cos(ra) * r * 1.1, y - 26 + math.sin(ra) * r * 1.1), 1)


def skybeam(surf, x, top_y, k):
    """The streak Quick leaves as he rockets up, or comes screaming down."""
    w = max(1, int(10 * (1 - k)))
    pygame.draw.line(surf, GOLD[2], (x, 0), (x, top_y), w + 2)
    pygame.draw.line(surf, GOLD[3], (x, 0), (x, top_y), max(1, w // 2))


def target_mark(surf, x, y, t):
    """Where Sky Pound will land: a shrinking gold reticle on the street."""
    r = 10 + 6 * abs(math.sin(t * 10))
    pygame.draw.ellipse(surf, GOLD[2], (x - r * 1.6, y - r * 0.4, r * 3.2, r * 0.8), 2)
    pygame.draw.line(surf, GOLD[3], (x - 4, y), (x + 4, y))


def quake(surf, x, y, k, seed):
    """Sky Pound's impact. k runs 0 to 1."""
    rng = random.Random(seed)
    # cracks in the street
    for j in range(9):
        a = rng.uniform(0, math.tau)
        L = (18 + rng.uniform(0, 40)) * min(1.0, k * 4)
        px, py = x, y
        for s in range(3):
            a += rng.uniform(-0.5, 0.5)
            nx, ny = px + math.cos(a) * L / 3, py + math.sin(a) * L / 3 * 0.35
            pygame.draw.line(surf, (20, 14, 18), (px, py), (nx, ny), 2)
            pygame.draw.line(surf, GOLD[2] if k < 0.3 else (90, 70, 60), (px, py - 1), (nx, ny - 1), 1)
            px, py = nx, ny
    # two shock rings along the ground
    for off, col in ((0.0, GOLD[3]), (0.12, GOLD[2])):
        kk = max(0.0, k - off) / (1 - off)
        if 0 < kk < 1:
            r = 10 + 110 * kk
            pygame.draw.ellipse(surf, col, (x - r, y - r * 0.28, r * 2, r * 0.56), max(1, int(5 * (1 - kk))))
    # dust
    for j in range(14):
        a = rng.uniform(math.pi, math.tau) if j % 2 else rng.uniform(0, math.tau)
        d = 20 + 70 * k * rng.uniform(0.6, 1.0)
        dx, dy = x + math.cos(a) * d, y - 4 + math.sin(a) * d * 0.3 - 16 * k
        r = int(3 + 6 * k * rng.uniform(0.5, 1.0))
        shade = int(120 - 50 * k)
        pygame.draw.circle(surf, (shade, shade - 12, shade - 26), (int(dx), int(dy)), r)
        pygame.draw.circle(surf, (shade + 30, shade + 18, shade), (int(dx) - 1, int(dy) - 1), max(1, r - 2))
    if k < 0.12:                           # flash at the fist
        pygame.draw.circle(surf, GOLD[3], (int(x), int(y - 4)), int(18 * (1 - k / 0.12)))


def debris(surf, x, y, z, rot):
    pts = [(x + math.cos(rot + a) * 3, y - z + math.sin(rot + a) * 3) for a in (0, 2.1, 4.2)]
    pygame.draw.polygon(surf, (110, 96, 90), pts)
    pygame.draw.polygon(surf, OUT, pts, 1)


def gather(surf, x, y, k, t):
    """Blue light pulled into Quick before the roar. k runs 0 to 1."""
    rng = random.Random(3)
    for j in range(22):
        a = rng.uniform(0, math.tau) + t * 2
        d = (1 - k) * rng.uniform(40, 110) + 6
        px, py = x + math.cos(a) * d, y - 26 + math.sin(a) * d * 0.7
        tail = 6 + 10 * (1 - k)
        pygame.draw.line(surf, BLUE[3], (px, py), (px + math.cos(a) * tail, py + math.sin(a) * tail * 0.7), 1)
    _glow(surf, BLUE[2], (x, y - 26), int(6 + 18 * k), 120)


def roar_ring(surf, x, y, r, k, t):
    """Blue Roar's discharge, radiating out from Quick. r is the ring radius, k the fade 0 to 1."""
    cx, cy = x, y - 22
    if r <= 0:
        return
    rr = int(r)
    alpha = int(200 * (1 - k))
    ring = pygame.Surface((rr * 2 + 12, rr * 2 + 12), pygame.SRCALPHA)
    c = (rr + 6, rr + 6)
    pygame.draw.circle(ring, BLUE[1] + (alpha // 3,), c, rr)
    pygame.draw.circle(ring, (0, 0, 0, 0), c, max(0, rr - 14))
    pygame.draw.circle(ring, BLUE[2] + (alpha,), c, rr, 5)
    pygame.draw.circle(ring, BLUE[3] + (alpha,), c, max(1, rr - 2), 2)
    surf.blit(ring, (cx - rr - 6, cy - rr - 6))
    rng = random.Random(int(t * 24))
    for j in range(16):                    # lightning flicking off the ring
        a = rng.uniform(0, math.tau)
        px, py = cx + math.cos(a) * r, cy + math.sin(a) * r
        pts = [(px, py)]
        for s in range(3):
            a2 = a + rng.uniform(-0.5, 0.5)
            px, py = px + math.cos(a2) * 7, py + math.sin(a2) * 7
            pts.append((px, py))
        pygame.draw.lines(surf, BLUE[3] if j % 3 else (255, 255, 255), False, pts, 1)
    # ground ring
    pygame.draw.ellipse(surf, BLUE[2], (x - r, y - r * 0.25, r * 2, r * 0.5), 2)


def tint(surf, col, alpha):
    if alpha <= 0:
        return
    f = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    f.fill(col + (int(alpha),))
    surf.blit(f, (0, 0))


def crimson_katana(surf, base, angle, length, t, ghost=0):
    """The Ninth Dominion blade, burning red and humming so hard it shakes."""
    rng = random.Random(int(t * 90) + ghost * 7)
    jx, jy = rng.uniform(-1.4, 1.4), rng.uniform(-1.4, 1.4)
    x, y = base[0] + jx, base[1] + jy
    ex, ey = x + math.cos(angle) * length, y + math.sin(angle) * length
    if ghost:
        pygame.draw.line(surf, RED[1], (x, y), (ex, ey), max(1, 4 - ghost))
        return
    _glow(surf, RED[2], ((x + ex) / 2, (y + ey) / 2), int(length * 0.4), 45)
    pygame.draw.line(surf, OUT, (x, y), (ex, ey), 5)
    pygame.draw.line(surf, RED[2], (x, y), (ex, ey), 3)
    pygame.draw.line(surf, RED[3], (x, y), (ex, ey), 1)
    hx, hy = x - math.cos(angle) * 9, y - math.sin(angle) * 9
    pygame.draw.line(surf, (30, 30, 60), (x, y), (hx, hy), 3)
    pygame.draw.circle(surf, RED[2], (int(x), int(y)), 3)


def slash_arc(surf, cx, cy, a0, a1, r, k):
    """A red swoosh left behind the spinning blade."""
    if k >= 1:
        return
    steps = 8
    pts = [(cx + math.cos(a0 + (a1 - a0) * i / steps) * r, cy + math.sin(a0 + (a1 - a0) * i / steps) * r * 0.55)
           for i in range(steps + 1)]
    pygame.draw.lines(surf, RED[2] if k < 0.5 else RED[1], False, pts, max(1, int(4 * (1 - k))))
