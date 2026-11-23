"""Heather the music teacher, drawn in code in the same hand as her Alien Storm portrait
(long blonde hair, green eyes), plus the classroom furniture. Full resolution, cached."""
import math

import pygame

from ..alien_storm import art as A

SKIN, SHADE = A.SKIN["heather"]
HAIR, HAIR_HI = (240, 208, 110), (252, 232, 160)
CARDI, CARDI_SH = (46, 120, 124), (32, 90, 96)
BLOUSE = (246, 242, 232)
WOOD, WOOD_SH = (226, 178, 84), (176, 128, 52)
UW, UH = 114, 130                       # the figure's drawing units; shown at twice this size
_cache = {}

POSES = {   # pose: (face, chalk arm, ruler arm)
    "calm": ("calm", "down", "rest"),
    "pleased": ("smile", "down", "rest"),
    "write": ("smile", "write", "rest"),
    "delighted": ("grin", "cheer", "rest"),
    "stern": ("stern", "down", "raised"),
    "strike": ("shout", "down", "strike"),
}


def _limb(s, col, a, b, w):
    A.line(s, col, a, b, w)
    for p in (a, b):
        A.oval(s, col, (p[0] - w / 2, p[1] - w / 2, w, w))


def _ruler(s, grip, angle, length=46.0):
    """A wooden ruler held at `grip`, pointing along `angle` (radians)."""
    dx, dy = math.cos(angle), math.sin(angle)
    nx, ny = -dy * 2.6, dx * 2.6
    a = (grip[0] - dx * 6, grip[1] - dy * 6)
    b = (grip[0] + dx * length, grip[1] + dy * length)
    A.poly(s, WOOD, [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)])
    A.line(s, WOOD_SH, (a[0] - nx, a[1] - ny), (b[0] - nx, b[1] - ny), 0.7)
    for i in range(1, 12):
        t = i / 12.0
        p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        k = 0.9 if i % 2 else 0.5
        A.line(s, (110, 76, 30), (p[0] + nx, p[1] + ny), (p[0] + nx * (1 - k), p[1] + ny * (1 - k)), 0.5)


