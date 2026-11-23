"""The opening: Lucas drives to work. Four shots at full resolution, each a picture of time.
Big button: next shot. Triangle: skip."""
import math

import pygame

from ..alien_storm import hud
from . import art

SHOTS = (8.0, 8.0, 9.0, 6.0)
_cache = {}


def _big(img, times=2):
    for _ in range(times):
        img = pygame.transform.scale2x(img)
    return img


def grey_car():
    if "car" in _cache:
        return _cache["car"]
    s = pygame.Surface((300, 110), pygame.SRCALPHA)
    body, dark, glass = (150, 154, 162), (104, 108, 118), (170, 210, 230)
    pygame.draw.polygon(s, body, [(10, 70), (16, 46), (70, 40), (104, 14), (196, 14), (236, 42), (286, 50), (292, 72), (286, 84), (14, 84)])
    pygame.draw.polygon(s, glass, [(80, 40), (108, 20), (146, 20), (146, 40)])
    pygame.draw.polygon(s, glass, [(154, 20), (192, 20), (222, 40), (154, 40)])
    pygame.draw.line(s, dark, (150, 16), (150, 82), 3)
    pygame.draw.polygon(s, dark, [(10, 70), (292, 72), (286, 84), (14, 84)])
    pygame.draw.rect(s, (250, 240, 170), (280, 52, 12, 10)); pygame.draw.rect(s, (220, 60, 60), (8, 52, 8, 12))
    pygame.draw.circle(s, (198, 142, 100), (176, 30), 9)                       # Lucas at the wheel
    pygame.draw.polygon(s, (60, 36, 22), [(166, 30), (168, 20), (182, 20), (186, 26), (176, 24), (170, 40), (164, 40)])
    pygame.draw.rect(s, (20, 20, 26), (176, 27, 10, 4))
    for wx in (70, 232):
        pygame.draw.circle(s, (24, 24, 28), (wx, 84), 22); pygame.draw.circle(s, (170, 174, 184), (wx, 84), 10)
    _cache["car"] = s
    return s


def _sky(screen, top, bottom, upto=480):
    for y in range(0, upto, 4):
        k = y / float(upto)
        pygame.draw.rect(screen, tuple(int(a + (b - a) * k) for a, b in zip(top, bottom)), (0, y, 800, 4))


def _caption(screen, msg, t):
    if t < 0.4:
        return
    pygame.draw.rect(screen, (0, 0, 0), (0, 424, 800, 56))
    hud.label(screen, msg[:int((t - 0.4) * 40)], (400, 440), 30, (255, 255, 255), center=True, shadow=False)


