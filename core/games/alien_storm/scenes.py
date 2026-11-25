"""Cutscenes for Alien Storm: Tom Cat Alley, drawn at the full 800 x 480.

Every scene is a list of shots. Each shot is a pure function of time, so scenes can be skipped or
tested at any moment. Big button: next shot. Triangle: skip the scene."""
import math
import random

import pygame

from . import art, world, fleet, hud, lines

SW, SH = 800, 480
BAR = 34                         # cinema bars, top and bottom
_c = {}


class Scene:
    def __init__(self, game, shots, after=None, music=None):
        self.game, self.shots, self.after, self.music = game, shots, after, music
        self.i, self.t, self.started = 0, 0.0, False

    def update(self, dt, inp):
        g = self.game
        if not self.started:
            self.started = True
            if self.music:
                g.sound.music(self.music)
        shot = self.shots[self.i]
        for at, name in shot.get("sfx", ()):
            if self.t <= at < self.t + dt:
                g.sfx(name)
        self.t += dt
        if "b" in inp.pressed or "start" in inp.pressed:
            return True
        if self.t >= shot["dur"] or ("a" in inp.pressed and self.t > 0.4):
            self.i, self.t = self.i + 1, 0.0
            if self.i >= len(self.shots):
                self.i = len(self.shots) - 1
                return True
        return False

    def draw(self, screen):
        shot = self.shots[self.i]
        t = self.t
        shot["draw"](screen, t)
        pygame.draw.rect(screen, (0, 0, 0), (0, 0, SW, BAR))
        pygame.draw.rect(screen, (0, 0, 0), (0, SH - BAR, SW, BAR))
        fade = min(1.0, t / 0.35, (shot["dur"] - t) / 0.35)
        if fade < 1:
            veil = _veil()
            veil.set_alpha(int(255 * (1 - max(0.0, fade))))
            screen.blit(veil, (0, 0))
        cap = shot.get("caption")
        if cap:
            for k, row in enumerate(cap if isinstance(cap, (list, tuple)) else [cap]):
                n = int(max(0, t - 0.5 - k * 1.2) * 30)
                if n > 0:
                    hud.label(screen, row[:n], (40, BAR + 14 + k * 30), 30, (255, 255, 255), bold=True)
        cur = None
        for item in shot.get("say", ()):
            if item[0] <= t:
                cur = item
        if cur:
            t0, who, mood, line = cur
            right = who in ("kj", "heather")
            hud.bubble(screen, who, mood, line, 14, SH - 80, right=right, size=76, width=688,
                       shown=int((t - t0) * 42))
        hud.label(screen, "Triangle: skip", (SW - 120, 9), 18, (150, 150, 160), shadow=False)


def _veil():
    if "veil" not in _c:
        _c["veil"] = pygame.Surface((SW, SH))
    return _c["veil"]


# ------------------------------------------------------------------ small drawing helpers
def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def zoom(im, k, ang=0.0):
    return pygame.transform.rotozoom(im, ang, k)


def put(screen, im, x, y):
    screen.blit(im, (int(x - im.get_width() / 2), int(y - im.get_height() / 2)))


def sea_hd(stage):
    key = ("sea_hd", stage)
    if key not in _c:
        _c[key] = pygame.transform.scale(world.sea(stage), (800, 960))
    return _c[key]


def top_sea(screen, stage, scroll):
    im = sea_hd(stage)
    off = int(scroll) % 960
    screen.blit(im, (0, off - 960))
    screen.blit(im, (0, off))


def blast(screen, x, y, t, t0, size=40, life=0.7):
    u = (t - t0) / life
    if 0 <= u < 1:
        key = ("blast", size)
        if key not in _c:
            _c[key] = [pygame.transform.scale(f, (size * 2, size * 2)) for f in world.boom(20)]
        screen.blit(_c[key][min(9, int(u * 10))], (int(x - size), int(y - size)))


def bez(p0, p1, lift, u):
    mx, my = (p0[0] + p1[0]) / 2, min(p0[1], p1[1]) - lift
    a = 1 - u
    return (a * a * p0[0] + 2 * a * u * mx + u * u * p1[0], a * a * p0[1] + 2 * a * u * my + u * u * p1[1])


def rocket(screen, t, t0, dur, p0, p1, lift=60, smoke=(210, 214, 220), boom=30):
    """A missile that climbs out of p0 on a pillar of smoke, arcs over and bursts at p1."""
    u = (t - t0) / dur
    if u < 0:
        return
    linger = max(0.0, u - 1.0) * dur
    if linger < 1.6:
        n = 22
        for k in range(n):
            uk = min(1.0, u) * k / (n - 1)
            x, y = bez(p0, p1, lift, uk)
            age = (min(1.0, u) - uk) * dur + linger
            r = 3 + age * 5
            g = max(0.0, 1 - age / 2.2)
            if g > 0.05:
                col = tuple(int(c * (0.55 + 0.45 * g)) for c in smoke)
                pygame.draw.circle(screen, col, (int(x + math.sin(k * 1.7) * age * 4), int(y)), int(r * (0.6 + 0.4 * g)))
    if u < 1:
        x, y = bez(p0, p1, lift, u)
        x2, y2 = bez(p0, p1, lift, max(0, u - 0.03))
        pygame.draw.line(screen, (255, 200, 90), (int(x2), int(y2)), (int(x), int(y)), 5)
        pygame.draw.line(screen, (255, 255, 240), (int(x), int(y)), (int(2 * x - x2), int(2 * y - y2)), 3)
        if u < 0.12:
            pygame.draw.circle(screen, (255, 230, 150), (int(p0[0]), int(p0[1])), int(14 * (1 - u / 0.12)) + 3)
    elif boom:
        blast(screen, p1[0], p1[1], t, t0 + dur, boom)


def tracers(screen, t, origin, target, col=(255, 230, 120), n=7, speed=3.0, jitter=10):
    for k in range(n):
        u = (t * speed + k / n) % 1.0
        x = origin[0] + (target[0] - origin[0]) * u + math.sin(k * 9.1 + int(t * speed + k / n) * 3.3) * jitter * u
        y = origin[1] + (target[1] - origin[1]) * u
        dx, dy = (target[0] - origin[0]) * 0.03, (target[1] - origin[1]) * 0.03
        pygame.draw.line(screen, col, (int(x), int(y)), (int(x + dx), int(y + dy)), 2)


def splash(screen, x, y, t, t0, size=40):
    u = (t - t0) / 1.4
    if 0 <= u < 1:
        h = size * math.sin(u * math.pi) * 1.6
        w = size * (0.3 + 0.5 * u)
        pygame.draw.ellipse(screen, (236, 246, 250), (int(x - w / 2), int(y - h), int(w), int(h + 6)))
        pygame.draw.ellipse(screen, (255, 255, 255), (int(x - w), int(y - 4), int(w * 2), 10))


def rain(screen, t, n=70, col=(150, 170, 190)):
    for i in range(n):
        x = (i * 131 + int(t * 500)) % (SW + 60) - 30
        y = (i * 197 + int(t * 1100)) % SH
        pygame.draw.line(screen, col, (x, y), (x - 6, y + 20), 1)


def lightning(screen, x, seed):
    rng = random.Random(seed)
    pts, y = [(x, 0)], 0
    while y < 300:
        y += rng.randrange(20, 46)
        pts.append((x + rng.randrange(-34, 35), y))
    pygame.draw.lines(screen, (170, 200, 255), False, pts, 6)
    pygame.draw.lines(screen, (255, 255, 255), False, pts, 2)


def falling(screen, im, t, t0, p0, vx, sea_y, spin=200.0):
    """A wreck tumbling out of the sky, trailing smoke, ending in a splash."""
    dt = t - t0
    if dt < 0:
        return False
    x, y = p0[0] + vx * dt, p0[1] + 60 * dt + 140 * dt * dt
    if y < sea_y:
        for k in range(8):
            a = dt - k * 0.07
            if a > 0:
                sx, sy = p0[0] + vx * a, p0[1] + 60 * a + 140 * a * a
                g = 60 + k * 14
                pygame.draw.circle(screen, (g, g, g), (int(sx), int(sy) - k * 3), 4 + k)
        put(screen, zoom(im, 1.6, dt * spin), x, y)
        pygame.draw.circle(screen, (255, 170, 60), (int(x), int(y)), 6)
    else:
        ts = t0 + (-60 + math.sqrt(3600 + 560 * (sea_y - p0[1]))) / 280
        splash(screen, p0[0] + vx * (ts - t0), sea_y, t, ts, 36)
    return True