def heather(pose="calm"):
    """Heather from the waist up, 228 by 260 pixels."""
    if pose in _cache:
        return _cache[pose]
    face, chalk, ruler = POSES[pose]
    s = pygame.Surface((UW * A.SS, UH * A.SS), pygame.SRCALPHA)
    cx = 57.0
    # hair falling behind the shoulders
    A.poly(s, HAIR, [(33, 30), (31, 92), (40, 98), (74, 98), (83, 92), (81, 30), (70, 12), (44, 12)])
    A.poly(s, (214, 180, 86), [(31, 70), (31, 92), (40, 98), (44, 98), (38, 70)], mirror=cx)
    # the ruler arm when it is up behind her shoulder
    sh_l, sh_r = (30.0, 72.0), (84.0, 72.0)
    if ruler == "raised":
        elbow, hand = (98, 58), (92, 30)
        _limb(s, CARDI, sh_r, elbow, 11); _limb(s, CARDI, elbow, hand, 9.5)
        _ruler(s, hand, -math.pi / 2 - 0.25)
        A.oval(s, SKIN, (hand[0] - 5, hand[1] - 5.5, 10, 11))
    # blouse, cardigan
    A.poly(s, CARDI, [(18, 130), (22, 78), (38, 66), (76, 66), (92, 78), (96, 130)])
    A.poly(s, CARDI_SH, [(18, 130), (22, 78), (30, 74), (30, 130)])
    A.poly(s, BLOUSE, [(46, 66), (68, 66), (63, 130), (51, 130)])
    A.poly(s, CARDI_SH, [(46, 66), (51, 130), (48, 130), (42, 68)], mirror=cx)
    for by in (92, 104, 116):
        A.oval(s, (214, 206, 190), (cx - 1.2, by, 2.4, 2.4))
    A.poly(s, BLOUSE, [(46, 66), (57, 76), (50, 80), (43, 68)], mirror=cx)            # collar
    A.oval(s, (236, 196, 70), (cx - 2.5, 77, 5, 5))                                    # a treble clef brooch
    A.line(s, (150, 110, 30), (cx, 78), (cx, 81), 0.6)
    # neck and head
    A.poly(s, SHADE, [(50, 54), (64, 54), (65, 68), (57, 74), (49, 68)])
    A.oval(s, SKIN, (40, 14, 34, 42))
    A.oval(s, SKIN, (37, 31, 5, 9), mirror=cx)
    A.poly(s, SHADE, [(43, 44), (57, 56.5), (71, 44), (67, 51), (57, 57.5), (47, 51)])
    # hair in front: a side parting and long sides
    A.poly(s, HAIR, [(33, 62), (33.5, 26), (43, 12), (71, 12), (80.5, 26), (81, 62), (76, 58), (76, 30), (69, 20), (47, 20), (38, 30), (38, 58)])
    A.poly(s, HAIR, [(40, 30), (46, 19), (66, 19), (52, 25)])
    A.poly(s, HAIR_HI, [(46, 14), (62, 13), (66, 19), (50, 19)])
    A.line(s, (214, 180, 86), (35.5, 34), (35.5, 58), 0.8, mirror=cx)
    # eyes
    tilt = {"stern": 2.6, "shout": 3.2}.get(face, 0.0)
    for ex in (49.0, 65.0):
        if face == "grin":
            pygame.draw.arc(s, (60, 40, 30), ((ex - 4) * A.SS, 31 * A.SS, 8 * A.SS, 7 * A.SS), 0.3, math.pi - 0.3, int(1.1 * A.SS))
            continue
        A.oval(s, (255, 255, 255), (ex - 4, 30, 8, 5.8))
        A.oval(s, (80, 150, 120), (ex - 2, 30.5, 4.2, 4.6))
        A.oval(s, (16, 14, 16), (ex - 1, 31.6, 2.2, 2.4))
        A.oval(s, (255, 255, 255), (ex + 0.2, 31.4, 1.1, 1.1))
        A.line(s, (60, 40, 30), (ex - 4, 30.2), (ex + 4, 29.9), 0.6)
    A.line(s, (190, 150, 70), (44.5, 27.2 - tilt * 0.3), (53.5, 27.2 + tilt), 1.2)
    A.line(s, (190, 150, 70), (69.5, 27.2 - tilt * 0.3), (60.5, 27.2 + tilt), 1.2)
    # nose and mouth
    A.poly(s, SHADE, [(56.2, 35), (54.2, 43), (59.8, 43)])
    lip = (214, 70, 96)
    if face == "grin":
        A.poly(s, (60, 24, 30), [(48.5, 46), (65.5, 46), (62, 52.5), (52, 52.5)])
        A.poly(s, (255, 255, 255), [(50, 46.5), (64, 46.5), (62.8, 49), (51.2, 49)])
    elif face == "smile":
        A.line(s, lip, (50, 47), (53, 49.2), 1.2); A.line(s, lip, (53, 49.2), (61, 49.2), 1.2); A.line(s, lip, (61, 49.2), (64, 47), 1.2)
    elif face == "stern":
        A.line(s, lip, (51, 49.6), (54, 48), 1.2); A.line(s, lip, (54, 48), (60, 48), 1.2); A.line(s, lip, (60, 48), (63, 49.6), 1.2)
    elif face == "shout":
        A.oval(s, (60, 24, 30), (51.5, 45, 11, 8.5)); A.oval(s, (255, 255, 255), (53, 45.6, 8, 2.2))
        A.oval(s, (200, 80, 90), (54, 50, 6, 3))
    else:
        A.line(s, lip, (51, 48.2), (63, 48.2), 1.2)
    # the chalk arm (on the blackboard side)
    if chalk == "write":
        elbow, hand = (14, 66), (10, 36)
    elif chalk == "cheer":
        elbow, hand = (12, 60), (16, 30)
    else:
        elbow, hand = (22, 100), (36, 116)
    _limb(s, CARDI, sh_l, elbow, 11); _limb(s, CARDI, elbow, hand, 9.5)
    A.oval(s, SKIN, (hand[0] - 5, hand[1] - 5.5, 10, 11))
    if chalk == "write":
        A.line(s, (255, 255, 255), (hand[0] - 2, hand[1] - 3), (hand[0] - 8, hand[1] - 9), 1.6)
    elif chalk == "cheer":                                                              # thumb up
        A.line(s, SKIN, (hand[0], hand[1] - 4), (hand[0] + 1, hand[1] - 11), 3.2)
    # the ruler arm in front
    if ruler == "rest":
        elbow, hand = (94, 100), (80, 112)
        _limb(s, CARDI, sh_r, elbow, 11); _limb(s, CARDI, elbow, hand, 9.5)
        _ruler(s, hand, -math.pi / 2 + 0.5, 40)
        A.oval(s, SKIN, (hand[0] - 5, hand[1] - 5.5, 10, 11))
    elif ruler == "strike":
        elbow, hand = (92, 98), (70, 118)
        _limb(s, CARDI, sh_r, elbow, 11); _limb(s, CARDI, elbow, hand, 9.5)
        _ruler(s, hand, math.pi - 0.12, 60)
        A.oval(s, SKIN, (hand[0] - 5, hand[1] - 5.5, 10, 11))
        for i, a0 in enumerate((-2.2, -1.9, -1.6)):                                     # swish lines
            r0, r1 = 34 + i * 4, 44 + i * 4
            A.line(s, (255, 255, 255), (70 + math.cos(a0) * r0, 118 + math.sin(a0) * r0),
                   (70 + math.cos(a0) * r1, 118 + math.sin(a0) * r1), 0.9)
    out = pygame.transform.smoothscale(s, (UW * 2, UH * 2))
    _cache[pose] = out
    return out


