"""Black Warrior tag team guests. Each one enters in style, fights on their own for 15 seconds,
and has one team attack with Quick (hold the triangle button for a second).

Positions are in world coordinates; draw() takes the camera offset.
"""
import math

import pygame

from . import bw_art as A
from . import bw_cast as C
from .bw_levels import GUESTS

DURATION = 15.0


class Guest:
    kind = "mazee"
    speed = 150
    reach = 18
    cool = 0.6

    def __init__(self, g):
        p = g.p
        self.x, self.y, self.z = g.cam - 30, p.y + 8, 0.0
        self.state, self.st = "enter", 0.0
        self.t = DURATION
        self.face = 1
        self.anim = 0.0
        self.target = None
        self.lines = GUESTS[self.kind]

    # ---- helpers
    def targets(self, g):
        return [e for e in g.enemies if e.alive and e.state not in ("fly", "down", "held")]

    def nearest(self, g):
        ts = self.targets(g)
        return min(ts, key=lambda e: abs(e.x - self.x) + abs(e.y - self.y)) if ts else None

    def heel(self, g, dt):
        p = g.p
        tx, ty = p.x - 36 * p.face, p.y + 6
        self.x += max(-150 * dt, min(150 * dt, tx - self.x))
        self.y += max(-80 * dt, min(80 * dt, ty - self.y))
        self.face = p.face

    def chase(self, e, dt, stand=12):
        dx, dy = e.x - self.x, e.y - self.y
        self.face = 1 if dx > 0 else -1
        if abs(dx) > self.reach or abs(dy) > 5:
            self.x += max(-self.speed * dt, min(self.speed * dt, dx - self.face * stand))
            self.y += max(-100 * dt, min(100 * dt, dy))
            self.anim += dt
            return False
        return True

    # ---- the loop
    def update(self, g, dt):
        self.st += dt
        if self.state == "leave":
            self.x -= 220 * dt
            self.face = -1
            self.anim += dt
            return self.x > g.cam - 80
        if self.state != "team":
            self.t -= dt
            if self.t <= 0:
                self.leave(g)
                return True
        getattr(self, "do_" + self.state)(g, dt)
        return True

    def leave(self, g, silent=False):
        if self.state == "leave":
            return
        self.state, self.st = "leave", 0.0
        if not silent:
            g.bubble(self.lines["bye"], g.p.x, g.p.y - 64, 2.4)
            g.sfx("bark" if self.kind == "mazee" else "select")

    def do_enter(self, g, dt):
        self.x += 260 * dt
        if self.x > g.p.x - 40:
            self.state, self.st = "fight", 0.0

    def do_fight(self, g, dt):
        e = self.nearest(g)
        if e is None:
            self.heel(g, dt)
            return
        if self.chase(e, dt) and self.st > self.cool:
            self.st = 0.0
            self.hit(g, e)

    def hit(self, g, e):
        g.damage_enemy(e, 5, False, self.face, gain=False)

    def team(self, g):
        return False

    def do_team(self, g, dt):
        self.state = "fight"

    def draw(self, surf, g, cam):
        pass


class Mazee(Guest):
    kind = "mazee"
    speed = 170
    cool = 0.5

    def __init__(self, g):
        super().__init__(g)
        self.fling = None
        g.fx.append(["fence", g.cam + 8, g.p.y, 0.5, False])

    def hit(self, g, e):
        e.state, e.st = "bitten", 0.0
        e.hp -= 5
        e.flash = 0.08
        g.score += 50
        g.sfx("bark" if g.rng.random() < 0.3 else "punch")
        if e.hp <= 0:
            g.damage_enemy(e, 0, True, self.face, gain=False)

    def team(self, g):              # Fetch and Fling
        e = self.nearest(g)
        if e is None:
            return False
        self.fling = e
        e.state, e.st = "held", 0.0
        self.state, self.st = "team", 0.0
        g.bubble("Fetch, Mazee!", g.p.x, g.p.y - 64, 1.2)
        g.sfx("bark")
        return True

    def do_team(self, g, dt):
        e, p = self.fling, g.p
        if not e.alive:
            self.state = "fight"
            return
        tx = p.x + p.face * 22
        e.x += (tx - e.x) * min(1.0, dt * 6)
        e.y += (p.y - e.y) * min(1.0, dt * 6)
        d = 1 if tx > e.x else -1
        self.x, self.y, self.face = e.x - 14 * d, e.y + 2, d
        if self.st > 0.6:
            p.state, p.st, p.move = "atk", 0.0, "spin"
            p.hit_ids = {e.id, -1}
            g.launch(e, p.face, 260.0, 20)
            g.fx.append(["spark", e.x, e.y - 30, 0.2, True])
            g.sfx("kick")
            g.score += 1000
            self.state = "fight"
            self.t = min(self.t, 0.8)

    def draw(self, surf, g, cam):
        img = A.mazee(int(self.anim * 10), self.face, self.state in ("fight", "team"))
        A.shadow(surf, self.x - cam, self.y, 40)
        surf.blit(img, (int(self.x - cam - img.get_width() / 2), int(self.y - img.get_height() + 3)))


