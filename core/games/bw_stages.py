"""Black Warrior stages for Levels 2 to 6: streets, set pieces and boss arenas, at night and after each reform."""
import math
import random

import pygame

from . import bw_art as A
from .bw_art import BLUE, GOLD, H, OUT, W, _cache


def _bright(col, morning, amt=70):
    return tuple(min(255, c + amt) for c in col) if morning else col


def _label(s, x, top, text, col, size=14):
    img = A.font(size).render(text, False, col)
    pygame.draw.rect(s, (16, 12, 22), (x - img.get_width() // 2 - 4, top, img.get_width() + 8, img.get_height() + 2))
    s.blit(img, (x - img.get_width() // 2, top + 2))


def _windows(s, x, w, top, bottom, lit, seed, col=(255, 210, 122), dark=(60, 50, 80)):
    rng = random.Random(seed)
    for wy in range(top, bottom, 22):
        for wx in range(x + 8, x + w - 12, 20):
            pygame.draw.rect(s, col if rng.random() < lit else dark, (wx, wy, 11, 13))


def building(s, x, b, morning, t):
    kind, bw = b["kind"], b["w"]
    if kind == "shop":
        top = b.get("top", 70)
        pygame.draw.rect(s, _bright(b["col"], morning), (x, top, bw, 146 - top))
        _windows(s, x, bw, top + 10, 118, 0.6, x)
        _label(s, x + bw // 2, top + 4, b["label"], b.get("lcol", (255, 220, 120)))
        pygame.draw.rect(s, (30, 24, 36), (x + bw // 2 - 10, 120, 20, 26))
    elif kind == "hospital":
        pygame.draw.rect(s, _bright((200, 206, 214), morning, 30), (x, 36, bw, 110))
        for wy in range(52, 120, 18):
            for wx in range(x + 8, x + bw - 12, 18):
                pygame.draw.rect(s, (120, 170, 210) if (wx + wy) % 3 else (250, 240, 200), (wx, wy, 12, 11))
        pygame.draw.rect(s, (40, 110, 170), (x + bw // 2 - 12, 40, 24, 10))
        img = A.font(12).render("H", False, (255, 255, 255))
        s.blit(img, (x + bw // 2 - 3, 40))
        _label(s, x + bw // 2, 124, b["label"], (90, 200, 255))
        pygame.draw.rect(s, (40, 50, 60), (x + bw // 2 - 16, 132, 32, 14))
    elif kind == "glass":
        pygame.draw.rect(s, _bright((24, 30, 48), morning), (x, 30, bw, 116))
        for gx in range(x + 6, x + bw - 4, 24):
            pygame.draw.rect(s, _bright((40, 60, 96), morning), (gx, 46, 20, 80))
            pygame.draw.line(s, (90, 130, 190), (gx + 2, 48), (gx + 8, 48))
        pygame.draw.rect(s, b.get("trim", GOLD[1]), (x, 128, bw, 4))
        _label(s, x + bw // 2, 34, b["label"], b.get("lcol", GOLD[3]))
        pygame.draw.rect(s, (60, 40, 20), (x + bw - 60, 96, 40, 50))
    elif kind == "warehouse":
        top = 60
        base = _bright((90, 96, 110), morning, 50)
        pygame.draw.rect(s, base, (x, top, bw, 146 - top))
        for xx in range(x, x + bw, 4):
            pygame.draw.line(s, tuple(c - 18 for c in base), (xx, top + 4), (xx, 145))
        pygame.draw.polygon(s, tuple(c - 30 for c in base), [(x - 4, top), (x + bw // 2, top - 14), (x + bw + 4, top)])
        pygame.draw.rect(s, (40, 40, 46), (x + 16, 90, bw - 32, 56))
        for k in range(6):
            pygame.draw.line(s, (70, 70, 78), (x + 16, 94 + k * 9), (x + bw - 17, 94 + k * 9))
        img = A.font(28).render(b["label"], False, (240, 200, 60))
        s.blit(img, (x + bw // 2 - img.get_width() // 2, top + 6))
    elif kind == "containers":
        rng = random.Random(x)
        for row in range(3):
            for k in range(bw // 44):
                col = rng.choice([(170, 70, 50), (60, 110, 150), (190, 150, 60), (80, 120, 80)])
                r = pygame.Rect(x + k * 44 + row * 8, 146 - (row + 1) * 26, 42, 24)
                pygame.draw.rect(s, _bright(col, morning, 30), r)
                for xx in range(r.x + 2, r.right - 2, 3):
                    pygame.draw.line(s, tuple(c - 30 for c in col), (xx, r.y + 2), (xx, r.bottom - 3))
    elif kind == "rowhouse":
        rng = random.Random(x)
        brick = _bright(rng.choice([(130, 60, 50), (110, 70, 60), (140, 80, 60)]), morning, 40)
        pygame.draw.rect(s, brick, (x, 64, bw, 82))
        for yy in range(66, 146, 5):
            pygame.draw.line(s, tuple(c - 25 for c in brick), (x, yy), (x + bw, yy))
        pygame.draw.polygon(s, (60, 50, 50), [(x - 2, 64), (x + bw // 2, 52), (x + bw + 2, 64)])
        for wx in (x + 8, x + bw - 22):
            for wy in (74, 102):
                if morning:
                    pygame.draw.rect(s, (250, 230, 160), (wx, wy, 14, 16))
                    pygame.draw.rect(s, (90, 170, 80), (wx - 1, wy + 15, 16, 3))
                else:
                    pygame.draw.rect(s, (150, 120, 80), (wx, wy, 14, 16))
                    pygame.draw.line(s, (100, 80, 50), (wx, wy), (wx + 14, wy + 16), 2)
                    pygame.draw.line(s, (100, 80, 50), (wx + 14, wy), (wx, wy + 16), 2)
        pygame.draw.rect(s, (60, 40, 30), (x + bw // 2 - 7, 118, 14, 28))
        if not morning:
            pygame.draw.rect(s, (250, 250, 240), (x + bw // 2 - 5, 124, 10, 12))
            pygame.draw.line(s, (220, 40, 40), (x + bw // 2 - 3, 127), (x + bw // 2 + 3, 127))
        pygame.draw.rect(s, (150, 150, 150), (x + bw // 2 - 12, 140, 24, 6))
    elif kind == "mill":
        brick = _bright((110, 60, 46), morning, 40)
        pygame.draw.rect(s, brick, (x, 54, bw, 92))
        _windows(s, x, bw, 66, 130, 0.5, x, col=(255, 160, 60) if not morning else (200, 230, 250))
        for k, sx in enumerate(range(x + 14, x + bw - 10, 40)):
            pygame.draw.rect(s, (80, 46, 36), (sx, 4, 12, 52))
            pygame.draw.rect(s, (230, 230, 230), (sx, 8, 12, 3))
            if not morning:
                for p in range(4):
                    pt = (t * 0.6 + p * 0.25 + k * 0.3) % 1.0
                    pygame.draw.circle(s, (60, 56, 54), (int(sx + 6 + pt * 30), int(2 - pt * 30)), int(4 + pt * 10))
        if morning:
            for sx in range(x + 4, x + bw - 18, 22):
                pygame.draw.polygon(s, (40, 60, 110), [(sx, 54), (sx + 18, 54), (sx + 14, 46), (sx + 4, 46)])
                pygame.draw.line(s, (140, 180, 240), (sx + 5, 48), (sx + 13, 48))
        _label(s, x + bw // 2, 112, b["label"], (250, 170, 80))
    elif kind == "hallfront":
        stone = _bright((200, 196, 186), morning, 30)
        pygame.draw.rect(s, stone, (x, 50, bw, 96))
        pygame.draw.polygon(s, stone, [(x - 6, 50), (x + bw // 2, 24), (x + bw + 6, 50)])
        pygame.draw.ellipse(s, (170, 166, 150), (x + bw // 2 - 30, 0, 60, 40))
        for cx in range(x + 14, x + bw - 6, 26):
            pygame.draw.rect(s, (236, 232, 222), (cx, 56, 10, 86))
            pygame.draw.line(s, (180, 176, 166), (cx + 8, 56), (cx + 8, 142))
        _label(s, x + bw // 2, 36, b["label"], (40, 40, 60))
        for k in range(4):
            pygame.draw.rect(s, (160, 156, 146), (x - 10 - k * 4, 138 + k * 2, bw + 20 + k * 8, 2))
        if morning:
            for k in range(0, bw, 16):
                pygame.draw.polygon(s, [(220, 60, 60), (250, 250, 250), (60, 100, 200)][k // 16 % 3],
                                    [(x + k, 56), (x + k + 14, 56), (x + k + 7, 64)])
    elif kind == "lot":
        pygame.draw.rect(s, (40, 36, 50), (x, 110, bw, 40))
        for fx in range(x, x + bw, 6):
            pygame.draw.line(s, (120, 124, 136), (fx, 104), (fx + 6, 146))
            pygame.draw.line(s, (120, 124, 136), (fx + 6, 104), (fx, 146))
        pygame.draw.line(s, (150, 154, 166), (x, 104), (x + bw, 104), 2)


def _wood_floor(s, cam, morning):
    for y in range(146, H):
        t = (y - 146) / (H - 146)
        s.fill((int(110 - 30 * t + (40 if morning else 0)), int(80 - 20 * t + (30 if morning else 0)),
                int(56 - 14 * t + (20 if morning else 0))), (0, y, W, 1))
    for y in range(150, H, 9):
        pygame.draw.line(s, (60, 40, 28), (0, y), (W, y))
    for row, y in enumerate(range(150, H, 9)):
        off = (row % 3) * 22 - int(cam) % 66
        for x in range(off - 66, W, 66):
            pygame.draw.line(s, (60, 40, 28), (x, y), (x, y + 8))
            s.set_at((x + 3, y + 4), (170, 150, 120))


def _dirt_floor(s, cam, morning):
    for y in range(146, H):
        t = (y - 146) / (H - 146)
        s.fill((int(120 - 30 * t + (30 if morning else 0)), int(96 - 24 * t + (40 if morning else 0)),
                int(70 - 20 * t)), (0, y, W, 1))
    rng = random.Random(3)
    for _ in range(120):
        x = (rng.randrange(800) - int(cam)) % W
        s.set_at((x, rng.randrange(150, H)), (80, 64, 48))


DISTRICTS = {
    "hospital_street": {"sky": ((20, 24, 50), (70, 60, 110)), "floor": "cobble",
                        "buildings": [(0, 150, "shop", "24H PHARMACY", (46, 40, 70), (224, 64, 122)),
                                      (170, 220, "hospital", "MERCY GENERAL"), (420, 160, "shop", "MEDICAL SUPPLY", (60, 60, 76), (120, 220, 255)),
                                      (600, 150, "lot"), (780, 260, "hospital", "MERCY EMERGENCY"),
                                      (1080, 420, "glass", "MERCY BILLING TOWER")]},
    "docks": {"sky": ((40, 30, 70), (240, 150, 110)), "floor": "wood",
              "buildings": [(0, 180, "warehouse", "7"), (200, 240, "containers"), (470, 180, "warehouse", "8"),
                            (680, 220, "containers"), (930, 200, "warehouse", "9"), (1160, 260, "containers"),
                            (1440, 200, "warehouse", "10")]},
    "pier": {"sky": ((40, 30, 70), (250, 170, 120)), "floor": "wood", "water": True,
             "buildings": [(80, 260, "containers"), (520, 200, "warehouse", "11")]},
    "old_ward": {"sky": ((20, 20, 44), (80, 50, 90)), "floor": "cobble",
                 "buildings": [(x, 86, "rowhouse") for x in range(0, 1600, 92)]},
    "mill_street": {"sky": ((90, 60, 50), (210, 130, 70)), "floor": "cobble", "smog": True,
                    "buildings": [(0, 200, "mill", "BEND STEEL"), (220, 160, "shop", "CORNER STORE", (70, 50, 40), (250, 200, 120)),
                                  (400, 240, "mill", "SMOKE WORKS"), (660, 200, "lot"), (880, 260, "mill", "FURNACE 9"),
                                  (1160, 200, "mill", "BARON SMOG CO"), (1380, 220, "mill", "COAL YARD")]},
    "hall_steps": {"sky": ((24, 20, 54), (90, 70, 120)), "floor": "cobble",
                   "buildings": [(0, 200, "shop", "TOWN NEWS", (50, 50, 70), (250, 250, 250)), (220, 180, "shop", "VOTER OFFICE", (40, 60, 90), (120, 220, 255)),
                                 (420, 600, "hallfront", "CITY HALL"), (1040, 200, "shop", "RECORDS", (60, 50, 50), GOLD[2])]},
}
MORNING_LABELS = {"24H PHARMACY": "FREE CLINIC", "MERCY BILLING TOWER": "MERCY HEALTH CENTER", "MEDICAL SUPPLY": "OPEN TO ALL",
                  "BARON SMOG CO": "BEND SOLAR", "SMOKE WORKS": "WIND WORKS", "FURNACE 9": "GREEN JOBS HALL",
                  "COAL YARD": "RIVER PARK", "VOTER OFFICE": "VOTE HERE", "BEND STEEL": "BEND STEEL"}


def district(s, name, cam, t=0.0, morning=False):
    spec = DISTRICTS[name]
    top, bottom = spec["sky"]
    if morning:
        top, bottom = (250, 170, 110), (255, 226, 170)
        if spec.get("smog"):
            top, bottom = (110, 170, 240), (210, 236, 255)
    key = ("sky", name, morning)
    if key not in _cache:
        _cache[key] = A._gradient(top, bottom)
    s.blit(_cache[key], (0, 0))
    sky, far, mid = A._layers(morning)
    for layer, k, y in ((far, 0.2, 0), (mid, 0.5, 8)):
        x = -int(cam * k) % 800
        s.blit(layer, (x - 800, y))
        s.blit(layer, (x, y))
    if spec.get("water"):
        pygame.draw.rect(s, (40, 70, 110) if not morning else (80, 150, 210), (0, 100, W, 46))
        for i in range(30):
            x = (i * 53 - int(cam * 0.6)) % W
            pygame.draw.line(s, (120, 170, 220), (x, 104 + (i % 6) * 7), (x + 8, 104 + (i % 6) * 7))
    for b in spec["buildings"]:
        bx, bw, kind = b[0], b[1], b[2]
        x = bx - int(cam)
        if x > W or x + bw < 0:
            continue
        d = {"kind": kind, "w": bw}
        if len(b) > 3:
            d["label"] = MORNING_LABELS.get(b[3], b[3]) if morning else b[3]
        if len(b) > 4:
            d["col"], d["lcol"] = b[4], b[5]
        building(s, x, d, morning, t)
    if spec.get("smog") and not morning:
        haze = _cache.get("haze")
        if haze is None:
            haze = _cache["haze"] = pygame.Surface((W, 150), pygame.SRCALPHA)
            haze.fill((90, 70, 50, 70))
        s.blit(haze, (0, 0))
    floor = spec["floor"]
    if floor == "wood":
        _wood_floor(s, cam, morning)
    elif floor == "dirt":
        _dirt_floor(s, cam, morning)
    else:
        A._street_floor(s, cam, morning)
    if floor != "wood":
        for lx in range(80, 1700, 260):
            x = lx - int(cam)
            if -60 < x < W + 60:
                A._lamp(s, x, morning)


# ------------------------------------------------------------------ interiors and set pieces
def _interior(s, wall, floor_top, floor_bottom):
    for y in range(0, 146):
        s.fill(tuple(max(0, c - y // 10) for c in wall), (0, y, W, 1))
    for y in range(146, H):
        t = (y - 146) / (H - 146)
        s.fill(tuple(int(a + (b - a) * t) for a, b in zip(floor_top, floor_bottom)), (0, y, W, 1))


def billing_hall(s, cam, t=0.0):
    _interior(s, (70, 90, 100), (110, 120, 130), (70, 80, 90))
    for lx in range(0, 760, 60):
        x = lx - int(cam)
        if -60 < x < W:
            pygame.draw.rect(s, (230, 240, 250), (x + 10, 8, 40, 4))
    for cx in range(20, 760, 110):
        x = cx - int(cam)
        if -100 < x < W:
            pygame.draw.rect(s, (150, 156, 166), (x, 100, 90, 46))
            pygame.draw.rect(s, (110, 116, 126), (x, 100, 90, 6))
            pygame.draw.rect(s, (40, 50, 60), (x + 30, 112, 26, 18))
            pygame.draw.rect(s, (100, 200, 140), (x + 32, 114, 22, 14))
    for fx in range(60, 760, 220):
        x = fx - int(cam)
        if -60 < x < W:
            pygame.draw.rect(s, (130, 130, 140), (x, 54, 30, 46))
            for k in range(3):
                pygame.draw.rect(s, (100, 100, 110), (x + 2, 56 + k * 15, 26, 13))
                pygame.draw.rect(s, (200, 200, 210), (x + 11, 61 + k * 15, 8, 2))
    sx = 300 - int(cam)
    if -200 < sx < W:
        _label(s, sx + 60, 24, "CLAIMS DEPARTMENT", (250, 80, 80), 18)
    pygame.draw.rect(s, (60, 70, 80), (0, 146, W, 3))


def billing_floor(s, t=0.0, stamp=True):
    _interior(s, (60, 70, 86), (120, 120, 130), (80, 80, 90))
    pygame.draw.rect(s, (20, 26, 50), (40, 16, 320, 100))
    sky, far, mid = A._layers(False)
    s.blit(far, (40, -10), area=pygame.Rect(0, 40, 320, 110))
    for gx in range(40, 360, 40):
        pygame.draw.line(s, (90, 96, 110), (gx, 16), (gx, 116), 2)
    pygame.draw.rect(s, (90, 96, 110), (40, 16, 320, 100), 3)
    if stamp:
        for k, x in enumerate((20, 336)):
            pygame.draw.rect(s, (160, 30, 40), (x, 22, 44, 70))
            img = A.font(16).render("NO", False, (255, 220, 220))
            s.blit(img, (x + 22 - img.get_width() // 2, 48))
    for x in range(0, W, 100):
        pygame.draw.rect(s, (110, 70, 50), (x + 10, 124, 70, 22))
        pygame.draw.rect(s, (140, 100, 70), (x + 10, 124, 70, 4))


def ramp(s, prog, t=0.0):
    """Racing down the hospital parking ramp on a gurney: pillars and stripes rush past."""
    _interior(s, (80, 80, 86), (100, 100, 104), (60, 60, 66))
    off = int(prog * 40 + t * 260) % 120
    for x in range(-off, W + 120, 120):
        pygame.draw.rect(s, (130, 130, 136), (x, 10, 22, 136))
        pygame.draw.rect(s, (240, 200, 40), (x, 110, 22, 8))
        pygame.draw.rect(s, (30, 30, 34), (x, 118, 22, 4))
        img = A.font(18).render("P%d" % max(1, 4 - int(prog // 20)), False, (30, 30, 34))
        s.blit(img, (x + 3, 40))
    for x in range(-(int(t * 400) % 60), W, 60):
        pygame.draw.rect(s, (230, 230, 230), (x, 190, 30, 3))
    pygame.draw.rect(s, (70, 70, 74), (0, 6, W, 6))
    for x in range(-(int(t * 300) % 80), W, 80):
        pygame.draw.rect(s, (250, 250, 220), (x + 20, 12, 30, 3))


def gurney(surf, x, y, rider=None):
    pygame.draw.rect(surf, OUT, (x - 26, y - 14, 52, 6))
    pygame.draw.rect(surf, (220, 224, 232), (x - 25, y - 13, 50, 4))
    for wx in (x - 20, x + 18):
        pygame.draw.line(surf, (150, 154, 166), (wx, y - 9), (wx, y - 2), 2)
        pygame.draw.circle(surf, OUT, (wx, y), 3)


def conveyor(s, prog, t=0.0, belt=1):
    _interior(s, (70, 64, 60), (60, 60, 64), (40, 40, 44))
    for sx in range(0, W, 80):
        pygame.draw.rect(s, (110, 90, 70), (sx + 4, 20, 70, 110))
        for k in range(4):
            pygame.draw.rect(s, (150, 130, 100), (sx + 4, 30 + k * 26, 70, 4))
            for bx in range(sx + 8, sx + 70, 14):
                pygame.draw.rect(s, (200, 150, 90), (bx, 18 + k * 26, 11, 11))
    pygame.draw.rect(s, (30, 30, 34), (0, 150, W, 80))
    off = int(t * 60 * belt) % 16
    for x in range(-16 + off, W + 16, 16):
        pygame.draw.line(s, (60, 60, 66), (x, 152), (x, 226))
    for y in (150, 228):
        pygame.draw.rect(s, (240, 200, 40), (0, y - 2, W, 4))
    arrow = ">" if belt > 0 else "<"
    for x in range(20, W, 80):
        img = A.font(20).render(arrow * 3, False, (240, 200, 40))
        s.blit(img, (x, 130))


def pier_end(s, t=0.0):
    district(s, "pier", 300, t)
    fog = _cache.get("fog")
    if fog is None:
        fog = _cache["fog"] = pygame.Surface((W, 120), pygame.SRCALPHA)
        for y in range(120):
            fog.fill((120, 120, 140, int(80 * (1 - y / 120))), (0, y, W, 1))
    s.blit(fog, (0, 30))
    for k in range(5):
        x = 20 + k * 90
        pygame.draw.rect(s, (60, 44, 32), (x, 140, 8, 24))


def scaffold(s, prog, t=0.0):
    s.blit(A._gradient((30, 24, 60), (110, 70, 100)), (0, 0))
    rise = prog * 2
    for k in range(10):
        x = k * 46
        pygame.draw.rect(s, (110, 60, 50), (x, 90 + rise, 42, 200))
        pygame.draw.polygon(s, (70, 50, 50), [(x - 2, 90 + rise), (x + 21, 80 + rise), (x + 44, 90 + rise)])
    for x in range(0, W, 50):
        pygame.draw.rect(s, (200, 160, 40), (x, 0, 4, 150))
    for y in range(20, 150, 40):
        pygame.draw.rect(s, (200, 160, 40), (0, y, W, 3))
        for x in range(0, W, 50):
            pygame.draw.line(s, (160, 120, 20), (x, y), (x + 50, y + 40))
    for y in range(146, H):
        s.fill((120, 96, 70), (0, y, W, 1))
    for y in range(150, H, 10):
        pygame.draw.line(s, (80, 60, 44), (0, y), (W, y))
    pygame.draw.rect(s, (200, 160, 40), (0, 144, W, 4))


def crane_site(s, t=0.0):
    district(s, "old_ward", 900, t)
    for y in range(146, H):
        s.fill((120, 96, 70), (0, y, W, 1))
    rng = random.Random(9)
    for _ in range(14):
        x, y = rng.randrange(W), rng.randrange(160, 230)
        pygame.draw.rect(s, (130, 60, 50), (x, y, rng.randint(6, 14), 5))


def barge(s, prog, t=0.0):
    s.blit(A._gradient((90, 60, 50), (220, 140, 80)), (0, 0))
    sky, far, mid = A._layers(False)
    s.blit(mid, (-int(t * 20) % 400 - 400, 40))
    s.blit(mid, (-int(t * 20) % 400, 40))
    pygame.draw.rect(s, (50, 70, 80), (0, 120, W, 30))
    for i in range(20):
        x = (i * 41 - int(t * 80)) % W
        pygame.draw.line(s, (110, 140, 150), (x, 126 + (i % 4) * 6), (x + 10, 126 + (i % 4) * 6))
    bx = W - ((prog * 40 + t * 30) % 700)       # a steel bridge sweeps overhead
    pygame.draw.rect(s, (60, 60, 70), (bx, 0, 160, 22))
    for k in range(8):
        pygame.draw.line(s, (90, 90, 100), (bx + k * 20, 0), (bx + k * 20 + 20, 22), 2)
    pygame.draw.rect(s, (70, 70, 80), (bx + 70, 22, 20, 100))
    pygame.draw.rect(s, (40, 36, 34), (0, 146, W, H - 146))
    for x in range(0, W, 40):
        pygame.draw.line(s, (60, 54, 50), (x, 146), (x - 10, H))
    pygame.draw.rect(s, (200, 120, 40), (0, 144, W, 4))
    for k in range(3):
        cx = (k * 140 - int(t * 15)) % (W + 80) - 40
        pygame.draw.ellipse(s, (30, 28, 26), (cx, 150, 70, 20))


def mill_yard(s, t=0.0, clear=False):
    district(s, "mill_street", 1150, t, morning=clear)
    glow = int(abs(math.sin(t * 2)) * 60)
    if not clear:
        pygame.draw.rect(s, (255, 120 + glow // 2, 40), (300, 110, 60, 36))
        pygame.draw.rect(s, OUT, (300, 110, 60, 36), 2)
    _dirt_floor(s, 0, clear)


def hallway(s, prog, t=0.0):
    _interior(s, (150, 140, 120), (200, 190, 170), (140, 130, 110))
    off = int(prog * 8) % 100
    for x in range(-off, W + 100, 100):
        pygame.draw.rect(s, (90, 60, 40), (x + 20, 50, 36, 96))
        pygame.draw.rect(s, GOLD[1], (x + 20, 50, 36, 96), 2)
        pygame.draw.circle(s, GOLD[2], (x + 50, 100), 2)
        pygame.draw.rect(s, GOLD[1], (x + 66, 30, 26, 32))
        pygame.draw.rect(s, (60, 50, 70), (x + 69, 33, 20, 26))
    for y in range(150, H, 14):
        off2 = ((y // 14) % 2) * 16 - int(prog * 8) % 32
        for x in range(off2 - 32, W, 32):
            pygame.draw.rect(s, (90, 80, 70), (x, y, 16, 14))
    pygame.draw.rect(s, (200, 40, 40), (0, 146, W, 3))
    for x in range(0, W, 30):       # red tape everywhere
        pygame.draw.line(s, (220, 40, 40), (x, 10), (x + 40, 60), 2)


def chamber(s, t=0.0, clear=False):
    _interior(s, (110, 90, 80) if not clear else (170, 150, 130), (150, 120, 90), (100, 80, 60))
    for k in range(3):
        x = 60 + k * 110
        pygame.draw.rect(s, OUT, (x - 2, 12, 64, 46))
        pygame.draw.rect(s, (30, 30, 36), (x, 14, 60, 42))
        if clear:
            pygame.draw.rect(s, (120, 200, 255), (x + 2, 16, 56, 38))
            img = A.font(14).render("VOTE", False, (255, 255, 255))
            s.blit(img, (x + 30 - img.get_width() // 2, 28))
        else:
            rs = int(t * 20)
            for y in range(16, 54, 3):
                for xx in range(x + 2, x + 58, 4):
                    v = ((xx * 13 + y * 7 + rs * 11) % 6) * 40
                    s.fill((v, v, v), (xx, y, 4, 3))
    for row in range(3):
        for x in range(10 + row * 14, W - 10, 34):
            pygame.draw.rect(s, (120, 70, 50), (x, 82 + row * 20, 26, 14))
            pygame.draw.rect(s, (90, 50, 36), (x, 92 + row * 20, 26, 4))
    pygame.draw.rect(s, (90, 60, 40), (150, 120, 100, 26))
    pygame.draw.rect(s, GOLD[1], (150, 120, 100, 4))
    if not clear:
        for x in range(0, W, 26):
            pygame.draw.line(s, (220, 40, 40), (x, 0), (x + 30, 80), 2)


def stage(s, name, cam, t, morning=False):
    """Draw any walk stage by name."""
    if name == "tower_street":
        A.street(s, cam, t, morning)
    elif name == "tower_lobby":
        A.lobby(s, cam, t)
    elif name == "billing_hall":
        billing_hall(s, cam, t)
    else:
        district(s, name, cam, t, morning)


def ride(s, name, prog, t, doors=0.0, belt=1):
    if name == "elevator":
        A.elevator(s, prog, t, doors)
    elif name == "ramp":
        ramp(s, prog, t)
    elif name == "conveyor":
        conveyor(s, prog, t, belt)
    elif name == "scaffold":
        scaffold(s, prog, t)
    elif name == "barge":
        barge(s, prog, t)
    else:
        hallway(s, prog, t)


def arena(s, name, t, clear=False):
    if name == "penthouse":
        A.penthouse(s, t, 1.0 if clear else 0.0)
    elif name == "billing_floor":
        billing_floor(s, t, not clear)
    elif name == "pier_end":
        pier_end(s, t)
    elif name == "crane_site":
        crane_site(s, t)
    elif name == "mill_yard":
        mill_yard(s, t, clear)
    else:
        chamber(s, t, clear)


# ------------------------------------------------------------------ reform props
def food_truck(s, x, y):
    pygame.draw.rect(s, OUT, (x - 1, y - 1, 72, 36), border_radius=4)
    pygame.draw.rect(s, (240, 120, 60), (x, y, 70, 34), border_radius=4)
    pygame.draw.rect(s, (250, 240, 200), (x + 8, y + 6, 36, 14))
    img = A.font(12).render("TACOS", False, (40, 30, 20))
    s.blit(img, (x + 10, y + 8))
    for wx in (x + 14, x + 56):
        pygame.draw.circle(s, OUT, (wx, y + 34), 6)


def garden(s, x, y):
    for k in range(6):
        pygame.draw.rect(s, (110, 70, 40), (x + k * 22, y, 20, 10))
        for f in range(3):
            pygame.draw.circle(s, [(250, 80, 120), (250, 220, 60), (120, 200, 255)][f], (x + k * 22 + 4 + f * 6, y - 3), 3)
            pygame.draw.line(s, (60, 150, 60), (x + k * 22 + 4 + f * 6, y), (x + k * 22 + 4 + f * 6, y - 3))


def bunting(s, y, t):
    for x in range(0, W, 14):
        col = [(220, 60, 60), (250, 220, 60), (60, 140, 230), (90, 200, 120)][(x // 14) % 4]
        dy = int(math.sin(t * 3 + x * 0.1) * 2)
        pygame.draw.polygon(s, col, [(x, y + dy), (x + 12, y + dy), (x + 6, y + 10 + dy)])
    pygame.draw.line(s, (60, 60, 60), (0, y), (W, y))