def swarm(screen, t, kind="fighter", n=12, seed=1, speed=90.0, y0=60, y1=200, scale=1.3, left=True):
    """A loose cloud of alien craft crossing the sky."""
    rng = random.Random(seed)
    im = _c.setdefault(("swarm", kind, scale, left), zoom(art.alien(kind), scale, 90 if left else -90))
    for i in range(n):
        ph, y, sp = rng.uniform(0, 1000), rng.uniform(y0, y1), speed * rng.uniform(0.7, 1.3)
        x = (ph + t * sp) % (SW + 200) - 100
        x = SW - x if left else x
        put(screen, im, x, y + math.sin(t * 2 + i) * 6)


def muzzle(screen, x, y, ang, size, u):
    """A big gun going off: flame along the barrel line, then rolling smoke."""
    if u < 0 or u > 1:
        return
    ca, sa = math.cos(ang), -math.sin(ang)
    if u < 0.25:
        k = 1 - u / 0.25
        L, w = size * (1.2 + 0.6 * k), size * 0.34 * k + 4
        pts = [(x, y), (x + ca * L * 0.4 - sa * w, y + sa * L * 0.4 + ca * w), (x + ca * L, y + sa * L),
               (x + ca * L * 0.4 + sa * w, y + sa * L * 0.4 - ca * w)]
        pygame.draw.polygon(screen, (255, 170, 50), pts)
        pygame.draw.polygon(screen, (255, 244, 190), [(x, y), (x + ca * L * 0.5 - sa * w * 0.4, y + sa * L * 0.5 + ca * w * 0.4),
                                                    (x + ca * L * 0.75, y + sa * L * 0.75), (x + ca * L * 0.5 + sa * w * 0.4, y + sa * L * 0.5 - ca * w * 0.4)])
    for k in range(5):
        d = size * (0.5 + 0.5 * k) * (0.4 + u)
        g = int(110 + 90 * u)
        pygame.draw.circle(screen, (g, g - 6, g - 14), (int(x + ca * d + math.sin(k * 2.2) * 8 * u), int(y + sa * d - u * 22 - k * 2)),
                           int(size * 0.2 * (1 + u * 1.6)))


def shake_of(t, t0, amt=8, life=0.6):
    u = t - t0
    if 0 <= u < life:
        k = amt * (1 - u / life)
        return int(math.sin(u * 90) * k), int(math.cos(u * 70) * k)
    return 0, 0


# ------------------------------------------------------------------ the two crews: the flex, every time
def cockpit(screen, t, top=(60, 130, 220), bottom=(190, 220, 250)):
    screen.blit(fleet.sky(top, bottom), (0, 0))
    for i in range(5):
        im = world.cloud(0, i % 3)
        x = (i * 260 - t * (240 + i * 40)) % (SW + 300) - 200
        screen.blit(im, (int(x), 60 + i * 70))
    for i in range(24):
        x = (i * 173 - t * 1400) % (SW + 200) - 100
        y = BAR + 10 + (i * 37) % (SH - 2 * BAR - 20)
        pygame.draw.line(screen, (255, 255, 255), (int(x), y), (int(x) + 60, y), 1)


def flex_shot(extra=(), dur=None):
    """Alex grins, flexes and says the line; KJ answers. Used, word for word, in every cutscene."""
    def draw(screen, t):
        cockpit(screen, t)
        pop = 1 + 0.06 * math.sin(t * 9) * (1 if t < 2.6 else 0)
        put(screen, zoom(art.portrait("alex", "flex" if t < 2.9 else "grin", 300), pop), 215, 210)
        put(screen, art.portrait("kj", "calm" if t < 2.9 else "grin", 300), 585, 210)
    say = [(0.3, "alex", "flex", lines.FLEX_ALEX), (2.9, "kj", "calm", lines.FLEX_KJ)]
    tt = 5.6
    for who, mood, line in extra:
        say.append((tt, who, mood, line))
        tt += 2.8
    return dict(dur=dur or tt + 0.4, draw=draw, say=say)


def alex_card(stage=0):
    """Alex's own moment before each launch: a pilot card with his portrait large."""
    notes = (("Pilot, F-14 Tomcat", "Landings: all of them", "Improv shows missed: 0"),
             ("Flight hours: plenty", "Hair: always good", "Aliens impressed: every one"),
             ("Favorite move: the loop", "Favorite audience: any", "Curtain time: soon"),
             ("Missions left: one", "Jokes left: many", "Still makes it look good"))[stage % 4]

    def draw(screen, t):
        screen.blit(fleet.sky((14, 26, 70), (40, 80, 150)), (0, 0))
        for i in range(-2, 12):                                   # searchlight stripes sliding past
            x = i * 110 + (t * 60) % 110
            pygame.draw.polygon(screen, (30, 56, 120), [(x, BAR), (x + 50, BAR), (x - 90, SH - BAR), (x - 140, SH - BAR)])
        slide = ease(t / 0.7)
        mood = "flex" if 2.2 < t < 4.6 else "grin"
        put(screen, zoom(art.portrait("alex", mood, 300), 1.15 + 0.03 * math.sin(t * 6)), int(-160 + 370 * slide), 235)
        x0 = int(820 - 400 * slide)
        pygame.draw.rect(screen, (250, 214, 90), (x0, 96, 360, 8))
        hud.label(screen, "LIEUTENANT", (x0, 110), 30, (190, 210, 255), bold=True)
        hud.label(screen, "ALEX", (x0, 136), 96, (255, 255, 255), bold=True)
        hud.label(screen, "call sign  TWIN", (x0, 214), 30, (250, 214, 90), bold=True)
        for i, row in enumerate(notes):
            if t > 1.2 + i * 0.6:
                hud.label(screen, row, (x0, 262 + i * 34), 28, (255, 255, 255))
        if 2.2 < t < 4.6:                                         # a camera flash or two
            for k in range(3):
                if int(t * 7 + k * 3) % 5 == 0:
                    fx, fy = 80 + k * 110, 120 + (k * 67) % 90
                    pygame.draw.line(screen, (255, 255, 255), (fx - 14, fy), (fx + 14, fy), 3)
                    pygame.draw.line(screen, (255, 255, 255), (fx, fy - 14), (fx, fy + 14), 3)
    return dict(dur=7.5, draw=draw, say=[(2.4, "alex", "flex", lines.CARD_ALEX), (5.6, "kj", "calm", "We have a launch window, twin.")])


def improv_show():
    """After the war: Alex makes his curtain. A stage, a spotlight, a microphone, and KJ in the front row."""
    def draw(screen, t):
        screen.fill((24, 10, 16))
        for i in range(9):                                        # the red curtain, in folds
            x = i * 100 - 50
            pygame.draw.rect(screen, (120, 20, 34) if i % 2 else (150, 28, 44), (x, BAR, 100, 250))
            pygame.draw.rect(screen, (90, 14, 26), (x + 92, BAR, 8, 250))
        pygame.draw.rect(screen, (230, 190, 80), (0, BAR, SW, 14))
        beam = pygame.Surface((SW, SH), pygame.SRCALPHA)
        sway = math.sin(t * 0.8) * 14
        pygame.draw.polygon(beam, (255, 244, 200, 70), [(400 + sway * 3, BAR), (270 + sway, 330), (530 + sway, 330)])
        screen.blit(beam, (0, 0))
        pygame.draw.rect(screen, (86, 60, 40), (0, 318, SW, 60))                    # the boards
        pygame.draw.rect(screen, (60, 40, 26), (0, 372, SW, 8))
        cur = [s for s in say if s[0] <= t]
        mood = cur[-1][2] if cur and cur[-1][1] == "alex" else "grin"
        bounce = abs(math.sin(t * 3)) * 6 if mood == "flex" else 0
        put(screen, art.portrait("alex", mood, 300), 400, 215 - int(bounce))
        pygame.draw.line(screen, (40, 40, 46), (300, 330), (300, 240), 5)            # the microphone stand
        pygame.draw.line(screen, (40, 40, 46), (300, 240), (330, 226), 5)
        pygame.draw.circle(screen, (200, 200, 210), (334, 224), 9)
        pygame.draw.rect(screen, (40, 40, 46), (286, 328, 28, 6))
        for i in range(13):                                       # the audience, in silhouette
            x = 30 + i * 62
            bob_y = int(abs(math.sin(t * 4 + i * 1.7)) * 5) if 4.6 < t < 6.6 or t > 10.2 else 0
            pygame.draw.circle(screen, (10, 6, 10), (x, 392 - bob_y), 22)
            pygame.draw.rect(screen, (10, 6, 10), (x - 30, 408 - bob_y, 60, 60), border_radius=14)
        if 4.6 < t < 6.6 or t > 10.2:                             # they laugh
            for i in range(5):
                u = (t * 0.9 + i * 0.37) % 1
                hud.label(screen, "HA", (90 + i * 150, int(300 - u * 90)), 30 + (i % 2) * 10, (255, 230, 150), bold=True)
        put(screen, art.portrait("kj", "grin" if t > 10.2 else "calm", 110), 730, 300)
    say = [(0.5, "alex", "grin", lines.STAGE_ALEX[0]), (4.4, "alex", "flex", lines.STAGE_ALEX[1]),
           (7.4, "kj", "calm", lines.FLEX_KJ), (10.2, "alex", "grin", lines.STAGE_ALEX[2])]
    return dict(dur=14.0, draw=draw, say=say, caption=("That night. He made the curtain.",))