class FigureGuest(Guest):
    look = "uncle_t"

    def pose(self):
        if self.state in ("enter", "leave") or self.moving:
            return "walk%d" % (int(self.anim * 8) % 4)
        if self.st < 0.25 and self.state == "fight" and self.swung:
            return self.attack_pose
        return "idle0"

    attack_pose = "jab"
    moving = False
    swung = False

    def chase(self, e, dt, stand=14):
        done = super().chase(e, dt, stand)
        self.moving = not done
        return done

    def draw_fig(self, surf, g, cam, look=None, dx=0):
        look = look or self.look
        img = C.guest_fig(look, self.pose(), self.face)
        ax = A.HX + 1 if self.face > 0 else img.get_width() - 2 - A.HX
        A.shadow(surf, self.x + dx - cam, self.y)
        surf.blit(img, (int(self.x + dx - cam - ax), int(self.y - self.z - A.FEET_Y - 1)))
        return img


class UncleT(FigureGuest):
    kind = "uncle_t"
    look = "uncle_t"
    speed = 140
    reach = 20
    cool = 0.35
    attack_pose = "jab"

    def __init__(self, g):
        super().__init__(g)
        self.car_x = g.cam - 90
        self.rally = None
        g.sfx("skid")

    def do_enter(self, g, dt):        # his car screeches in, he hops out over the hood
        self.car_x += 300 * dt
        self.x = self.car_x + 40
        if self.car_x > g.p.x - 150:
            g.bubble("#@%&!... ALICE!", self.x, self.y - 70, 1.2)
            self.state, self.st = "fight", 0.0

    def hit(self, g, e):              # a flurry of angry slaps
        self.swung = True
        g.damage_enemy(e, 4, False, self.face, gain=False)
        g.sfx("punch")

    def team(self, g):                # Road Rage Rally
        self.rally = g.cam - 90.0
        self.state, self.st = "team", 0.0
        g.p.state, g.p.st = "cut", 0.0
        g.sfx("turbo")
        return True

    def do_team(self, g, dt):
        p = g.p
        self.rally += 330 * dt
        p.x = self.rally + 30
        p.masked = True
        for e in g.enemies:
            if e.alive and e.state not in ("fly", "down") and abs(e.y - p.y) < 22 and abs(e.x - (self.rally + 40)) < 30:
                g.launch(e, 1, 200.0, 22)
                g.sfx("crash")
                g.score += 500
        if self.rally > g.cam + A.W + 40:
            self.rally = None
            p.state, p.st = "idle", 0.0
            p.x = g.cam + A.W - 40
            self.state = "fight"
            self.t = min(self.t, 0.8)

    def draw(self, surf, g, cam):
        if self.state == "enter":
            img = C.car(g.time)
            surf.blit(img, (int(self.car_x - cam), int(self.y - 36)))
            return
        if self.state == "team" and self.rally is not None:
            img = C.car(g.time, rider=True)
            surf.blit(img, (int(self.rally - cam), int(g.p.y - 70)))
            return
        self.draw_fig(surf, g, cam)