def _bubble(screen, msg, x, y, t):
    if t < 0:
        return
    f = hud.font(28)
    msg = msg[:int(t * 30)]
    if not msg:
        return
    w = f.size(msg)[0] + 24
    box = pygame.Rect(x - w // 2, y, w, 40)
    pygame.draw.rect(screen, (255, 255, 255), box, border_radius=10)
    pygame.draw.rect(screen, (30, 26, 30), box, 2, border_radius=10)
    pygame.draw.polygon(screen, (255, 255, 255), [(x - 8, y + 38), (x + 8, y + 38), (x, y + 52)])
    screen.blit(f.render(msg, True, (30, 26, 30)), (box.x + 12, box.y + 9))


def _factory(screen, x, y):
    pygame.draw.rect(screen, (74, 78, 96), (x, y, 520, 220))
    for i in range(4):
        pygame.draw.polygon(screen, (60, 64, 80), [(x + i * 130, y), (x + i * 130 + 130, y), (x + i * 130 + 130, y - 50)])
    for cx in (x + 40, x + 100):
        pygame.draw.rect(screen, (54, 56, 70), (cx, y - 130, 30, 130))
    pygame.draw.rect(screen, (236, 232, 214), (x + 150, y + 22, 330, 44))
    f = hud.font(34, True)
    screen.blit(f.render("BRIGHTWELL REMEDIES", True, (40, 80, 120)), (x + 162, y + 32))
    for i in range(6):
        pygame.draw.rect(screen, (20, 22, 40), (x + 30 + i * 80, y + 90, 50, 44))
        if i in (1, 4):
            pygame.draw.circle(screen, (230, 40, 50), (x + 48 + i * 80, y + 110), 3); pygame.draw.circle(screen, (230, 40, 50), (x + 62 + i * 80, y + 110), 3)


def shot(screen, n, t):
    if n == 0:                                                   # the drive in at dawn
        _sky(screen, (60, 60, 120), (250, 170, 120), 330)
        pygame.draw.circle(screen, (255, 230, 170), (620, 300), 56)
        for i in range(-1, 6):
            hx = i * 220 - int(t * 30) % 220
            pygame.draw.polygon(screen, (70, 90, 90), [(hx, 330), (hx + 110, 250), (hx + 220, 330)])
        pygame.draw.rect(screen, (50, 52, 60), (0, 330, 800, 150))
        for i in range(-1, 8):
            pygame.draw.rect(screen, (240, 230, 160), (i * 130 - int(t * 260) % 130, 398, 60, 6))
        for i in range(-1, 5):
            px = i * 260 - int(t * 180) % 260
            pygame.draw.rect(screen, (60, 50, 40), (px, 250, 8, 84)); pygame.draw.circle(screen, (60, 110, 70), (px + 4, 240), 30)
        bob = int(math.sin(t * 9) * 2)
        screen.blit(grey_car(), (160 + int(min(t, 2.0) * 40), 296 + bob))
        _caption(screen, "6:52 a.m. Lucas drives to work. The coffee is still hot.", t)
    elif n == 1:                                                 # the car park
        _sky(screen, (70, 70, 130), (240, 180, 140), 330)
        _factory(screen, 250, 110)
        pygame.draw.rect(screen, (56, 58, 66), (0, 330, 800, 150))
        for i in range(5):
            cx = 330 + i * 92
            pygame.draw.rect(screen, (240, 240, 230), (cx - 4, 336, 3, 70))
            if i < 4:
                pygame.draw.rect(screen, ((120, 50, 50), (50, 80, 120), (60, 100, 70), (120, 110, 60))[i], (cx + 6, 346, 76, 30), border_radius=8)
                pygame.draw.rect(screen, (30, 30, 36), (cx + 18, 336, 50, 14), border_radius=5)
                for k in range(5):                               # cobwebs on every other car
                    pygame.draw.line(screen, (220, 220, 230), (cx + 6, 346), (cx + 16 + k * 14, 376))
                    pygame.draw.line(screen, (220, 220, 230), (cx + 82, 346), (cx + 70 - k * 12, 376))
        pygame.draw.rect(screen, (230, 200, 60), (210, 300, 10, 70))          # the barrier, with a bat on it
        pygame.draw.rect(screen, (230, 60, 60), (214, 304, 150, 8))
        bat = _big(art.monster("bat", int(t * 3) % 2), 1)
        screen.blit(bat, (280, 276))
        x = -300 + int(min(t, 4.0) * 110)
        screen.blit(grey_car(), (x, 362))
        _caption(screen, "The car park is full. Nobody has gone home. For some time.", t)
    elif n == 2:                                                 # the front door
        screen.fill((74, 78, 96))
        pygame.draw.rect(screen, (40, 42, 54), (0, 380, 800, 100))
        pygame.draw.rect(screen, (30, 30, 40), (380, 110, 190, 270))
        open_w = int(min(1.0, max(0.0, (t - 2.0) / 0.8)) * 170)
        pygame.draw.rect(screen, (150, 110, 70), (390 + open_w, 120, 170 - open_w, 260))
        pygame.draw.rect(screen, (236, 232, 214), (392, 60, 166, 34)); screen.blit(hud.font(26, True).render("STAFF ENTRANCE", True, (40, 80, 120)), (400, 68))
        if open_w > 60:
            z = _big(art.monster("zombie", int(t * 2) % 2))
            screen.blit(z, (410, 380 - z.get_height()))
        lx = int(min(t, 1.6) / 1.6 * 200)
        pose = "walk" if t < 1.6 else "stand"
        me = _big(art.hunter("lucas", pose, int(t * 8) % 4))
        screen.blit(me, (lx + 20, 380 - me.get_height() + 4))
        _bubble(screen, "Braaains... I mean, badge?", 470, 150, t - 3.2)
        _bubble(screen, "Vampires. Oh well...", 330, 200, t - 5.6)
    else:                                                        # the sunglasses come down
        screen.fill((20, 10, 24))
        for i in range(24):
            a = i * math.pi / 12 + t * 0.2
            pygame.draw.line(screen, (60, 20, 40), (400, 240), (400 + math.cos(a) * 600, 240 + math.sin(a) * 600), 6)
        me = _big(art.hunter("lucas", "stand"), 3)
        screen.blit(me, (400 - 160, 250 - me.get_height() // 2))
        if t > 0.8:
            hud.label(screen, "VAMPIRES, OH WELL...", (400, 40), 64, (230, 60, 80), center=True, bold=True)
        _bubble(screen, "Monday.", 430, 110, t - 2.0)


class Opening:
    def __init__(self):
        self.n, self.t = 0, 0.0

    def update(self, dt, inp):
        """True when the opening is over."""
        self.t += dt
        if "b" in inp.pressed or "start" in inp.pressed:
            return True
        if self.t >= SHOTS[self.n] or ("a" in inp.pressed and self.t > 0.3):
            self.n, self.t = self.n + 1, 0.0
        return self.n >= len(SHOTS)

    def draw(self, screen):
        shot(screen, min(self.n, len(SHOTS) - 1), self.t)
        hud.label(screen, "Big button: next    Triangle: skip", (790 - 300, 4), 20, (200, 200, 210), shadow=True)
