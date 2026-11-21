"""Black Warrior bosses. Each has its own pattern and its own moment of weakness.

A boss works in the arena's screen coordinates (the camera holds still). The
game calls update() every frame and take() when Quick lands a hit; take()
returns False when the hit can't land (out of reach, shielded). Mini versions
return for one quick rematch each in the City Hall hallway.
"""
import math

import pygame

from . import bw_art as A
from . import bw_cast as C

W = A.W
TOP, BOTTOM = A.FLOOR_TOP + 6, A.FLOOR_BOTTOM - 2


class Boss:
    name = "BOSS"
    hp_full = 260
    mini_hp = 70

    def __init__(self, mini=False):
        self.mini = mini
        self.x, self.y, self.z = 300.0, 196.0, 0.0
        self.hp = self.max = self.mini_hp if mini else self.hp_full
        self.state, self.st = "walk", 0.0
        self.flash = 0.0
        self.summons = 0
        self.gag = False          # set by the katana cutscene
        self.cycle = 0
        self.face = -1
        self.armor = 1.0

    def hittable(self, from_air):
        return True

    def take(self, dmg, from_air):
        if self.hp <= 0 or not self.hittable(from_air):
            return False
        self.hp = max(0, self.hp - int(round(dmg * self.armor)))
        self.flash = 0.08
        return True

    def body(self):
        return self.x, self.y - self.z - 40

    def go(self, state):
        self.state, self.st = state, 0.0

    def summon_at(self, g, kind, fracs=(0.66, 0.33), count=2):
        if self.mini:
            return
        for i, f in enumerate(fracs):
            if self.hp < self.max * f and self.summons <= i:
                self.summons += 1
                for k in range(count):
                    side = -1 if k % 2 == 0 else 1
                    g.spawn(kind, W / 2 + side * (W / 2 + 15), TOP + 14 + k * 26)
                return True
        return False

    def toward(self, target, speed, dt):
        return max(-speed * dt, min(speed * dt, target))

    def update(self, g, dt):
        self.st += dt
        self.flash = max(0.0, self.flash - dt)
        self.think(g, dt)
        self.x = max(30.0, min(W - 30.0, self.x))
        self.y = max(TOP, min(BOTTOM, self.y))

    def think(self, g, dt):
        pass

    def draw(self, surf, g):
        pass

    def shadow(self, surf, w=56):
        A.shadow(surf, self.x, self.y, w)


class Heir(Boss):
    name = "THE TRILLION HEIR"

    def __init__(self, mini=False):
        super().__init__(mini)
        self.z = 34.0
        self.state = "float"
        self.vx = 0.0
        self.thrown = False

    def hittable(self, from_air):
        return self.z <= 14 or from_air

    def think(self, g, dt):
        p = g.p
        if self.summon_at(g, "butler"):
            g.bubble("Butlers!", self.x, self.y - self.z - 70, 1.4)
        s = self.state
        if s == "float":
            self.z += (34 - self.z) * min(1.0, dt * 3)
            want = max(50, min(W - 50, p.x + (90 if self.x >= p.x else -90)))
            self.x += self.toward(want - self.x, 60, dt)
            self.y += self.toward(p.y - self.y, 40, dt)
            if self.st > (2.2 if not self.mini else 1.6):
                self.go("coins" if self.cycle % 2 == 0 else "ram")
                self.cycle += 1
        elif s == "coins":
            if self.st > 0.5 and not self.thrown:
                self.thrown = True
                d = 1 if p.x > self.x else -1
                for k in range(5):
                    g.projs.append({"kind": "coin", "x": self.x + d * 20, "y": p.y + (k - 2) * 9, "z": self.z + 30,
                                    "vx": d * (110 + k * 12), "vz": 60.0, "g": 260.0, "dmg": 6, "owner": "enemy"})
                g.sfx("coin")
            if self.st > 1.0:
                self.thrown = False
                self.go("tired")
        elif s == "tired":
            self.z += (6 - self.z) * min(1.0, dt * 5)
            if self.st > 2.4:
                self.go("float")
        elif s == "ram":
            if self.st < 0.6:
                self.z += (44 - self.z) * min(1.0, dt * 4)
                self.vx = 230.0 if p.x > self.x else -230.0
                self.y += self.toward(p.y - self.y, 50, dt)
            else:
                self.z += (10 - self.z) * min(1.0, dt * 8)
                self.x += self.vx * dt
                if abs(self.x - p.x) < 26 and abs(self.y - p.y) < 12 and p.z < 30:
                    g.hurt_player(14, self.x, knock=True)
                if self.x <= 31 or self.x >= W - 31 or self.st > 2.4:
                    self.go("tired")

    def draw(self, surf, g):
        img = A.trillion_heir(g.time, self.state in ("tired", "beaten"), self.gag)
        if self.flash > 0:
            img = A.white(img)
        self.shadow(surf)
        surf.blit(img, (int(self.x - img.get_width() / 2), int(self.y - self.z - img.get_height() + 10)))