class Stephen(FigureGuest):
    kind = "stephen"
    look = "stephen"
    speed = 120
    reach = 34
    cool = 0.9
    attack_pose = "swing"

    def __init__(self, g):
        super().__init__(g)
        self.x = g.p.x - 50
        self.z = 140.0
        self.sweep = None
        g.sfx("whoosh")

    def do_enter(self, g, dt):        # swings down on a girder from a crane hook
        self.z = max(0.0, self.z - 220 * dt)
        if self.z <= 0:
            g.sfx("thud")
            for e in g.enemies:
                if e.alive and abs(e.x - self.x) < 50 and abs(e.y - self.y) < 16:
                    g.damage_enemy(e, 8, True, 1 if e.x > self.x else -1, gain=False)
            self.state, self.st = "fight", 0.0

    def hit(self, g, e):              # wide girder swing that knocks people down
        self.swung = True
        for o in g.enemies:
            if o.alive and o.state not in ("fly", "down") and abs(o.y - self.y) < 12 and 0 < (o.x - self.x) * self.face < 44:
                g.damage_enemy(o, 10, True, self.face, gain=False)
        g.sfx("bonk")

    def team(self, g):                # Girder Sweep
        self.sweep = 0.0
        self.state, self.st = "team", 0.0
        g.bubble("Heads down!", self.x, self.y - 70, 1.0)
        return True

    def do_team(self, g, dt):
        self.sweep += dt
        if 0.3 <= self.sweep and self.sweep - dt < 0.3:
            for e in g.enemies:
                if e.alive and e.state not in ("fly", "down"):
                    g.damage_enemy(e, 18, True, 1 if e.x > g.p.x else -1, gain=False)
            g.sfx("crash")
            g.score += 800
        if self.sweep > 0.8:
            p = g.p
            p.state, p.st, p.vz, p.air = "jump", 0.0, 200.0, "elbow"
            self.state = "fight"
            self.t = min(self.t, 0.8)

    def draw(self, surf, g, cam):
        if self.state == "enter":
            pygame.draw.line(surf, (60, 60, 66), (int(self.x - cam), 0), (int(self.x - cam), int(self.y - self.z - 60)), 2)
            surf.blit(C.girder(60), (int(self.x - cam - 30), int(self.y - self.z - 62)))
        img = self.draw_fig(surf, g, cam)
        gx = self.x - cam + self.face * 14
        if self.state == "team" and self.sweep is not None:
            ang = -60 + min(1.0, self.sweep / 0.4) * 150
            gir = C.girder(70, ang % 360)
            surf.blit(gir, (int(gx - gir.get_width() / 2), int(self.y - 40 - gir.get_height() / 2)))
        elif self.state != "enter":
            ang = 40 if self.pose() == "swing" else 300
            gir = C.girder(50, ang if self.face > 0 else (180 - ang) % 360)
            surf.blit(gir, (int(gx - gir.get_width() / 2), int(self.y - self.z - 34 - gir.get_height() / 2)))


class Squad(FigureGuest):
    kind = "squad"
    look = "miles"
    speed = 120
    reach = 120
    cool = 0.55
    attack_pose = "jab"

    def __init__(self, g):
        super().__init__(g)
        self.x = g.p.x - 50
        self.z = 150.0
        self.f_off = -30
        self.turn = 0
        g.sfx("drone")

    def do_enter(self, g, dt):        # rappel down from a helicopter
        self.z = max(0.0, self.z - 160 * dt)
        if self.z <= 0:
            self.state, self.st = "fight", 0.0
            g.bubble("Squad's here!", self.x, self.y - 70, 1.0)

    def chase(self, e, dt, stand=70):
        dy = e.y - self.y
        self.face = 1 if e.x > self.x else -1
        moving = abs(dy) > 5 or abs(e.x - self.x) > 140
        if moving:
            self.y += max(-90 * dt, min(90 * dt, dy))
            if abs(e.x - self.x) > 140:
                self.x += self.face * 110 * dt
            self.anim += dt
        self.moving = moving
        return not moving

    def hit(self, g, e):              # cartoon stun blasters, the two of them taking turns
        self.swung = True
        self.turn += 1
        sx = self.x + (self.f_off if self.turn % 2 else 0)
        g.projs.append({"kind": "stun", "x": sx + self.face * 14, "y": self.y, "z": 28.0, "vx": self.face * 260.0,
                        "vz": 0.0, "g": 0.0, "dmg": 4, "owner": "guest"})
        g.sfx("shot")

    def team(self, g):                # Crossfire
        self.state, self.st = "team", 0.0
        g.bubble("Covering fire!", self.x, self.y - 70, 1.0)
        return True

    def do_team(self, g, dt):
        if self.st < dt * 1.5:
            for e in g.enemies:
                if e.alive and e.state not in ("fly", "down"):
                    e.state, e.st = "dazed", 0.0
            g.sfx("orders")
        if 0.5 <= self.st and self.st - dt < 0.5:
            p = g.p
            for e in g.enemies:
                if e.alive and e.state == "dazed":
                    g.damage_enemy(e, 16, True, 1 if e.x > p.x else -1, gain=False)
                    g.fx.append(["spark", e.x, e.y - 30, 0.15, True])
            p.state, p.st, p.vx = "dodge", 0.0, p.face * 190.0
            g.sfx("kick")
            g.score += 800
        if self.st > 0.9:
            self.state = "fight"
            self.t = min(self.t, 0.8)

    def draw(self, surf, g, cam):
        if self.state == "enter":
            for dx in (0, self.f_off):
                C.rope(surf, self.x + dx - cam, 0, self.y - self.z - 50)
        self.draw_fig(surf, g, cam, "felix", self.f_off)
        self.draw_fig(surf, g, cam, "miles")
        if self.state == "team":
            for k in range(6):
                y = self.y - 30 + (k % 3) * 6
                x = (g.time * 600 + k * 70) % A.W
                surf.fill((255, 240, 150), (int(x), int(y), 6, 2))