def desk(width=240, height=92):
    """The teacher's desk seen from the pupil's side, with an apple, a metronome and a stack of scores."""
    key = ("desk", width, height)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(s, (150, 96, 50), (0, 14, width, height - 14))
    pygame.draw.rect(s, (186, 126, 68), (0, 0, width, 18), border_radius=4)
    pygame.draw.rect(s, (118, 72, 36), (0, 16, width, 4))
    for x in (18, width // 2 + 8):
        pygame.draw.rect(s, (128, 80, 40), (x, 30, width // 2 - 26, height - 40), border_radius=4)
        pygame.draw.circle(s, (226, 190, 90), (x + (width // 2 - 26) // 2, 52), 5)
    _cache[key] = s
    return s


def props():
    """Things standing on the desk: drawn behind the desk's front edge."""
    if "props" in _cache:
        return _cache["props"]
    s = pygame.Surface((240, 70), pygame.SRCALPHA)
    pygame.draw.polygon(s, (90, 56, 30), [(196, 70), (206, 14), (222, 14), (232, 70)])       # metronome
    pygame.draw.polygon(s, (130, 86, 46), [(200, 66), (208, 20), (220, 20), (228, 66)])
    pygame.draw.line(s, (230, 230, 230), (214, 62), (206, 24), 2)
    pygame.draw.rect(s, (226, 190, 90), (204, 34, 8, 6))
    pygame.draw.circle(s, (206, 44, 50), (22, 54), 15)                                       # apple
    pygame.draw.circle(s, (240, 110, 110), (17, 48), 5)
    pygame.draw.line(s, (90, 56, 30), (22, 40), (25, 32), 3)
    pygame.draw.ellipse(s, (80, 160, 80), (25, 28, 14, 7))
    _cache["props"] = s
    return s


def check(color=(255, 255, 255)):
    key = ("check", color)
    if key not in _cache:
        s = pygame.Surface((11, 10), pygame.SRCALPHA)
        pygame.draw.lines(s, color, False, [(1, 5), (4, 8), (9, 1)], 2)
        _cache[key] = s
    return _cache[key]