def duo_shot(who_a, who_b, say, dur, top=(60, 130, 220), bottom=(190, 220, 250)):
    def draw(screen, t):
        cockpit(screen, t, top, bottom)
        cur = [s for s in say if s[0] <= t]
        speaker, mood = (cur[-1][1], cur[-1][2]) if cur else (None, "calm")
        for who, x in ((who_a, 230), (who_b, 570)):
            m = mood if who == speaker else "calm"
            if who == "poppa":
                m = "angry"
            put(screen, art.portrait(who, m if m != "flex" or who == "alex" else "grin", 300), x - 15 if x < 400 else x + 15, 210)
    return dict(dur=dur, draw=draw, say=say)


# ------------------------------------------------------------------ takeoff
def deck_view(screen, t, jet_y, pan=0.0, sweep=0.0, burner=0.3, steam=True, shake=(0, 0)):
    key = "deck_big"
    if key not in _c:
        _c[key] = art.carrier(1300)
    car = _c[key]
    top_sea(screen, 0, t * 40 + pan)
    ox, oy = 175 + shake[0], -40 + int(pan) + shake[1]
    for k in range(6):                                           # the wake of the bow
        pygame.draw.line(screen, (200, 226, 240), (ox + 200 - k * 40, oy + 30 + k * 60), (ox + 160 - k * 44, oy + 90 + k * 60), 3)
        pygame.draw.line(screen, (200, 226, 240), (ox + 250 + k * 40, oy + 30 + k * 60), (ox + 290 + k * 44, oy + 90 + k * 60), 3)
    screen.blit(car, (ox, oy))
    cx = ox + 182
    if steam:
        for k in range(9):
            y = oy + 60 + k * 44
            r = 7 + int(5 * math.sin(t * 5 + k))
            puff = _c.setdefault(("puff", r), _puff(r))
            screen.blit(puff, (cx - r + int(math.sin(t * 3 + k * 2) * 6), y - r))
    jet = zoom(art.tomcat(round(sweep * 2) / 2, 1, 4, round(burner * 2.5) / 2.5), 2.0)
    put(screen, jet, cx, jet_y + oy + 40)
    return cx, oy


def _puff(r):
    s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    pygame.draw.circle(s, (255, 255, 255, 120), (r, r), r)
    return s