class Pops(FigureGuest):
    kind = "pops"
    look = "pops"
    speed = 120
    reach = 22
    cool = 0.6
    attack_pose = "swing"

    def __init__(self, g):
        super().__init__(g)
        self.door_x = g.p.x - 70
        self.x = self.door_x
        self.cloud = None
        self.cyclone = None
        g.sfx("thud")

    def do_enter(self, g, dt):        # kicks a door off its hinges in a cloud of bug spray
        if self.st > 0.5:
            self.state, self.st = "fight", 0.0
            self.cloud = [self.x, self.y, 1.4]
            g.sfx("spray")

    def hit(self, g, e):              # swatter zaps leave enemies buzzing
        self.swung = True
        e.state, e.st = "dazed", 0.6
        g.damage_enemy(e, 5, False, self.face, gain=False)
        if e.state != "fly":
            e.state = "dazed"
        g.sfx("zap")
        if g.rng.random() < 0.3:
            self.cloud = [e.x, e.y, 1.2]
            g.sfx("spray")

    def update(self, g, dt):
        if self.cloud is not None:
            self.cloud[2] -= dt
            for e in g.enemies:
                if e.alive and e.state not in ("fly", "down") and abs(e.x - self.cloud[0]) < 30 and abs(e.y - self.cloud[1]) < 12:
                    e.hp -= 6 * dt
                    if e.hp <= 0:
                        g.damage_enemy(e, 0, True, 1, gain=False)
            if self.cloud[2] <= 0:
                self.cloud = None
        return super().update(g, dt)

    def team(self, g):                # Bug Out: Quick spins the spray into a cyclone
        self.state, self.st = "team", 0.0
        self.cloud = [g.p.x, g.p.y, 1.6]
        g.bubble("Spin it, son!", self.x, self.y - 70, 1.2)
        g.sfx("spray")
        return True

    def do_team(self, g, dt):
        p = g.p
        if 0.4 <= self.st and self.st - dt < 0.4:
            p.state, p.st = "special", 0.0
            for e in g.enemies:
                if e.alive and e.state not in ("fly", "down") and abs(e.x - p.x) < 140:
                    g.launch(e, 1 if e.x > p.x else -1, 60.0, 20)
                    e.vz = 260.0
            g.sfx("whoosh")
            g.score += 800
        if self.st > 1.2:
            self.state = "fight"
            self.t = min(self.t, 0.8)

    def draw(self, surf, g, cam):
        if self.state == "enter" or (self.state == "fight" and self.st < 1.0 and self.t > DURATION - 2):
            surf.blit(C.door(min(1.0, self.st * 3) if self.state == "enter" else 1.0),
                      (int(self.door_x - cam - 13), int(self.y - 56)))
        if self.cloud is not None:
            C.spray_cloud(surf, self.cloud[0] - cam, self.cloud[1] - 20, 50, g.time)
        self.draw_fig(surf, g, cam)
        sw = C.swatter(self.pose() == "swing")
        sw = pygame.transform.flip(sw, True, False) if self.face < 0 else sw
        surf.blit(sw, (int(self.x - cam + self.face * 12 - 8), int(self.y - 46)))
        if self.state == "team" and self.st > 0.4:
            for k in range(10):
                a = g.time * 12 + k
                r = 20 + k * 4
                surf.fill((200, 240, 200), (int(g.p.x - cam + math.cos(a) * r), int(g.p.y - 30 - k * 5), 3, 2))


KINDS = {"mazee": Mazee, "uncle_t": UncleT, "stephen": Stephen, "squad": Squad, "pops": Pops}


def summon(kind, g):
    return KINDS[kind](g)