class Pig(Boss):
    name = "THE CAPITALIST PIG"
    hp_full = 300

    def __init__(self, mini=False):
        super().__init__(mini)
        self.wave = None
        self.vx = 0.0

    def hittable(self, from_air):
        return self.state != "charge"

    def think(self, g, dt):
        p = g.p
        if self.summon_at(g, "authdrone"):
            g.bubble("Prior authorization required!", self.x, self.y - 100, 1.6)
        self.face = 1 if p.x > self.x else -1
        s = self.state
        if self.wave is not None:
            self.wave[2] += dt * 170
            wx, wy, r = self.wave
            d = math.hypot(p.x - wx, (p.y - wy) * 2.2)
            if abs(d - r) < 9 and p.z < 4 and not self.wave[3]:
                self.wave[3] = True
                g.hurt_player(10, wx, knock=True)
            if r > 170:
                self.wave = None
        if s == "walk":
            dx = p.x - self.x
            self.x += self.toward(dx - self.face * 30, 42, dt)
            self.y += self.toward(p.y - self.y, 34, dt)
            if abs(dx) < 46 and abs(p.y - self.y) < 10 and self.st > 0.8:
                self.go("swing")
            elif self.st > 2.6:
                self.go("charge_wind" if self.cycle % 2 == 0 else "stamp_wind")
                self.cycle += 1
        elif s == "swing":
            if 0.4 <= self.st and self.st - dt < 0.4:
                if abs(p.y - self.y) < 12 and 0 < (p.x - self.x) * self.face < 52 and p.z < 20:
                    g.hurt_player(10, self.x)
                g.sfx("punch")
            if self.st > 0.8:
                self.go("walk")
        elif s == "charge_wind":
            self.y += self.toward(p.y - self.y, 60, dt)
            self.vx = 260.0 * self.face
            if self.st > 0.7:
                self.go("charge")
                g.sfx("dash")
        elif s == "charge":
            self.x += self.vx * dt
            if abs(self.x - p.x) < 28 and abs(self.y - p.y) < 12 and p.z < 24:
                g.hurt_player(14, self.x, knock=True)
            if self.x <= 31 or self.x >= W - 31:
                g.sfx("thud")
                self.go("stunned")
        elif s == "stunned":       # crashed into the wall: wide open
            if self.st > 2.2:
                self.go("walk")
        elif s == "stamp_wind":
            if self.st > 0.6:
                self.go("stamp")
        elif s == "stamp":
            if self.st < dt * 1.5:
                self.wave = [self.x + self.face * 30, self.y, 10.0, False]
                g.sfx("boom")
            if self.st > 1.0:
                self.go("walk")

    def draw(self, surf, g):
        st = {"charge_wind": "walk", "stamp_wind": "stamp"}.get(self.state, self.state)
        img = C.capitalist_pig(g.time, st, self.flash > 0, self.gag)
        if self.face < 0:
            img = pygame.transform.flip(img, True, False)
        self.shadow(surf, 60)
        surf.blit(img, (int(self.x - img.get_width() / 2), int(self.y - img.get_height() + 6)))
        if self.state == "stunned":
            A.stars(surf, self.x, self.y - 96, g.time)
        if self.wave is not None:
            wx, wy, r, _ = self.wave
            pygame.draw.ellipse(surf, (255, 220, 120), (int(wx - r), int(wy - r / 2.2), int(r * 2), int(r / 1.1)), 2)


