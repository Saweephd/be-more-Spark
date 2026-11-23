"""The collectible cards. The frame, back, symbols, names and pictures are this project's own."""
import math

import pygame

from ..alien_storm import hud

CW, CH = 250, 350
_cache = {}

# key: name, type, colour of the frame's gem, seconds it lasts (0 = at once or lasting), what it does
CARDS = (
    ("garlic", "Garlic Bread", "Relic", (236, 196, 70), 20, "A ring of garlic surrounds you for 20 seconds. Anything that touches you is hurt and thrown back."),
    ("dawn", "Dawn Chorus", "Spell", (255, 160, 60), 0, "Sunlight floods the room. Every creature on screen takes heavy damage. You are a daywalker: it only tickles."),
    ("stapler", "Silver Stapler", "Relic", (200, 210, 230), 0, "Thirty silver staples. Each swing also fires one across the room."),
    ("coffee", "The Second Coffee", "Spell", (150, 100, 60), 15, "You move and swing much faster for 15 seconds. Do not have a third."),
    ("bat", "Bat Form", "Spell", (150, 110, 220), 8, "Turn into a bat for 8 seconds: fly anywhere, and nothing can hurt you."),
    ("rosary", "Grandmother's Rosary", "Relic", (120, 200, 230), 0, "Works by itself. The next time your health runs out, it is restored in full, once."),
    ("hallpass", "Hall Pass", "Ally", (120, 210, 130), 20, "A friendly ghost from the family floats beside you for 20 seconds, swatting whatever comes near."),
    ("fire", "Lanyard of Fire", "Relic", (240, 90, 60), 0, "Works by itself. Your weapon burns: longer reach and double damage until the stage ends."),
)
KEYS = tuple(c[0] for c in CARDS)
PASSIVE = ("rosary", "fire")


def info(key):
    return CARDS[KEYS.index(key)]