def takeoff(game, first=False):
    shots = []
    if first:
        def far(screen, t):                                      # the whole strike group, from high above
            z = 1.0 + 1.5 * ease(t / 9.0)
            top_sea(screen, 0, t * 14)
            cx, cy = 400, 250
            ships = (("carrier", 0, 0), ("destroyer", -150, -70), ("destroyer", 150, -110), ("destroyer", 175, 95),
                     ("battleship", -140, 105))
            for kind, dx, dy in ships:
                im = world.carrier_small() if kind == "carrier" else world.ship(kind)
                x, y = cx + dx * z, cy + dy * z
                for k in range(1, 6):                            # wake
                    w = (im.get_width() * 0.5 + k * 5) * z
                    yy = y + (im.get_height() * 0.5 + k * 9) * z
                    pygame.draw.line(screen, (190, 220, 236), (int(x - w), int(yy)), (int(x - w * 0.6), int(yy - 7 * z)), 2)
                    pygame.draw.line(screen, (190, 220, 236), (int(x + w), int(yy)), (int(x + w * 0.6), int(yy - 7 * z)), 2)
                put(screen, zoom(im, z), x, y)
            u = ease((t - 2.0) / 4.0)                            # the submarine slips under
            sx, sy = cx - 60 * z, cy - 165 * z
            if u < 1:
                im = zoom(world.ship("sub"), z * (1 - 0.15 * u))
                im.set_alpha(int(255 * (1 - u)))
                put(screen, im, sx, sy)
            if 0 < u:
                r = int((10 + 26 * u) * z)
                pygame.draw.ellipse(screen, (200, 230, 240), (int(sx - r / 2), int(sy - r), r, r * 2), 2)
            for i in range(3):
                im = world.cloud(0, i)
                screen.blit(im, (int((i * 330 + t * 26) % 1000 - 160), 70 + i * 130))
        shots.append(dict(dur=9.5, draw=far, caption=("THE PACIFIC OCEAN.  TODAY.", "A carrier strike group, a long way from home.")))

        def scope(screen, t):                                    # the radar picture
            screen.fill((4, 16, 10))
            cx, cy, R = 400, 240, 190
            for r in (R, R * 2 // 3, R // 3):
                pygame.draw.circle(screen, (20, 110, 50), (cx, cy), r, 2)
            pygame.draw.line(screen, (20, 110, 50), (cx - R, cy), (cx + R, cy), 1)
            pygame.draw.line(screen, (20, 110, 50), (cx, cy - R), (cx, cy + R), 1)
            a = t * 2.4
            for k in range(14):
                g = 200 - k * 13
                pygame.draw.line(screen, (10, g, 40), (cx, cy), (cx + math.cos(a - k * 0.03) * R, cy + math.sin(a - k * 0.03) * R), 3)
            for dx, dy in ((0, 0), (-18, -10), (20, -14), (22, 12), (-17, 14)):
                pygame.draw.rect(screen, (90, 255, 130), (cx + dx - 3, cy + dy - 3, 6, 6))
            rng = random.Random(8)
            n = int(max(0, t - 1.0) * 26)
            for i in range(min(n, 150)):
                bx = cx + rng.uniform(-170, 170)
                by = cy - 185 + rng.uniform(0, 60) + max(0, t - 1.0 - i / 26) * 16
                if (bx - cx) ** 2 + (by - cy) ** 2 < R * R and by < cy - 30:
                    pygame.draw.polygon(screen, (255, 60, 60), [(bx, by - 4), (bx + 4, by + 3), (bx - 4, by + 3)])
            hud.label(screen, "CONTACTS  %03d" % min(n * 3, 412), (590, 80), 28, (90, 255, 130), bold=True)
            if t > 1.6 and int(t * 3) % 2 == 0:
                hud.label(screen, "UNKNOWN.  NOT ANSWERING.", (400, 60), 30, (255, 80, 80), center=True, bold=True)
        shots.append(dict(dur=7.5, draw=scope, sfx=((1.6, "as_warning"), (2.6, "as_warning"), (3.6, "as_warning")),
                          say=[(3.2, "poppa", "angry", "That is not weather and that is not ours. Launch the Tomcats!")]))

        def deck(screen, t):
            deck_view(screen, t, 330, burner=0.2 + 0.25 * min(1, t / 6), sweep=0.0)
        shots.append(dict(dur=10.5, draw=deck, say=[
            (0.5, "poppa", "angry", "You scratch my airplane, you answer to me. Now get off my deck!"),
            (3.6, "alex", "grin", lines.IMPROV_ALEX),
            (7.0, "kj", "calm", "Then fly fast, twin. You are already late.")]))

    def launch(screen, t):                                       # the catapult shot
        u = max(0.0, t - 1.0)
        dist = 620 * u * u
        pan = max(0.0, dist - 180)
        sh = shake_of(t, 1.0, 7, 1.2)
        cx, oy = deck_view(screen, t, 330 - dist, pan=pan, sweep=ease((t - 2.4) / 1.4), burner=1.0 if t > 0.5 else 0.5,
                           steam=True, shake=sh)
        if 0.6 < t < 1.0:
            hud.label(screen, "LAUNCH!", (400, 110), 60, (255, 230, 90), center=True, bold=True)
        if pan > 500:
            for i in range(3):
                im = world.cloud(0, i)
                screen.blit(im, (int(i * 300 + 40), int((pan * 1.4 + i * 200) % 700 - 120)))
    shots.append(dict(dur=4.6, draw=launch, sfx=((0.2, "as_burner"), (1.0, "as_catapult")),
                      say=[] if first else [(0.2, "poppa", "angry", "Again! And this time bring it back clean!")]))
    banter = []
    if not first:
        banter = [[("heather", "grin", "Dash Two is up. Right behind you."), ("stephen", "grin", "Try to keep up, kids.")],
                  [("kj", "calm", "Fuel is good. Missiles are good. Hair is good."), ("alex", "grin", "Hair is always good.")],
                  [("heather", "calm", lines.SCREEN_TIME_HEATHER), ("stephen", "grin", lines.SCREEN_TIME_STEPHEN)],
                  [("alex", "calm", "One more and I can still make curtain."), ("kj", "grin", "They can hold the improv show. This is the show.")],
                  ][game.stage % 4]
    shots.append(alex_card(game.stage))
    shots.append(flex_shot(banter))
    if first:
        def title(screen, t):
            cockpit(screen, t, (30, 60, 130), (240, 150, 90))
            for i, sq in enumerate((1, 2)):
                jet = zoom(art.tomcat(1.0, sq, 4, 1.0), 2.2)
                put(screen, jet, 250 + i * 300, 330 - min(1, t / 1.5) * 60 + math.sin(t * 2 + i) * 6)
            k = ease(t / 1.2)
            hud.label(screen, "ALIEN STORM", (400, 70), int(40 + 60 * k), (255, 80, 70), center=True, bold=True)
            if t > 1.3:
                hud.label(screen, "TOM CAT ALLEY", (400, 150), 52, (255, 255, 255), center=True, bold=True)
        shots.append(dict(dur=4.5, draw=title))
    return Scene(game, shots, after=None, music="as_anthem")


# ------------------------------------------------------------------ side on battle staging
def backdrop(screen, t, pal, horizon=300, sun=None, clouds=0, stage=0):
    screen.blit(fleet.sky(pal[0], pal[1]), (0, 0))
    if sun:
        pygame.draw.circle(screen, sun[2], (sun[0], sun[1]), 46)
        pygame.draw.circle(screen, (255, 250, 220), (sun[0], sun[1]), 34)
    for i in range(clouds):
        im = world.cloud(stage, i % 3)
        screen.blit(im, (int((i * 290 + t * (10 + i * 4)) % 1100 - 180), 50 + (i * 53) % 120))
    fleet.waves(screen, horizon, t, pal[2], pal[3])


def bob(t, k=0.0, amp=3.0):
    return math.sin(t * 1.3 + k) * amp


DAY = ((70, 140, 225), (200, 225, 245), (26, 82, 128), (120, 170, 210))
STORM = ((26, 32, 44), (70, 80, 96), (30, 42, 56), (110, 124, 140))
TROPIC = ((60, 160, 235), (210, 240, 245), (20, 120, 144), (150, 225, 225))
DAWN = ((40, 40, 90), (250, 160, 110), (40, 60, 110), (240, 170, 140))
DUSK = ((60, 40, 100), (255, 150, 80), (50, 50, 100), (255, 180, 120))


def set_piece(game, stage):
    shots = [piece_destroyers, piece_battleship, piece_submarine, piece_everything][stage]()

    def after():
        game.landing = Landing(game)
    return Scene(game, shots, after=after, music="as_fleet")


def piece_destroyers():
    def wide(screen, t):
        backdrop(screen, t, DAY, sun=(650, 110, (255, 230, 150)), clouds=3)
        swarm(screen, t, "fighter", 16, 2, 120, 60, 210, 1.2)
        screen.blit(fleet.carrier(), (60 - int(t * 4), 300 - 132 + int(bob(t))))
        screen.blit(fleet.destroyer(), (470 - int(t * 9), 372 - 78 + int(bob(t, 1))))
        screen.blit(zoom(fleet.destroyer(), 0.6), (620 - int(t * 5), 318 - 47 + int(bob(t, 2, 2))))
    s1 = dict(dur=8.0, draw=wide, caption=("The first wave reaches the fleet.",),
              say=[(3.4, "poppa", "angry", "All ships: weapons free! Nothing touches my carrier!")])

    def close(screen, t):
        sx, sy = shake_of(t, 1.0, 4, 0.4)
        backdrop(screen, t, DAY, horizon=330, clouds=2)
        swarm(screen, t, "fighter", 10, 4, 150, 50, 150, 1.5)
        dy = int(bob(t, 0, 4))
        big = _c.setdefault("dd_big", zoom(fleet.destroyer(), 2.0))
        x0, y0 = 60 + sx, 400 - 156 + dy + sy
        targets = ((640, 90), (520, 60), (700, 140), (590, 120), (460, 100), (720, 70), (560, 150), (660, 110))
        for i, (tx, ty) in enumerate(targets):                   # the vertical launchers
            cell = (x0 + (410 if i % 2 == 0 else 86), y0 + 100)
            rocket(screen, t, 1.0 + i * 0.9, 1.5, cell, (tx, ty), lift=150, boom=40)
            falling(screen, art.alien("fighter"), t, 2.5 + i * 0.9, (tx, ty), -40 + i * 12, 330)
        screen.blit(big, (x0, y0))
        tracers(screen, t, (x0 + 250, y0 + 50), (700, 60), n=9, speed=2.6, jitter=30)      # the close in gun
        if int(t * 20) % 2 == 0:
            pygame.draw.circle(screen, (255, 240, 170), (x0 + 252, y0 + 48), 7)
    s2 = dict(dur=10.5, draw=close, sfx=tuple((1.0 + i * 0.9, "as_radar") for i in range(8)) + tuple((2.5 + i * 0.9, "as_boom") for i in range(8)),
              say=[(4.0, "heather", "grin", lines.REEL_HEATHER), (7.0, "stephen", "calm", "Film it later, honey. Fly now.")])

    def high(screen, t):
        screen.blit(fleet.sky((40, 100, 200), (150, 200, 240)), (0, 0))
        for i in range(4):
            screen.blit(world.cloud(0, i % 3), (int((i * 250 + t * 30) % 1000 - 150), 320 + (i * 37) % 90))
        bomber = _c.setdefault("bomber_big", zoom(art.alien("bomber"), 2.4, 90))
        hits = ((1.6, 0), (3.4, 1), (5.2, 2))
        for i in range(3):
            x, y = 900 - t * 80 - i * 190, 110 + i * 70
            th = hits[i][0]
            for k in range(3):
                rocket(screen, t, th - 1.4 + k * 0.12, 1.4, (120 + k * 60 + i * 40, 470), (900 - (th + k * 0.12) * 80 - i * 190, y), lift=40, boom=56)
            if t < th + 0.1:
                put(screen, bomber, x, y)
            else:
                falling(screen, art.alien("bomber"), t, th, (900 - th * 80 - i * 190, y), -70, 520, spin=90)
    s3 = dict(dur=9.0, draw=high, sfx=((1.6, "as_boom_big"), (3.4, "as_boom_big"), (5.2, "as_boom_big")),
              say=[(4.4, "kj", "grin", "The fleet is hitting everything. " + lines.KILL_KJ[0])])

    def turn(screen, t):
        backdrop(screen, t, DAY, sun=(650, 110, (255, 230, 150)), clouds=3)
        for i, x in enumerate((140, 330, 520, 700)):             # smoke where the wave went down
            for k in range(6):
                pygame.draw.circle(screen, (70 + k * 16,) * 3, (x + int(math.sin(t + k) * 5) + k * 5, 296 - k * 16), 6 + k * 2)
        x = 420 - int(ease(t / 8) * 300)
        for k in range(7):                                       # a curving wake as she turns into the wind
            pygame.draw.arc(screen, (220, 240, 250), (x + 300 - k * 10, 330 + k * 4, 420 + k * 30, 60 + k * 10), 3.4, 5.6, 2)
        screen.blit(fleet.carrier(), (x, 320 - 132 + int(bob(t))))
        screen.blit(zoom(fleet.destroyer(), 0.6), (60 + int(t * 6), 312 - 47 + int(bob(t, 2, 2))))
    s4 = dict(dur=8.0, draw=turn, say=[(1.2, "poppa", "angry", "Carrier is into the wind. Bring my birds home. In one piece!")])
    return [s1, s2, s3, s4, flex_shot()]


def bb_draw(screen, x, y, elev, scale=1.0):
    """The battleship with its nine guns raised to `elev` radians. Returns the three muzzle points."""
    bb = fleet.battleship() if scale == 1.0 else _c.setdefault(("bb", scale), zoom(fleet.battleship(), scale))
    out = []
    for gx, gy, d in fleet.BB_GUNS:
        rx, ry = x + gx * scale, y + gy * scale
        L = 62 * scale
        ex, ey = rx + d * math.cos(elev) * L, ry - math.sin(elev) * L
        for k in (-3, 0, 3):
            pygame.draw.line(screen, (60, 66, 78), (int(rx), int(ry + k * scale)), (int(ex), int(ey + k * scale)), max(2, int(3 * scale)))
        out.append((ex, ey, d))
    screen.blit(bb, (int(x), int(y)))
    return out


def piece_battleship():
    def emerge(screen, t):
        backdrop(screen, t, STORM, clouds=5, stage=1)
        if int(t * 1.3) % 3 == 0 and (t * 1.3) % 1 < 0.12:
            screen.fill((60, 60, 70), special_flags=pygame.BLEND_RGB_ADD)
            lightning(screen, 560, int(t))
        x = -540 + ease(t / 7.5) * 620
        bb_draw(screen, x, 392 - 116 + bob(t, 0, 2), 0.05)
        for k in range(6):
            pygame.draw.ellipse(screen, (220, 230, 240), (int(x + 480 + k * 8), 384 + k * 3, 40 - k * 4, 10))
        rain(screen, t)
    s1 = dict(dur=9.0, draw=emerge, sfx=((2.3, "as_thunder"), (6.9, "as_thunder")),
              caption=("Out of the storm: an old battleship,", "called back for one more fight."),
              say=[(5.0, "poppa", "angry", "They pulled the old girl out of the museum?! ...Good.")])

    salvos = (4.6, 7.6)

    def broadside(screen, t):
        sx, sy = 0, 0
        for ts in salvos:
            a, b = shake_of(t, ts, 14, 0.9)
            sx, sy = sx + a, sy + b
        backdrop(screen, t, STORM, clouds=5, stage=1)
        swarm(screen, t, "bomber", 5, 6, 60, 50, 130, 1.3)
        elev = 0.05 + 0.42 * ease((t - 1.0) / 3.0)
        mz = bb_draw(screen, 130 + sx, 400 - 116 + bob(t, 0, 2) + sy, elev)
        for ts in salvos:
            u = (t - ts) / 1.6
            for ex, ey, d in mz:
                muzzle(screen, ex, ey, elev if d > 0 else math.pi - elev, 80, u)
            if 0 <= t - ts < 0.1:
                screen.fill((120, 110, 90), special_flags=pygame.BLEND_RGB_ADD)
            if 0 <= u < 1:                                        # the blast flattens the sea beside her
                w = int(600 * u)
                pygame.draw.ellipse(screen, (200, 214, 226), (390 - w // 2, 424, w, 20 + int(20 * u)), 3)
        rain(screen, t)
    s2 = dict(dur=10.5, draw=broadside, sfx=tuple((ts, "as_broadside") for ts in salvos),
              say=[(1.0, "kj", "alarm", "Those guns are older than all of us put together."),
                   (5.6, "stephen", "grin", lines.OLD_MAN_STEPHEN), (8.4, "heather", "calm", "It's a ship, honey. Ships are a she.")])

    def shells(screen, t):
        screen.blit(fleet.sky((20, 26, 38), (60, 70, 86)), (0, 0))
        for i in range(5):
            screen.blit(world.cloud(1, i % 3), (int((i * 230 - t * 50) % 1000 - 150), 60 + (i * 71) % 300))
        bomber = _c.setdefault("bomber_big", zoom(art.alien("bomber"), 2.4, 90))
        for i in range(4):
            th = 2.0 + i * 1.1
            bx, by = 760 - i * 150, 110 + (i % 2) * 110
            for k in range(3):
                u = (t - (th - 1.0) - k * 0.06) / 1.0
                if 0 < u < 1:
                    x, y = -40 + (bx + 40) * u, 440 + (by - 440) * u - math.sin(u * math.pi) * 60 + k * 10
                    pygame.draw.line(screen, (255, 200, 120), (int(x - 30), int(y + 12)), (int(x), int(y)), 4)
                    pygame.draw.circle(screen, (60, 60, 66), (int(x), int(y)), 5)
            if t < th:
                put(screen, bomber, bx - t * 20, by)
            else:
                blast(screen, bx - th * 20, by, t, th, 90, 0.9)
                blast(screen, bx - th * 20 + 40, by - 30, t, th + 0.15, 60, 0.8)
                falling(screen, art.alien("bomber"), t, th + 0.2, (bx - th * 20, by), -50, 520, spin=120)
        if (t * 1.1) % 1 < 0.08:
            screen.fill((50, 50, 60), special_flags=pygame.BLEND_RGB_ADD)
            lightning(screen, 200 + int(t) * 90 % 500, int(t * 3))
        rain(screen, t, 50)
    s3 = dict(dur=8.5, draw=shells, sfx=tuple((2.0 + i * 1.1, "as_boom_big") for i in range(4)))

    def dive(screen, t):
        backdrop(screen, t, STORM, clouds=4, stage=1)
        screen.blit(fleet.carrier(), (150, 330 - 132 + int(bob(t))))
        bb_draw(screen, -260, 430 - 116 + bob(t, 1, 2), 0.4, 1.0)
        for i, (ts, x) in enumerate(((1.4, 120), (2.8, 700), (4.0, 420))):
            u = (t - ts + 1.2) / 1.2                             # bombs fall, and miss
            if 0 < u < 1:
                pygame.draw.circle(screen, (90, 170, 255), (int(x + 80 * (1 - u)), int(60 + 280 * u * u)), 6)
            splash(screen, x, 344, t, ts, 90)
        dv = _c.setdefault("bomber_dive", zoom(art.alien("bomber"), 2.0, 140))
        u = t / 6.0
        if t < 6.0:
            put(screen, dv, 860 - u * 500, 40 + u * 190)
            tracers(screen, t, (420, 250), (860 - u * 500, 40 + u * 190), n=10, speed=3.0, jitter=14)
            tracers(screen, t, (160, 330), (860 - u * 500, 40 + u * 190), n=8, speed=2.4, jitter=14)
        else:
            blast(screen, 360, 230, t, 6.0, 110, 1.0)
            blast(screen, 400, 210, t, 6.2, 70, 0.9)
        rain(screen, t)
    s4 = dict(dur=8.5, draw=dive, sfx=((1.4, "as_splash"), (2.8, "as_splash"), (4.0, "as_splash"), (6.0, "as_boom_big")),
              say=[(6.4, "kj", "grin", lines.KILL_KJ[1] + " Everybody plays defense.")])
    return [s1, s2, s3, s4, flex_shot()]


def islands_far(screen, t, speed=0.0, horizon=300):
    rng = random.Random(5)
    for i in range(5):
        w, h = rng.randrange(150, 300), rng.randrange(30, 80)
        x = (rng.randrange(0, 1200) + t * speed) % 1300 - 300
        pygame.draw.ellipse(screen, (60, 130, 90), (int(x), horizon - h // 2, w, h))
        pygame.draw.ellipse(screen, (90, 160, 100), (int(x + w * 0.2), horizon - h // 2 + 4, int(w * 0.5), h // 2))
        pygame.draw.rect(screen, (236, 222, 170), (int(x + 10), horizon - 3, w - 20, 5))


def piece_submarine():
    gun = lambda: _c.setdefault("gun_side", zoom(art.alien("gunship"), 1.8, 90))

    def hunt(screen, t):
        backdrop(screen, t, TROPIC, sun=(140, 100, (255, 240, 170)), clouds=3)
        islands_far(screen, t)
        fleet.waves(screen, 304, t, TROPIC[2], TROPIC[3])
        for i in range(3):
            x, y = 880 - t * 70 - i * 210, 150 + i * 34 + math.sin(t * 2 + i) * 8
            beam = pygame.Surface((160, 300), pygame.SRCALPHA)
            sw = math.sin(t * 1.4 + i * 2) * 50
            pygame.draw.polygon(beam, (120, 200, 255, 60), [(80, 0), (30 + sw, 300), (130 + sw, 300)])
            screen.blit(beam, (int(x - 80), int(y)))
            put(screen, gun(), x, y)
    s1 = dict(dur=8.0, draw=hunt, caption=("The channel between the islands.", "They are hunting for something."))

    def surface(screen, t):
        backdrop(screen, t, TROPIC, sun=(140, 100, (255, 240, 170)), clouds=3, horizon=320)
        islands_far(screen, t, horizon=320)
        fleet.waves(screen, 324, t, TROPIC[2], TROPIC[3])
        u = ease((t - 2.0) / 3.0)
        y = 400 - 46 + 70 * (1 - u)
        if t > 1.0:
            for k in range(14):                                  # the sea boils
                bx = 230 + k * 26 + math.sin(t * 9 + k) * 6
                r = int(6 + 6 * math.sin(t * 7 + k * 1.3) + 10 * (1 - abs(u - 0.5) * 2))
                pygame.draw.circle(screen, (236, 250, 252), (int(bx), 398), max(2, r))
        screen.blit(fleet.sub(), (220, int(y)))
        pygame.draw.rect(screen, TROPIC[2], (200, 414, 400, 70))
        fleet.waves(screen, 414, t, TROPIC[2], TROPIC[3])
        if 0.2 < u < 1:
            for k in range(10):                                  # water pouring off the hull
                x = 250 + k * 30
                pygame.draw.line(screen, (236, 250, 252), (x, int(y + 34)), (x + 2, 410), 2)
    s2 = dict(dur=10.0, draw=surface, sfx=((2.0, "as_splash"), (3.2, "as_splash")),
              say=[(0.4, "heather", "calm", lines.SCREEN_TIME_HEATHER), (3.6, "stephen", "grin", lines.SCREEN_TIME_STEPHEN),
                   (6.8, "kj", "alarm", "Uh. Guys. The ocean just grew a submarine.")])

    def volley(screen, t):
        sx, sy = shake_of(t, 1.0, 5, 0.5)
        backdrop(screen, t, TROPIC, clouds=3, horizon=320)
        islands_far(screen, t, horizon=320)
        fleet.waves(screen, 324, t, TROPIC[2], TROPIC[3])
        tg = [(680 - i * 90, 90 + (i % 3) * 50) for i in range(6)]
        for i, (tx, ty) in enumerate(tg):
            ts = 1.0 + i * 1.0
            if t < ts + 1.6:
                put(screen, gun(), tx + math.sin(t * 2 + i) * 10, ty)
            else:
                falling(screen, art.alien("gunship"), t, ts + 1.6, (tx, ty), -30 + i * 14, 322, spin=160)
            rocket(screen, t, ts, 1.6, (286 + i * 14 + sx, 392 + sy), (tx, ty), lift=170, boom=54, smoke=(236, 238, 242))
        screen.blit(fleet.sub(), (220 + sx, 400 - 46 + int(bob(t, 0, 2)) + sy))
        pygame.draw.rect(screen, TROPIC[2], (200, 416, 400, 70))
        fleet.waves(screen, 416, t, TROPIC[2], TROPIC[3])
    s3 = dict(dur=10.5, draw=volley, sfx=tuple((1.0 + i, "as_radar") for i in range(6)) + tuple((2.6 + i, "as_boom_big") for i in range(6)),
              say=[(5.0, "alex", "grin", "I like that boat. Can we keep that boat?")])

    def race(screen, t):
        backdrop(screen, t, TROPIC, clouds=3, horizon=300)
        islands_far(screen, t, speed=60)
        fleet.waves(screen, 304, t, TROPIC[2], TROPIC[3], drift=220)
        dd = _c.setdefault("dd_fast", zoom(fleet.destroyer(), 1.5))
        for i, (x0, y, k) in enumerate(((120, 330, 0.7), (300, 400, 1.0))):
            im = dd if k == 1.0 else _c.setdefault("dd_fast2", zoom(fleet.destroyer(), 1.05))
            x = x0 + math.sin(t * 0.6 + i) * 30
            yy = y - int(im.get_height() * 0.87) + int(bob(t * 2, i, 3))
            screen.blit(im, (int(x), yy))
            bx = x + im.get_width() - 14
            for q in range(7):                                   # the bow wave
                pygame.draw.circle(screen, (240, 250, 252), (int(bx - q * 13 * k + math.sin(t * 20 + q) * 3), int(y - 4 - q * (5 - q) * 1.4 * k)), int((9 - q) * k) + 2)
            for q in range(10):
                pygame.draw.line(screen, (226, 244, 248), (int(x - q * 30), y + 2), (int(x - q * 30 - 18), y + 2 + q), 2)
            if (t * 1.2 + i * 0.5) % 1 < 0.25:                   # the deck gun
                muzzle(screen, x + im.get_width() * 0.92, yy + im.get_height() * 0.44, 0.2, 40 * k, ((t * 1.2 + i * 0.5) % 1) / 0.6)
    s4 = dict(dur=8.0, draw=race, sfx=((0.4, "as_shot"), (1.3, "as_shot"), (2.1, "as_shot"), (3.0, "as_shot")),
              say=[(2.0, "poppa", "angry", "Channel is clear. Somebody tell that submarine I said thank you. QUIETLY.")])
    return [s1, s2, s3, s4, flex_shot()]


def mothership(screen, x, y, t, split=0.0, burn=1.0):
    """The Red Star, hanging in the sky. split 0 to 1 breaks her back and drops the halves."""
    for side in (-1, 1):
        dx = side * split * 90
        dy = split * split * 330
        ang = side * split * 0.5
        ca, sa = math.cos(ang), math.sin(ang)
        hull = [(0, -30), (side * 330, -46), (side * 400, -8), (side * 300, 40), (side * 120, 64), (0, 56)]
        pts = [(x + dx + px * ca - py * sa, y + dy + px * sa + py * ca) for px, py in hull]
        pygame.draw.polygon(screen, (16, 20, 32), pts)
        ridge = [(0, -30), (side * 330, -46), (side * 300, -24), (0, -8)]
        pygame.draw.polygon(screen, (38, 56, 104), [(x + dx + px * ca - py * sa, y + dy + px * sa + py * ca) for px, py in ridge])
        for k in range(8):
            px, py = side * (40 + k * 40), 18 + (k % 2) * 14
            col = (90, 170, 255) if burn < 2 or k % 3 else (255, 150, 60)
            pygame.draw.circle(screen, col, (int(x + dx + px * ca - py * sa), int(y + dy + px * sa + py * ca)), 4)
        if split > 0.02:
            for k in range(5):
                pygame.draw.circle(screen, (255, 170, 60), (int(x + dx + side * 8), int(y + dy - 20 + k * 18)), 14 - k)
    if split < 0.02:
        pygame.draw.circle(screen, (120, 20, 30), (int(x), int(y + 10)), 40)
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            r = 32 if i % 2 == 0 else 13
            pts.append((x + math.cos(a) * r, y + 10 + math.sin(a) * r))
        pygame.draw.polygon(screen, (255, 50, 50), pts)


def piece_everything():
    def looming(screen, t):
        backdrop(screen, t, DAWN, clouds=0)
        mothership(screen, 400 + math.sin(t * 0.4) * 10, 130 + ease(t / 8) * 20, t)
        for i in range(6):
            blast(screen, 180 + (i * 137) % 460, 120 + (i * 41) % 60, t % 2.4, i * 0.4, 50, 0.8)
        screen.blit(zoom(fleet.carrier(), 0.7), (190, 320 - 92 + int(bob(t))))
        screen.blit(zoom(fleet.destroyer(), 0.6), (40, 352 - 47 + int(bob(t, 1))))
        screen.blit(zoom(fleet.destroyer(), 0.6), (600, 346 - 47 + int(bob(t, 2))))
    s1 = dict(dur=8.5, draw=looming, caption=("The Red Star is dying.", "The fleet is going to make sure."),
              say=[(4.4, "poppa", "angry", "Every ship. Every gun. Everything you have got. NOW!")])

    def everything(screen, t):
        sx, sy = shake_of(t % 3.0, 0.8, 9, 0.8)
        backdrop(screen, t, DAWN, clouds=0, horizon=320)
        mx, my = 400 + math.sin(t * 0.4) * 10, 120
        mothership(screen, mx, my, t, burn=2)
        elev = 0.5
        mz = bb_draw(screen, -150 + sx, 440 - 116 + bob(t, 0, 2) + sy, elev)
        for ts in (0.8, 3.8, 6.8, 9.8):
            for ex, ey, d in mz:
                if d > 0:
                    muzzle(screen, ex, ey, elev, 70, (t - ts) / 1.5)
            for k in range(3):
                blast(screen, 240 + k * 70, my + 10 + k * 8, t, ts + 0.7 + k * 0.1, 60, 0.9)
        screen.blit(zoom(fleet.carrier(), 0.62), (250, 338 - 82 + int(bob(t, 3))))
        dd = _c.setdefault("dd_mid", zoom(fleet.destroyer(), 0.9))
        screen.blit(dd, (430, 392 - 70 + int(bob(t, 1))))
        screen.blit(fleet.sub(), (520, 446 - 46 + int(bob(t, 2, 2))))
        for i in range(10):                                      # destroyer and submarine missiles
            src = (470 + (i % 2) * 150, 330) if i % 2 == 0 else (600 + (i % 3) * 16, 438)
            rocket(screen, t, 0.5 + i * 1.05, 1.5, src, (mx - 200 + (i * 97) % 420, my + (i % 3) * 14), lift=120, boom=58)
        tracers(screen, t, (330, 330), (mx, my + 30), n=10, speed=2.8, jitter=24)
        tracers(screen, t, (540, 350), (mx + 150, my + 30), n=8, speed=2.4, jitter=24)
    s2 = dict(dur=12.5, draw=everything,
              sfx=tuple((ts, "as_broadside") for ts in (0.8, 3.8, 6.8, 9.8)) + tuple((2.0 + i * 1.05, "as_boom_big") for i in range(10)),
              say=[(2.0, "heather", "grin", lines.REEL_HEATHER), (5.4, "stephen", "grin", "Get my good side. And the battleship."),
                   (8.6, "kj", "grin", lines.KILL_KJ[0])])

    def fall(screen, t):
        sx, sy = shake_of(t, 5.6, 16, 2.0)
        backdrop(screen, t, DAWN, clouds=0, horizon=320)
        split = ease((t - 1.0) / 4.6)
        if t < 5.6:
            mothership(screen, 400, 140, t, split=split, burn=2)
            for i in range(8):
                blast(screen, 240 + (i * 61) % 320, 120 + (i * 29) % 70 + split * 200, t, 0.3 + i * 0.5, 70, 0.8)
        else:
            for side in (-1, 1):
                splash(screen, 400 + side * 190, 322, t, 5.6, 260)
                splash(screen, 400 + side * 80, 322, t, 5.9, 180)
            if t < 5.8:
                screen.fill((255, 255, 255))
        amp = 3 + (14 * max(0, 1 - abs(t - 7.2) / 2.0) if t > 5.6 else 0)   # the swell rocks the fleet
        screen.blit(zoom(fleet.carrier(), 0.7), (180 + sx, 360 - 92 + int(bob(t * 1.6, 0, amp)) + sy))
        screen.blit(zoom(fleet.destroyer(), 0.6), (30 + sx, 392 - 47 + int(bob(t * 1.6, 1, amp)) + sy))
        screen.blit(zoom(fleet.destroyer(), 0.6), (610 + sx, 386 - 47 + int(bob(t * 1.6, 2, amp)) + sy))
    s3 = dict(dur=10.5, draw=fall, sfx=((1.0, "as_boom_big"), (2.4, "as_boom_big"), (4.0, "as_boom_big"), (5.6, "as_splash"), (5.7, "as_broadside")),
              say=[(1.2, "kj", "alarm", "She is breaking up! She is coming DOWN!"), (7.4, "alex", "grin", "And the crowd goes wild.")])

    def quiet(screen, t):
        backdrop(screen, t, DUSK, sun=(400, 300 - int(ease(t / 8) * 70), (255, 200, 120)), clouds=0)
        fleet.waves(screen, 300, t, DUSK[2], DUSK[3])
        for x in (200, 600):
            for k in range(9):
                pygame.draw.circle(screen, (60 + k * 8, 50 + k * 8, 70 + k * 8), (x + int(math.sin(t * 0.7 + k) * 6) + k * 6, 292 - k * 22), 8 + k * 3)
        screen.blit(zoom(fleet.carrier(), 0.8), (150, 350 - 106 + int(bob(t))))
        screen.blit(zoom(fleet.battleship(), 0.5), (20, 330 - 58 + int(bob(t, 1))))
        screen.blit(zoom(fleet.destroyer(), 0.6), (610, 336 - 47 + int(bob(t, 2))))
    s4 = dict(dur=8.5, draw=quiet, caption=("And then it was quiet.",),
              say=[(3.0, "poppa", "angry", "...Fine. That was acceptable. Now land my airplanes!")])
    return [s1, s2, s3, s4, flex_shot()]


# ------------------------------------------------------------------ the ending
def ending(game):
    def deck(screen, t):
        backdrop(screen, t, DUSK, sun=(620, 250, (255, 200, 120)), clouds=2)
        screen.blit(fleet.carrier(), (90, 350 - 132 + int(bob(t))))
        rng = random.Random(2)
        for i in range(40):                                      # the whole crew, jumping
            x = 120 + rng.randrange(0, 560)
            j = abs(math.sin(t * 5 + i)) * 8
            col = rng.choice(((240, 200, 60), (60, 160, 80), (220, 60, 60), (80, 120, 220), (240, 240, 240), (150, 90, 170)))
            pygame.draw.rect(screen, col, (x, int(350 - 132 + 76 - j + bob(t)), 4, 9))
        for i in range(5):                                       # flares
            u = (t * 0.5 + i * 0.2) % 1
            pygame.draw.circle(screen, (255, 240, 180), (160 + i * 120, int(210 - u * 130)), 4)
    s1 = dict(dur=8.0, draw=deck, caption=("The Pacific. That evening.", "Every jet came home."))

    def group(screen, t):
        screen.blit(fleet.sky(DUSK[0], DUSK[1]), (0, 0))
        say = group_say
        cur = [s for s in say if s[0] <= t]
        speaker, mood = (cur[-1][1], cur[-1][2]) if cur else (None, "calm")
        for i, who in enumerate(("stephen", "heather", "poppa", "alex", "kj")):
            m = "angry" if who == "poppa" else (mood if who == speaker else "calm")
            if m == "flex":
                m = "grin"
            k = 1.08 if who == speaker else 1.0
            put(screen, zoom(art.portrait(who, m, 150), k), 90 + i * 155, 170)
    group_say = [(0.4, "poppa", "angry", "Four landings. Zero airplanes bent. I am almost not angry."),
                 (4.0, "stephen", "grin", lines.OLD_MAN_STEPHEN),
                 (6.6, "poppa", "angry", "WHO are you calling old?!"),
                 (9.2, "heather", "grin", "Somebody please tell me one of you filmed that."),
                 (12.2, "alex", "grin", "World: saved. " + lines.IMPROV_ALEX),
                 (16.2, "kj", "grin", "Go. I have practice. My team has a game Saturday.")]
    s2 = dict(dur=19.5, draw=group, say=group_say)

    credits = ["ALIEN STORM", "TOM CAT ALLEY", "", "THE CREW", "Alex,  pilot", "KJ,  radar intercept officer", "Stephen,  pilot",
               "Heather,  radar intercept officer", "Angry Poppa,  landing signal officer", "", "THE FLEET",
               "One carrier, three destroyers,", "one very old battleship,", "and a submarine nobody saw", "",
               "All art, music and sound made in code", "", "Made for the family", "", "THE END"]

    def roll(screen, t):
        backdrop(screen, t, DUSK, sun=(400, 250, (255, 200, 120)), clouds=2)
        screen.blit(zoom(fleet.carrier(), 0.5), (40 + int(t * 6), 340 - 66))
        for i, sq in enumerate((1, 2)):
            jet = zoom(art.tomcat(1.0, sq, 4, 1.0), 1.2, -90)
            put(screen, jet, (t * 120 - i * 110) % 1100 - 100, 110 + i * 34)
        for i, row in enumerate(credits):
            y = SH - 20 + i * 38 - t * 34
            if BAR - 30 < y < SH:
                big = row in ("ALIEN STORM", "TOM CAT ALLEY", "THE END", "THE CREW", "THE FLEET")
                hud.label(screen, row, (400, int(y)), 44 if big else 30, (255, 214, 90) if big else (255, 255, 255), center=True, bold=big)
    s4 = dict(dur=(SH + len(credits) * 38) / 34 + 1.5, draw=roll)

    def after():
        game.win = True
        game.game_over()
    return Scene(game, [s1, s2, flex_shot(), improv_show(), s4], after=after, music="as_anthem")


# ------------------------------------------------------------------ the landing, graded by Angry Poppa
GRADES = {
    3: ("OK. THREE WIRE.", "Three wire. OK pass. ...Do not let it go to your head.", 3000),
    2: ("FAIR. TWO WIRE.", "Two wire. A little low. I have seen worse. From you.", 1800),
    4: ("FAIR. FOUR WIRE.", "Four wire. Long! You nearly went swimming off the front.", 1500),
    1: ("NO GRADE. ONE WIRE.", "ONE WIRE?! Were you trying to land in my hangar bay?!", 600),
    0: ("NO GRADE.", "I am calling that a landing because the airplane is on the boat. Barely.", 200),
}


class Landing:
    """Fly the approach: line up on the angled deck, hold the glide path, catch a wire."""
    APPROACH = 11.0

    def __init__(self, game):
        self.game = game
        self.t, self.d = 0.0, 1.0                    # d: distance to the wires, 1 down to 0
        self.x, self.alt, self.vy = 200.0 + game.rng.uniform(-60, 60), 1.05, 0.0
        self.tries, self.state, self.state_t = 0, "approach", 0.0
        self.grade, self.call, self.line = None, "", ""
        self.roll = 0.0
        game.sound.music("as_anthem")
        self.car = art.carrier(360)
        self.say("Paddles has you. Line it up and keep it coming.")

    def say(self, line):
        self.line, self.line_t = line, 3.0

    def target_x(self):
        t = self.t if self.state != "trap" else self.trap_at
        return 200 + math.sin(t * 0.5) * 34          # the ship is moving too

    def update(self, dt, inp):
        g = self.game
        self.t += dt
        self.state_t += dt
        self.line_t -= dt
        if self.state == "approach":
            self.d = max(0.0, self.d - dt / self.APPROACH)
            dx = ("right" in inp.held) - ("left" in inp.held)
            self.x = max(60, min(340, self.x + dx * 80 * dt + math.sin(self.t * 0.9) * 6 * dt))
            power = (1 if ("a" in inp.held or "up" in inp.held) else 0) - (1 if ("b" in inp.held or "down" in inp.held) else 0)
            self.vy += (power * 0.16 - 0.03 - self.vy) * min(1, dt * 3)
            self.alt = max(-0.2, min(1.4, self.alt + (self.vy - 1 / self.APPROACH) * dt))
            off, ge = self.x - self.target_x(), self.alt - self.d
            if self.line_t <= 0.8:
                if ge < -0.07:
                    self.say("POWER! You are low! POWER!")
                elif ge > 0.09:
                    self.say("You are HIGH! Ease it down!")
                elif off > 16:
                    self.say("Come LEFT for line up!")
                elif off < -16:
                    self.say("Come RIGHT for line up!")
            if self.d <= 0:
                self.judge(off, ge)
        elif self.state == "trap":
            self.roll = min(1.0, self.state_t / 0.9)
            if self.state_t > 4.2 or (self.state_t > 1.5 and "a" in inp.pressed):
                g.score += GRADES[self.grade][2]
                g.grades.append(self.grade)
                return True
        elif self.state == "around":
            if self.state_t > 2.6:
                self.state, self.state_t, self.d, self.alt, self.vy = "approach", 0.0, 1.0, 1.05, 0.0
        return False

    def judge(self, off, ge):
        g = self.game
        last = self.tries >= 2
        if abs(off) > 24 and not last:
            self.tries += 1
            self.state, self.state_t, self.call = "around", 0.0, "WAVE OFF!"
            self.say("WAVE OFF! WAVE OFF! Line it up and try again!")
            g.sfx("as_warning")
            return
        if ge > 0.10 and not last:
            self.tries += 1
            self.state, self.state_t, self.call = "around", 0.0, "BOLTER!"
            self.say("BOLTER! BOLTER! Go around, and do it RIGHT!")
            g.sfx("as_warning")
            return
        if abs(off) > 24 or ge > 0.10:
            self.grade = 0
        elif ge > 0.04:
            self.grade = 4
        elif ge > -0.035:
            self.grade = 3
        elif ge > -0.085:
            self.grade = 2
        else:
            self.grade = 1
        self.state, self.state_t, self.trap_at = "trap", 0.0, self.t
        self.call = GRADES[self.grade][0]
        self.say(GRADES[self.grade][1])
        self.line_t = 9.0
        g.sfx("as_wire")

    def after(self):
        g = self.game
        if g.stage + 1 >= 4:
            g.scene = ending(g)
        else:
            g.begin_stage(g.stage + 1)
            g.scene = takeoff(g)

    # the playfield, on the small canvas
    def draw(self, surf):
        from ..common import text, W, H, WHITE, YELLOW
        sea = world.sea(0)
        off = int(self.t * 90) % 480
        surf.blit(sea, (0, off - 480))
        surf.blit(sea, (0, off))
        k = 1.2
        tx = self.target_x()
        d = self.d if self.state == "approach" else (0.0 if self.state == "trap" else -self.state_t * 0.2)
        wires_y = 150 - d * 300                       # where the wires are on screen
        cx = tx - 46 * k                              # carrier left edge so the landing area is under the jet
        cy = wires_y - 245 * k
        for q in range(1, 9):                         # wake astern
            y = cy + 360 * k + q * 22
            pygame.draw.line(surf, (200, 226, 240), (int(cx + 62 - q * 9), int(y)), (int(cx + 62 + q * 9), int(y)), 2)
        surf.blit(self.car, (int(cx), int(cy)))
        jy = 168
        alt = max(0.0, self.alt if self.state == "approach" else (0.0 if self.state == "trap" else self.state_t * 0.4))
        jx = self.x
        if self.state == "trap":
            jy = 168 - self.roll * 26 - (self.grade - 2) * 12 if self.grade else 168 - self.roll * 20
            pygame.draw.line(surf, (20, 20, 24), (int(jx) - 22, int(jy) + 26), (int(jx), int(jy) + 18 - int(self.roll * 8)), 1)
            pygame.draw.line(surf, (20, 20, 24), (int(jx) + 22, int(jy) + 26), (int(jx), int(jy) + 18 - int(self.roll * 8)), 1)
        elif self.state == "around":
            jy = 168 - self.state_t * 90
        sh = pygame.Surface((26, 34), pygame.SRCALPHA)   # the jet's shadow shows its height
        pygame.draw.ellipse(sh, (0, 0, 0, 70), (0, 0, 26, 34))
        surf.blit(sh, (int(jx) - 13 + int(alt * 40), int(jy) - 17 + int(alt * 60)))
        im = art.tomcat(0.0, 1, 0, 0.2 if self.state != "around" else 1.0)
        zk = 0.62 * (1 + alt * 0.5)
        im = pygame.transform.smoothscale(im, (int(56 * zk), int(72 * zk)))
        surf.blit(im, (int(jx) - im.get_width() // 2, int(jy) - im.get_height() // 2))
        # the meatball: keep the amber ball between the green bars
        bx, by = W - 26, 70
        pygame.draw.rect(surf, (20, 22, 30), (bx - 12, by - 44, 24, 88))
        pygame.draw.rect(surf, (60, 220, 90), (bx - 11, by - 2, 7, 4))
        pygame.draw.rect(surf, (60, 220, 90), (bx + 4, by - 2, 7, 4))
        ge = (self.alt - self.d) if self.state == "approach" else 0.0
        yb = by - max(-38, min(38, ge * 300))
        pygame.draw.circle(surf, (255, 190, 60) if ge > -0.085 else (255, 60, 60), (bx, int(yb)), 5)
        text(surf, "GLIDE", (bx, by + 48), 12, WHITE, center=True)
        off = self.x - tx                             # line up bar
        pygame.draw.rect(surf, (20, 22, 30), (W // 2 - 50, 222, 100, 10))
        pygame.draw.rect(surf, (60, 220, 90), (W // 2 - 8, 222, 16, 10))
        pygame.draw.rect(surf, (255, 190, 60), (int(W // 2 + max(-48, min(46, off * 1.6))) - 2, 221, 4, 12))
        text(surf, "LINE UP", (W // 2, 208), 12, WHITE, center=True)
        if self.state == "approach" and self.t < 4:
            text(surf, "Left / right: line up", (W // 2, 40), 16, WHITE, center=True)
            text(surf, "Big button: power    Triangle: ease off", (W // 2, 56), 16, WHITE, center=True)
        if self.state in ("trap", "around"):
            text(surf, self.call, (W // 2, 70), 30, YELLOW if self.state == "trap" else (255, 90, 80), center=True)
            if self.state == "trap":
                text(surf, "+%d" % GRADES[self.grade][2], (W // 2, 98), 20, WHITE, center=True)

    def draw_hd(self, screen):
        if self.line_t > 0 and self.line:
            hud.bubble(screen, "poppa", "angry", self.line, 6, 6, size=84, width=380)