class Poverty(Boss):
    name = "MISTER POVERTY"
    hp_full = 320

    def think(self, g, dt):
        p = g.p
        if self.summon_at(g, "picker"):
            g.bubble("Work harder. For less.", self.x, self.y - 110, 1.6)
        self.face = 1 if p.x > self.x else -1
        s = self.state
        if s == "walk":
            self.x += self.toward(p.x - self.face * 50 - self.x, 26, dt)
            self.y += self.toward(p.y - self.y, 22, dt)
            if abs(p.y - self.y) < 10 and abs(p.x - self.x) < 90 and self.st > 1.2:
                self.go("whip_wind")
            elif self.st > 3.0:
                self.go("wind")
        elif s == "whip_wind":
            if self.st > 0.85:
                self.go("whip")
                g.sfx("whoosh")
        elif s == "whip":
            if self.st < 0.3 and abs(p.y - self.y) < 11 and 0 < (p.x - self.x) * self.face < 92 and p.z < 20:
                g.hurt_player(8, self.x)
            if self.st > 0.6:
                self.go("walk")
        elif s == "wind":          # a cold wind that shoves Quick away
            if p.state not in ("dodge", "down", "fly"):
                p.x += (1 if p.x > self.x else -1) * 70 * dt
            if self.st > 2.4:
                self.go("tired")
        elif s == "tired":
            if self.st > 1.6:
                self.go("walk")

    def draw(self, surf, g):
        img = C.mister_poverty(g.time, self.state, self.flash > 0, 1.0 if self.gag else 0.0)
        if self.face < 0:
            img = pygame.transform.flip(img, True, False)
        self.shadow(surf, 44)
        surf.blit(img, (int(self.x - img.get_width() / 2), int(self.y - img.get_height() + 4)))
        if self.state in ("whip", "whip_wind"):
            reach = 92 if self.state == "whip" else 30
            C.bills_chain(surf, self.x + self.face * 20, self.y - 50, self.x + self.face * reach, self.y - 24, g.time)
        if self.state == "wind":
            for k in range(8):
                y = self.y - 70 + k * 9
                x = self.x + self.face * ((g.time * 200 + k * 37) % 160)
                pygame.draw.line(surf, (200, 220, 255), (int(x), int(y)), (int(x + self.face * 16), int(y)))