def _picture(key, s, r):
    """Paint the card's picture inside rectangle r."""
    x, y, w, h = r
    cx, cy = x + w // 2, y + h // 2
    if key == "garlic":
        pygame.draw.rect(s, (70, 40, 60), r)
        for i in range(12):
            a = i * math.pi / 6
            pygame.draw.circle(s, (250, 240, 200), (int(cx + math.cos(a) * 62), int(cy + math.sin(a) * 50)), 7)
        pygame.draw.ellipse(s, (200, 140, 70), (cx - 56, cy - 18, 112, 40))
        pygame.draw.ellipse(s, (236, 190, 110), (cx - 50, cy - 16, 100, 28))
        for k in range(-2, 3):
            pygame.draw.line(s, (250, 240, 170), (cx + k * 18 - 5, cy - 10), (cx + k * 18 + 5, cy + 4), 4)
            pygame.draw.circle(s, (90, 160, 80), (cx + k * 18, cy - 4), 2)
    elif key == "dawn":
        for i in range(h):
            k = i / float(h)
            pygame.draw.line(s, (255, int(120 + 110 * (1 - k)), int(60 + 120 * (1 - k))), (x, y + i), (x + w, y + i))
        pygame.draw.circle(s, (255, 250, 200), (cx, y + h - 26), 34)
        for i in range(13):
            a = math.pi + i * math.pi / 12
            pygame.draw.line(s, (255, 250, 200), (cx + math.cos(a) * 42, y + h - 26 + math.sin(a) * 42), (cx + math.cos(a) * 80, y + h - 26 + math.sin(a) * 80), 3)
        pygame.draw.rect(s, (60, 40, 50), (x, y + h - 22, w, 22))
        for bx in (cx - 60, cx - 20, cx + 30):
            pygame.draw.lines(s, (40, 30, 40), False, [(bx, y + 40), (bx + 8, y + 34), (bx + 16, y + 40), (bx + 24, y + 34), (bx + 32, y + 40)], 3)
    elif key == "stapler":
        pygame.draw.rect(s, (40, 50, 80), r)
        pygame.draw.polygon(s, (200, 210, 230), [(cx - 70, cy + 24), (cx + 60, cy + 24), (cx + 66, cy + 38), (cx - 70, cy + 38)])
        pygame.draw.polygon(s, (230, 236, 250), [(cx - 70, cy + 14), (cx + 50, cy - 28), (cx + 66, cy - 10), (cx - 60, cy + 22)])
        pygame.draw.polygon(s, (150, 160, 190), [(cx - 70, cy + 14), (cx - 60, cy + 22), (cx - 70, cy + 24)])
        for k in range(4):
            px = cx + 76 + k * 0 - k * 0
            pygame.draw.lines(s, (255, 255, 255), False, [(x + 20 + k * 30, y + 26), (x + 20 + k * 30, y + 18), (x + 36 + k * 30, y + 18), (x + 36 + k * 30, y + 26)], 3)
    elif key == "coffee":
        pygame.draw.rect(s, (90, 60, 50), r)
        pygame.draw.rect(s, (250, 250, 245), (cx - 34, cy - 20, 60, 60), border_radius=8)
        pygame.draw.ellipse(s, (70, 40, 26), (cx - 30, cy - 26, 52, 16))
        pygame.draw.arc(s, (250, 250, 245), (cx + 14, cy - 8, 34, 34), -1.4, 1.4, 7)
        for k in (-14, 0, 14):
            pygame.draw.lines(s, (240, 230, 220), False, [(cx - 4 + k, cy - 34), (cx + 2 + k, cy - 46), (cx - 4 + k, cy - 58), (cx + 2 + k, cy - 70)], 3)
        pygame.draw.polygon(s, (255, 220, 60), [(cx - 12, cy), (cx + 2, cy), (cx - 4, cy + 12), (cx + 8, cy + 12), (cx - 12, cy + 34), (cx - 6, cy + 16), (cx - 16, cy + 16)])
    elif key == "bat":
        pygame.draw.rect(s, (30, 26, 60), r)
        pygame.draw.circle(s, (240, 236, 200), (cx + 40, cy - 30), 30)
        pygame.draw.polygon(s, (20, 16, 30), [(cx, cy), (cx - 80, cy - 34), (cx - 54, cy + 4), (cx - 70, cy + 24), (cx - 30, cy + 16), (cx, cy + 34),
                                               (cx + 30, cy + 16), (cx + 70, cy + 24), (cx + 54, cy + 4), (cx + 80, cy - 34)])
        pygame.draw.polygon(s, (20, 16, 30), [(cx - 12, cy - 4), (cx - 14, cy - 26), (cx - 2, cy - 10), (cx + 2, cy - 10), (cx + 14, cy - 26), (cx + 12, cy - 4)])
        pygame.draw.circle(s, (255, 220, 90), (cx - 6, cy + 2), 3); pygame.draw.circle(s, (255, 220, 90), (cx + 6, cy + 2), 3)
    elif key == "rosary":
        pygame.draw.rect(s, (40, 70, 100), r)
        for i in range(22):
            a = i * 2 * math.pi / 22
            pygame.draw.circle(s, (150, 220, 240), (int(cx + math.cos(a) * 52), int(cy - 14 + math.sin(a) * 42)), 5)
        pygame.draw.line(s, (236, 196, 70), (cx, cy + 28), (cx, cy + 70), 7); pygame.draw.line(s, (236, 196, 70), (cx - 14, cy + 42), (cx + 14, cy + 42), 7)
        pygame.draw.circle(s, (255, 255, 255), (cx - 20, cy - 26), 3)
    elif key == "hallpass":
        pygame.draw.rect(s, (40, 90, 70), r)
        pygame.draw.rect(s, (250, 240, 200), (cx - 62, cy - 34, 124, 70), border_radius=6)
        pygame.draw.rect(s, (120, 210, 130), (cx - 62, cy - 34, 124, 18), border_top_left_radius=6, border_top_right_radius=6)
        s.blit(hud.font(26, True).render("HALL PASS", True, (30, 60, 40)), (cx - 52, cy - 34))
        for k in range(3):
            pygame.draw.line(s, (150, 140, 110), (cx - 50, cy - 4 + k * 12), (cx + 20, cy - 4 + k * 12), 2)
        pygame.draw.ellipse(s, (230, 240, 250), (cx + 28, cy - 8, 26, 30)); pygame.draw.circle(s, (30, 40, 70), (cx + 37, cy + 4), 3); pygame.draw.circle(s, (30, 40, 70), (cx + 46, cy + 4), 3)
    else:
        pygame.draw.rect(s, (60, 20, 20), r)
        pts = [(x + 14 + i * (w - 28) / 10.0, cy + math.sin(i * 1.1) * 26) for i in range(11)]
        pygame.draw.lines(s, (70, 130, 220), False, pts, 6)
        for i, p in enumerate(pts):
            f = 10 + (i % 3) * 6
            pygame.draw.polygon(s, (255, 150, 50), [(p[0] - 8, p[1]), (p[0], p[1] - f - 12), (p[0] + 8, p[1])])
            pygame.draw.polygon(s, (255, 230, 100), [(p[0] - 4, p[1]), (p[0], p[1] - f), (p[0] + 4, p[1])])
        pygame.draw.rect(s, (250, 250, 250), (x + w - 34, cy - 14, 22, 30)); pygame.draw.rect(s, (70, 130, 220), (x + w - 30, cy - 10, 14, 8))


