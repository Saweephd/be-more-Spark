"""Momma Rose's Air Hockey: first to five goals wins.

    D-pad        move your paddle (your half of the table)
    Big button   hold for a burst of speed
    Touch        drag on the screen to move the paddle

Pick how tough Momma Rose plays on the title screen. A second controller takes
over Momma Rose's paddle for a two player game.

All characters, art, sounds and music here are original to this project.
"""
import math

import pygame

from . import common as c
from . import move_art as art
from .common import H, W, Game, text

TW, TL = 200.0, 300.0            # table size in table units
GOAL = 38.0                      # half the goal mouth
PUCK_R, PAD_R = 7.0, 13.0
WIN = 5
FAR_Y, NEAR_Y = 92, 232
MODES = ("Easy Going", "Game Night", "Momma Means Business")
SKILL = (dict(speed=105, aim=30, hit=150, lag=0.30), dict(speed=160, aim=14, hit=220, lag=0.16),
         dict(speed=225, aim=4, hit=300, lag=0.05))
ROSE_SCORES = ("Not in my house!", "Momma's still got it!", "Too slow, baby!", "And that's how it's done.")
YOU_SCORE = ("Ooh, nice one, baby.", "Okay, okay. I see you.", "Lucky shot!", "Who taught you that?")


def project(x, y):
    """Table units to screen pixels: the far end is narrower."""
    k = y / TL
    return 200 + (x / TW - 0.5) * (208 + 136 * k), FAR_Y + (NEAR_Y - FAR_Y) * k


def unproject(sx, sy):
    k = max(0.0, min(1.0, (sy - FAR_Y) / (NEAR_Y - FAR_Y)))
    return ((sx - 200) / (208 + 136 * k) + 0.5) * TW, k * TL


def scale_at(y):
    return 0.62 + 0.38 * y / TL