class Eviction(Boss):
    name = "MADAME EVICTION"
    hp_full = 300

    def __init__(self, mini=False):
        super().__init__(mini)
        self.state = "ground" if mini else "cab"
        self.cab_x = 200.0
        self.ball = None           # [x, y, vx, phase]
        self.sweeps = 0
        self.thrown = False

    def hittable(self, from_air):
        return self.state in ("ground", "kick")

    def think(self, g, dt):
        p = g.p
        if self.summon_at(g, "repo"):
            g.bubble("Repo men! Clear them out!", self.cab_x, 50, 1.6)
        s = self.state
        if s == "cab":
            self.z = 80.0
            self.x = self.cab_x
            if self.ball is None and self.st > 0.6 and self.sweeps < 2:
                side = -1 if self.rng_side(g) else 1
                self.ball = [W / 2 - side * (W / 2 + 30), p.y, side * 300.0, 0.0]
            if self.ball is not None:
                b = self.ball
                b[3] += dt
                if b[3] > 1.3:                    # the lane is telegraphed first, then the ball sweeps
                    b[0] += b[2] * dt
                    if abs(b[0] - p.x) < 16 and abs(b[1] - p.y) < 10 and p.z < 24:
                        g.hurt_player(12, b[0] - b[2], knock=True)
                    if b[0] < -40 or b[0] > W + 40:
                        self.ball = None
                        self.sweeps += 1
                        self.st = -0.6
                        g.sfx("whoosh")
            if self.sweeps >= 2 and self.ball is None:
                if not self.thrown:
                    self.thrown = True
                    for k in range(3):
                        g.projs.append({"kind": "notice", "x": self.cab_x, "y": p.y + (k - 1) * 12, "z": 70.0,
                                        "vx": (p.x - self.cab_x) / 0.8, "vz": -60.0, "g": 40.0, "dmg": 5, "owner": "enemy"})
                    g.sfx("throw")
                elif self.st > 1.2:
                    self.sweeps, self.thrown = 0, False
                    self.go("climb")
        elif s == "climb":
            self.z = max(0.0, self.z - dt * 120)
            if self.z <= 0:
                self.go("ground")
        elif s == "ground":       # down off the crane: now she can be hit
            self.face = 1 if p.x > self.x else -1
            self.x += self.toward(p.x - self.face * 24 - self.x, 70, dt)
            self.y += self.toward(p.y - self.y, 50, dt)
            if abs(p.x - self.x) < 32 and abs(p.y - self.y) < 9 and self.st > 0.6:
                self.go("kick")
            if self.st > 6.5 and not self.mini:
                self.go("up")
        elif s == "kick":
            if 0.25 <= self.st and self.st - dt < 0.25:
                if abs(p.y - self.y) < 10 and 0 < (p.x - self.x) * self.face < 36 and p.z < 20:
                    g.hurt_player(10, self.x)
            if self.st > 0.6:
                self.go("ground")
        elif s == "up":
            self.x += self.toward(self.cab_x - self.x, 120, dt)
            self.z = min(80.0, self.z + dt * 120)
            if self.z >= 80:
                self.go("cab")

    def rng_side(self, g):
        return g.rng.random() < 0.5

    def draw(self, surf, g):
        if not self.mini and self.state != "beaten":
            C.crane(surf, 70, 30, self.cab_x)
        if self.ball is not None:
            b = self.ball
            if b[3] <= 1.3:
                lane = pygame.Surface((W, 10), pygame.SRCALPHA)
                lane.fill((255, 60, 60, 60 if int(g.time * 10) % 2 else 20))
                surf.blit(lane, (0, int(b[1] - 5)))
            else:
                A.shadow(surf, b[0], b[1], 30)
                C.wrecking_ball(surf, b[0], b[1] - 22, (self.cab_x, 40))
        img = C.madame_eviction(g.time, self.state, self.flash > 0, self.gag)
        if self.face < 0:
            img = pygame.transform.flip(img, True, False)
        if self.state == "cab":
            surf.blit(pygame.transform.scale(img, (22, 35)), (int(self.cab_x - 11), 30))
        else:
            self.shadow(surf, 30)
            surf.blit(img, (int(self.x - img.get_width() / 2), int(self.y - self.z - img.get_height() + 4)))


class Smog(Boss):
    name = "BARON SMOG"
    hp_full = 340

    def think(self, g, dt):
        p = g.p
        self.armor = 1.0 if self.state == "vent" else 0.5
        if self.summon_at(g, "smog", count=3):
            g.bubble("Breathe it in!", self.x, self.y - 110, 1.4)
        self.face = 1 if p.x > self.x else -1
        s = self.state
        if s == "walk":
            self.x += self.toward(p.x - self.face * 70 - self.x, 34, dt)
            self.y += self.toward(p.y - self.y, 30, dt)
            if self.st > 2.4:
                self.go("vacuum" if self.cycle % 2 == 0 else "puffs")
                self.cycle += 1
        elif s == "vacuum":       # sucks Quick in; the vents open afterwards
            if p.state not in ("dodge", "down", "fly", "jump"):
                p.x += (1 if self.x > p.x else -1) * 64 * dt
                p.y += max(-30 * dt, min(30 * dt, self.y - p.y))
            if abs(p.x - self.x) < 40 and abs(p.y - self.y) < 12:
                g.hurt_player(12, self.x, knock=True)
                self.go("vent")
            elif self.st > 2.4:
                self.go("vent")
        elif s == "vent":
            if self.st > 2.6:
                self.go("walk")
        elif s == "puffs":
            if self.st < dt * 1.5 and not self.mini:
                for k in range(2):
                    g.spawn("smog", self.x - self.face * 30, self.y + (k - 0.5) * 20)
                g.sfx("boom")
            if self.st > 1.0:
                self.go("walk")

    def draw(self, surf, g):
        img = C.baron_smog(g.time, self.state, self.flash > 0, self.gag)
        if self.face < 0:
            img = pygame.transform.flip(img, True, False)
        self.shadow(surf, 70)
        surf.blit(img, (int(self.x - img.get_width() / 2), int(self.y - img.get_height() + 4)))
        if self.state == "vacuum":
            for k in range(6):
                u = (g.time * 2 + k / 6) % 1.0
                x = self.x + self.face * (40 + 120 * (1 - u))
                pygame.draw.circle(surf, (150, 140, 130), (int(x), int(self.y - 40 + math.sin(k) * 10)), 2)