def _frame(gem):
    s = pygame.Surface((CW, CH), pygame.SRCALPHA)
    pygame.draw.rect(s, (30, 20, 44), (0, 0, CW, CH), border_radius=14)
    pygame.draw.rect(s, (236, 196, 70), (4, 4, CW - 8, CH - 8), 3, border_radius=12)
    pygame.draw.rect(s, (60, 36, 84), (10, 10, CW - 20, CH - 20), border_radius=8)
    for px, py in ((16, 16), (CW - 16, 16), (16, CH - 16), (CW - 16, CH - 16)):          # a stud at each corner
        pygame.draw.circle(s, (236, 196, 70), (px, py), 7); pygame.draw.circle(s, gem, (px, py), 4)
    return s


def front(key):
    if ("f", key) in _cache:
        return _cache[("f", key)]
    _, name, kind, gem, _, _ = info(key)
    s = _frame(gem)
    pygame.draw.rect(s, (20, 14, 30), (22, 22, CW - 44, 34), border_radius=6)
    f = hud.font(28, True)
    img = f.render(name, True, (250, 240, 210))
    if img.get_width() > CW - 56:
        img = hud.font(22, True).render(name, True, (250, 240, 210))
    s.blit(img, (CW // 2 - img.get_width() // 2, 39 - img.get_height() // 2))
    box = pygame.Rect(22, 64, CW - 44, 200)
    _picture(key, s, box)
    pygame.draw.rect(s, (236, 196, 70), box, 2)
    pygame.draw.rect(s, (20, 14, 30), (22, 274, CW - 44, 28), border_radius=6)
    t = hud.font(24).render(kind, True, gem)
    s.blit(t, (CW // 2 - t.get_width() // 2, 280))
    hint = hud.font(20).render("Big button: turn it over", True, (200, 190, 220))
    s.blit(hint, (CW // 2 - hint.get_width() // 2, 312))
    _cache[("f", key)] = s
    return s


def back(key):
    if ("b", key) in _cache:
        return _cache[("b", key)]
    _, name, kind, gem, secs, what = info(key)
    s = _frame(gem)
    pygame.draw.rect(s, (240, 230, 200), (22, 22, CW - 44, CH - 44), border_radius=8)
    f = hud.font(26, True)
    s.blit(f.render(name, True, (50, 30, 60)), (34, 32))
    pygame.draw.line(s, (150, 120, 80), (34, 58), (CW - 34, 58), 2)
    s.blit(hud.font(22).render(kind + (", %d seconds" % secs if secs else ""), True, (110, 80, 60)), (34, 64))
    body = hud.font(24)
    for i, row in enumerate(hud.wrap(what, body, CW - 72)):
        s.blit(body.render(row, True, (40, 30, 40)), (34, 96 + i * 24))
    use = "It works by itself." if key in PASSIVE else "Use it: hold up and press the triangle."
    for i, row in enumerate(hud.wrap(use, hud.font(22), CW - 72)):
        s.blit(hud.font(22).render(row, True, (120, 50, 50)), (34, 270 + i * 22))
    _cache[("b", key)] = s
    return s


def card_back():
    """The pattern on a card not yet found."""
    if "back" in _cache:
        return _cache["back"]
    s = _frame((150, 110, 220))
    for i in range(6):
        pygame.draw.ellipse(s, (90, 56, 120), (CW // 2 - 20 - i * 14, CH // 2 - 30 - i * 20, 40 + i * 28, 60 + i * 40), 2)
    pygame.draw.polygon(s, (236, 196, 70), [(CW // 2, CH // 2 - 30), (CW // 2 + 18, CH // 2), (CW // 2, CH // 2 + 30), (CW // 2 - 18, CH // 2)])
    _cache["back"] = s
    return s


def show(screen, key, turn, centre=(400, 232)):
    """Draw a card turning over. turn: 0 = front, 1 = back, in between it swings round."""
    face = front(key) if turn < 0.5 else back(key)
    wide = max(2, int(CW * abs(math.cos(turn * math.pi))))
    img = pygame.transform.smoothscale(face, (wide, CH)) if wide != CW else face
    screen.blit(img, (centre[0] - wide // 2, centre[1] - CH // 2))