class AirHockey(Game):
    name = "air_hockey"
    players_max = 2         # the second controller is player two, not a copy of player one
    title = "Air Hockey"
    music = "air_hockey"
    title_color = (120, 200, 255)
    help_lines = ("D-pad or touch: move your paddle", "Hold the big button for a burst", "First to 5 beats Momma Rose!")
    modes = MODES

    def __init__(self, **kw):
        super().__init__(**kw)
        self.rose_art = {(m, l): art.rose(m, l) for m in ("smile", "smug", "oops") for l in (-3, 0, 3)}
        self.rose_big = pygame.transform.scale2x(art.rose("smile"))
        self.table = None
        self.intro_seen = False
        self.reset()

    def reset(self):
        self.score = 0
        self.win = False
        self.you, self.rose = 0, 0
        self.two = False
        self.me = {"x": TW / 2, "y": TL - 40, "vx": 0.0, "vy": 0.0}
        self.her = {"x": TW / 2, "y": 40.0, "vx": 0.0, "vy": 0.0}
        self.mood, self.mood_t, self.line = "smile", 0.0, None
        self.trail, self.sparks = [], []
        self.flash = 0.0
        self.shake = 0.0
        self.aim_err, self.aim_t = 0.0, 0.0
        self.stuck = 0.0
        self.serve(to_rose=False)
        self.phase, self.pt = ("play", 0.0) if self.intro_seen else ("intro", 0.0)

    def serve(self, to_rose):
        self.puck = {"x": TW / 2, "y": TL / 2 + (-50 if to_rose else 50), "vx": 0.0, "vy": 0.0}
        self.wait = 0.9

    # ------------------------------------------------------------ update
    def update(self, dt, inp):
        self.pt += dt
        if self.phase == "intro":
            if self.pt > 6.0 or (self.pt > 0.4 and ("a" in inp.pressed or "b" in inp.pressed)):
                self.intro_seen = True
                self.phase, self.pt = "play", 0.0
            return
        self.mood_t = max(0.0, self.mood_t - dt)
        if self.mood_t <= 0 and self.phase == "play":
            self.mood, self.line = "smile", None
        self.flash = max(0.0, self.flash - dt)
        self.shake = max(0.0, self.shake - dt)
        self.trail = [(x, y, t - dt) for x, y, t in self.trail if t > dt]
        self.sparks = [[x + vx * dt, y + vy * dt, vx, vy, t - dt] for x, y, vx, vy, t in self.sparks if t > dt]
        if self.phase == "end":
            if self.pt > 3.2:
                self.win = self.you > self.rose
                self.score = max(0, self.you * 100 - self.rose * 20) + (300 + 200 * self.mode if self.win else 0)
                self.game_over()
            return
        p2 = getattr(inp, "p2", None)
        if p2 is not None and not self.two and ("a" in p2.pressed or "start" in p2.pressed):
            self.two = True
            self.sfx("select")
        self.move_player(self.me, inp, dt, TL / 2 + PAD_R, TL - PAD_R)
        if self.two and p2 is not None:
            self.move_player(self.her, p2, dt, PAD_R, TL / 2 - PAD_R)
        else:
            self.move_rose(dt)
        if self.wait > 0:
            self.wait -= dt
            return
        for _ in range(3):                       # small steps so a fast puck never tunnels through a paddle
            if self.step_puck(dt / 3):
                break

    def move_player(self, pad, inp, dt, y0, y1):
        ox, oy = pad["x"], pad["y"]
        speed = 300.0 if "a" in inp.held and inp.touch is None else 195.0
        if inp.touch is not None and pad is self.me:
            tx, ty = unproject(*inp.touch)
            dx, dy = tx - ox, ty - oy
            d = math.hypot(dx, dy)
            step = min(d, 420.0 * dt)
            if d > 0.5:
                pad["x"], pad["y"] = ox + dx / d * step, oy + dy / d * step
        else:
            dx = ("right" in inp.held) - ("left" in inp.held)
            dy = ("down" in inp.held) - ("up" in inp.held)
            if dx or dy:
                n = math.hypot(dx, dy)
                pad["x"], pad["y"] = ox + dx / n * speed * dt, oy + dy / n * speed * dt
        self.clamp(pad, y0, y1, ox, oy, dt)

    def clamp(self, pad, y0, y1, ox, oy, dt):
        pad["x"] = max(PAD_R, min(TW - PAD_R, pad["x"]))
        pad["y"] = max(y0, min(y1, pad["y"]))
        pad["vx"], pad["vy"] = (pad["x"] - ox) / dt, (pad["y"] - oy) / dt

    def move_rose(self, dt):
        sk, pk, pad = SKILL[self.mode], self.puck, self.her
        self.aim_t -= dt
        if self.aim_t <= 0:                      # she misjudges a little, more on the easy settings
            self.aim_t = 0.4 + sk["lag"]
            self.aim_err = self.rng.uniform(-sk["aim"], sk["aim"])
        coming = pk["vy"] < -20
        mine = pk["y"] < TL / 2 + 6
        if mine and (not coming or abs(pk["vy"]) < 140) and pk["y"] > pad["y"] - 4:
            tx, ty = pk["x"] + self.aim_err * 0.3, pk["y"] - 6          # step up and hit it
            speed = sk["hit"]
        elif mine and pk["y"] <= pad["y"]:
            if pk["y"] < PAD_R + PUCK_R + 6:     # it is tucked against her end rail: back off and let it out
                tx, ty = TW / 2, 64.0
            else:                                # get round behind it
                tx, ty = pk["x"] + (20 if pk["x"] < TW / 2 else -20), pk["y"] - 16
            speed = sk["hit"]
        else:
            if coming and pk["vy"] != 0:         # guard the spot it is heading for
                t = (pad["y"] - pk["y"]) / pk["vy"]
                tx = pk["x"] + pk["vx"] * max(0.0, t)
                while tx < 0 or tx > TW:
                    tx = -tx if tx < 0 else 2 * TW - tx
            else:
                tx = pk["x"]
            tx = TW / 2 + (tx - TW / 2) * 0.7 + self.aim_err
            ty, speed = 34.0, sk["speed"]
        ox, oy = pad["x"], pad["y"]
        dx, dy = tx - ox, ty - oy
        d = math.hypot(dx, dy)
        if d > 1.0:
            step = min(d, speed * dt)
            pad["x"], pad["y"] = ox + dx / d * step, oy + dy / d * step
        self.clamp(pad, PAD_R, TL / 2 - PAD_R, ox, oy, dt)

    def step_puck(self, dt):
        pk = self.puck
        pk["x"] += pk["vx"] * dt
        pk["y"] += pk["vy"] * dt
        drag = 0.994 ** (dt * 60)
        pk["vx"] *= drag
        pk["vy"] *= drag
        fast = math.hypot(pk["vx"], pk["vy"])
        for pad in (self.me, self.her):
            dx, dy = pk["x"] - pad["x"], pk["y"] - pad["y"]
            d = math.hypot(dx, dy)
            if 0 < d < PUCK_R + PAD_R:
                nx, ny = dx / d, dy / d
                rvx, rvy = pk["vx"] - pad["vx"], pk["vy"] - pad["vy"]
                along = rvx * nx + rvy * ny
                if along < 0:                    # bounce off the paddle and take some of its swing
                    pk["vx"] -= 1.9 * along * nx
                    pk["vy"] -= 1.9 * along * ny
                    self.sfx("tick")
                    self.spark(pk["x"], pk["y"], 4)
                pk["x"], pk["y"] = pad["x"] + nx * (PUCK_R + PAD_R + 0.5), pad["y"] + ny * (PUCK_R + PAD_R + 0.5)
        sp = math.hypot(pk["vx"], pk["vy"])
        if sp > 560:
            pk["vx"], pk["vy"] = pk["vx"] / sp * 560, pk["vy"] / sp * 560
        if pk["x"] < PUCK_R or pk["x"] > TW - PUCK_R:
            pk["x"] = max(PUCK_R, min(TW - PUCK_R, pk["x"]))
            pk["vx"] = -pk["vx"] * 0.92
            if fast > 120:
                self.sfx("thud")
                self.spark(pk["x"], pk["y"], 5)
        in_goal = abs(pk["x"] - TW / 2) < GOAL - PUCK_R * 0.5
        if pk["y"] < PUCK_R:
            if in_goal:
                return self.goal(mine=True)
            pk["y"], pk["vy"] = PUCK_R, -pk["vy"] * 0.92
        elif pk["y"] > TL - PUCK_R:
            if in_goal:
                return self.goal(mine=False)
            pk["y"], pk["vy"] = TL - PUCK_R, -pk["vy"] * 0.92
        if sp > 200:
            self.trail.append((pk["x"], pk["y"], 0.22))
        # a puck left sitting where nobody can reach it gets a nudge
        self.stuck = self.stuck + dt if sp < 25 else 0.0
        if self.stuck > 1.4:                     # the air table gives it a push back towards the middle
            self.stuck = 0.0
            pk["vy"] = 110.0 if pk["y"] < TL / 2 else -110.0
            pk["vx"] = (TW / 2 - pk["x"]) * 0.8 + self.rng.uniform(-30, 30)
        return False

    def spark(self, x, y, n):
        for _ in range(n):
            a = self.rng.uniform(0, math.tau)
            v = self.rng.uniform(30, 90)
            self.sparks.append([x, y, math.cos(a) * v, math.sin(a) * v, 0.25])

    def goal(self, mine):
        self.flash, self.shake = 0.5, 0.35
        self.sfx("ding" if mine else "hurt")
        if mine:
            self.you += 1
            self.mood, self.line = "oops", self.rng.choice(YOU_SCORE)
        else:
            self.rose += 1
            self.mood, self.line = "smug", self.rng.choice(ROSE_SCORES)
            if self.rose == WIN - 1 and self.you < WIN - 1:
                self.line = "Mahjong is still an option."
        self.mood_t = 2.2
        if self.you >= WIN or self.rose >= WIN:
            self.phase, self.pt = "end", 0.0
            self.mood = "oops" if self.you > self.rose else "smug"
            self.line = "Fine. Best of three?" if self.you > self.rose else "Mahjong next time?"
            self.mood_t = 9.0
            self.sfx("win" if self.you > self.rose else "over")
            self.puck.update(x=TW / 2, y=TL / 2, vx=0.0, vy=0.0)
        else:
            self.serve(to_rose=mine)             # the one who was scored on gets the puck
        return True

    # ------------------------------------------------------------ draw
    def room(self, surf):
        surf.fill((60, 36, 44))
        for x in range(0, W, 40):
            pygame.draw.rect(surf, (72, 44, 54), (x, 0, 20, 96))
        pygame.draw.rect(surf, (120, 80, 50), (300, 34, 74, 5))
        for i in range(5):                       # the mahjong set on the shelf
            pygame.draw.rect(surf, (240, 236, 220), (306 + i * 13, 20, 10, 14), border_radius=2)
            pygame.draw.rect(surf, (90, 170, 120), (306 + i * 13, 31, 10, 3), border_radius=1)
            pygame.draw.circle(surf, ((200, 60, 70), (60, 120, 200))[i % 2], (311 + i * 13, 26), 2)
        pygame.draw.circle(surf, (250, 226, 150), (40, 26), 12)       # a lamp glow
        pygame.draw.circle(surf, (255, 244, 200), (40, 26), 7)

    def table_art(self):
        if self.table is None:
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            pts = [project(0, 0), project(TW, 0), project(TW, TL), project(0, TL)]
            pygame.draw.polygon(s, (30, 38, 60), [(86, 84), (314, 84), (392, 240), (8, 240)])
            pygame.draw.polygon(s, (50, 64, 96), [(90, 87), (310, 87), (384, 240), (16, 240)])
            pygame.draw.polygon(s, (232, 244, 255), pts)
            for r in range(1, 12):               # the little air holes
                y = TL * r / 12
                for q in range(1, 12):
                    x, yy = project(TW * q / 12, y)
                    s.set_at((int(x), int(yy)), (176, 198, 230))
            shine = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.polygon(shine, (255, 255, 255, 110), [project(30, 2), project(62, 2), project(34, TL - 2), project(2, TL - 2)])
            s.blit(shine, (0, 0))
            a, b = project(0, TL / 2), project(TW, TL / 2)
            pygame.draw.line(s, (230, 70, 80), a, b, 2)
            cx, cy = project(TW / 2, TL / 2)
            pygame.draw.ellipse(s, (230, 70, 80), (cx - 30, cy - 13, 60, 26), 2)
            for y, col in ((0, (255, 120, 150)), (TL, (120, 200, 255))):      # goal creases
                gx, gy = project(TW / 2, y)
                wdt = GOAL * 2 * (208 + 136 * y / TL) / TW
                pygame.draw.ellipse(s, col, (gx - wdt / 2, gy - 9, wdt, 18), 1)
            g0, g1 = project(TW / 2 - GOAL, 0), project(TW / 2 + GOAL, 0)
            pygame.draw.rect(s, (14, 14, 22), (g0[0], g0[1] - 5, g1[0] - g0[0], 6))
            g0, g1 = project(TW / 2 - GOAL, TL), project(TW / 2 + GOAL, TL)
            pygame.draw.rect(s, (14, 14, 22), (g0[0], g0[1] - 1, g1[0] - g0[0], 9))
            pygame.draw.lines(s, (120, 200, 255), True, pts, 3)
            pygame.draw.line(s, (200, 236, 255), pts[0], pts[1], 1)
            self.table = s
        return self.table

    def draw_paddle(self, surf, pad, col):
        x, y = project(pad["x"], pad["y"])
        r = PAD_R * scale_at(pad["y"]) * 1.15
        pygame.draw.ellipse(surf, (150, 170, 200), (x - r, y - r * 0.5 + 4, r * 2, r))
        dark = tuple(max(0, v - 60) for v in col)
        pygame.draw.ellipse(surf, dark, (x - r, y - r * 0.5 + 2, r * 2, r))
        pygame.draw.ellipse(surf, col, (x - r, y - r * 0.5 - 1, r * 2, r))
        hi = tuple(min(255, v + 70) for v in col)
        pygame.draw.ellipse(surf, dark, (x - r * 0.5, y - r * 0.3 - 3, r, r * 0.55))
        pygame.draw.ellipse(surf, hi, (x - r * 0.45, y - r * 0.3 - 5, r * 0.9, r * 0.5))

    def draw_rose(self, surf):
        lean = max(-3, min(3, int((self.her["x"] - TW / 2) / 22))) if not self.two else 0
        lean = -3 if lean < -1 else (3 if lean > 1 else 0)
        img = self.rose_art[(self.mood, lean)]
        bob = 0
        if self.mood == "smug" and self.mood_t > 0:          # her little victory dance
            bob = int(abs(math.sin(self.time * 12)) * 4)
            lean_px = int(math.sin(self.time * 6) * 5)
        else:
            lean_px = int((self.her["x"] - TW / 2) * 0.12)
        surf.blit(img, (200 - 43 + lean_px, 2 - bob))
        if self.line and self.mood_t > 0:
            art.bubble(surf, self.line, 318, 58)

    def draw(self, surf):
        if self.phase == "intro":
            self.draw_intro(surf)
            return
        self.room(surf)
        self.draw_rose(surf)
        surf.blit(self.table_art(), (0, 0))
        self.draw_paddle(surf, self.her, (220, 60, 90))
        for x, y, t in self.trail:
            sx, sy = project(x, y)
            r = PUCK_R * scale_at(y) * t / 0.22
            pygame.draw.ellipse(surf, (255, 200, 80), (sx - r, sy - r * 0.5, r * 2, r))
        pk = self.puck
        sx, sy = project(pk["x"], pk["y"])
        r = PUCK_R * scale_at(pk["y"]) * 1.2
        pygame.draw.ellipse(surf, (150, 170, 200), (sx - r, sy - r * 0.5 + 3, r * 2, r))
        pygame.draw.ellipse(surf, (30, 30, 40), (sx - r, sy - r * 0.5, r * 2, r))
        pygame.draw.ellipse(surf, (250, 220, 90), (sx - r * 0.7, sy - r * 0.4, r * 1.4, r * 0.7))
        for x, y, vx, vy, t in self.sparks:
            px, py = project(x, y)
            surf.set_at((int(px), int(py)), (255, 240, 160))
            surf.set_at((int(px) + 1, int(py)), (255, 200, 90))
        self.draw_paddle(surf, self.me, (60, 120, 230))
        pygame.draw.rect(surf, (16, 16, 26), (8, 8, 96, 36), border_radius=4)
        pygame.draw.rect(surf, (70, 80, 110), (8, 8, 96, 36), 1, border_radius=4)
        text(surf, "YOU  %d" % self.you, (16, 11), 18, (120, 200, 255))
        text(surf, "%s %d" % ("P2  " if self.two else "ROSE", self.rose), (16, 26), 18, (255, 120, 150))
        if not self.two:
            text(surf, MODES[self.mode], (56, 48), 12, (200, 200, 210), center=True)
        if self.flash > 0:
            f = pygame.Surface((W, H), pygame.SRCALPHA)
            f.fill((255, 255, 255, int(150 * self.flash / 0.5)))
            surf.blit(f, (0, 0))
            text(surf, "GOAL!", (W // 2, 150), 44, c.YELLOW, center=True)
        if self.phase == "end":
            won = self.you > self.rose
            text(surf, "YOU WIN!" if won else "MOMMA ROSE WINS!", (W // 2, 150), 36, c.YELLOW if won else (255, 120, 150), center=True)
        if self.shake > 0:
            k = int(self.time * 60)
            surf.scroll((k * 7) % 7 - 3, (k * 5) % 5 - 2)

    def draw_intro(self, surf):
        self.room(surf)
        t = self.pt
        surf.blit(self.table_art(), (0, 60))
        slide = min(1.0, t / 0.6)
        surf.blit(self.rose_big, (int(-180 + 200 * slide), 28))
        if 0.8 < t < 4.0:
            art.bubble(surf, "It's either this or mahjong.", 290, 74)
            if t > 1.8:
                art.bubble(surf, "You choose.", 290, 92)
        if t > 2.2:                                           # she taps the mahjong set
            pygame.draw.rect(surf, (255, 240, 150), (302, 16, 72, 26), 1, border_radius=3)
        if t > 4.0:
            x, y = project(TW / 2, TL - 40)
            y = y + 60 + max(0.0, 4.6 - t) * 120
            pygame.draw.ellipse(surf, (60, 120, 230), (x - 18, y - 9, 36, 18))
            pygame.draw.ellipse(surf, (130, 190, 255), (x - 8, y - 9, 16, 9))
            if t > 4.6:
                art.bubble(surf, "Good choice.", 290, 74)
        text(surf, "MOMMA ROSE'S AIR HOCKEY", (W // 2, 8), 18, (120, 200, 255), center=True)
        if int(self.time * 2) % 2:
            text(surf, "Big button: skip", (W - 60, 228), 12, c.WHITE, center=True)


def make(**kw):
    return AirHockey(**kw)