class BigLie(Boss):
    name = "THE BIG LIE"
    hp_full = 330

    def __init__(self, mini=False):
        super().__init__(mini)
        self.z = 8.0
        self.wave = None
        self.state = "float"

    def hittable(self, from_air):
        return self.state != "shield"

    def think(self, g, dt):
        p = g.p
        phase2 = self.hp < self.max * 0.5
        drones = sum(1 for e in g.enemies if e.alive and e.kind == "fakenews")
        if drones < (2 if phase2 else 1) and self.st > 1.0 and self.state == "float" and g.rng.random() < dt * 0.3:
            g.spawn("fakenews", -15 if g.rng.random() < 0.5 else W + 15, TOP + 20)
        if self.wave is not None:
            self.wave[2] += dt * 150
            wx, wy, r, hit = self.wave
            if abs(math.hypot(p.x - wx, (p.y - wy) * 2.2) - r) < 9 and p.z < 4 and not hit:
                self.wave[3] = True
                g.hurt_player(9, wx, knock=True)
            if r > 220:
                self.wave = None
        s = self.state
        if s == "float":
            self.z = 8 + math.sin(g.time * 2) * 4
            want = max(60, min(W - 60, p.x + (110 if self.x >= p.x else -110)))
            self.x += self.toward(want - self.x, 50, dt)
            self.y += self.toward(p.y - self.y, 30, dt)
            if self.st > 2.4:
                self.go(["static", "rings", "shield"][self.cycle % 3] if phase2 else "static")
                self.cycle += 1
        elif s == "static":
            if 0.5 <= self.st and self.st - dt < 0.5:
                d = 1 if p.x > self.x else -1
                g.projs.append({"kind": "static", "x": self.x + d * 20, "y": p.y, "z": 24.0, "vx": d * 120.0,
                                "vz": 0.0, "g": 0.0, "dmg": 5, "owner": "enemy"})
                g.sfx("zap")
            if self.st > 1.0:
                self.go("float")
        elif s == "rings":
            if self.st < dt * 1.5:
                self.wave = [self.x, self.y, 10.0, False]
                g.sfx("horn")
            if self.st > 1.4:
                self.go("float")
        elif s == "shield":
            if self.st > 2.0:
                self.go("float")

    def draw(self, surf, g):
        img = C.big_lie(g.time, self.state, self.flash > 0, self.gag, self.state == "shield")
        self.shadow(surf, 50)
        surf.blit(img, (int(self.x - img.get_width() / 2), int(self.y - self.z - img.get_height() + 6)))
        if self.wave is not None:
            wx, wy, r, _ = self.wave
            pygame.draw.ellipse(surf, (200, 120, 255), (int(wx - r), int(wy - r / 2.2), int(r * 2), int(r / 1.1)), 2)


BOSSES = {"heir": Heir, "pig": Pig, "poverty": Poverty, "eviction": Eviction, "smog": Smog, "biglie": BigLie}


def make(kind, mini=False):
    return BOSSES[kind](mini)
