"""The Big Move: Whitney and Lucas carry their things from the pickup, across the
freeway, into their new apartment.

    D-pad        walk
    Big button   pick up from the truck bed (or pick a dropped item back up)

Carry each item through the apartment door to score. Bigger items are worth more
but make you slower and wider. Cars, trucks and bikes cost a life and send the
item back to the truck. Cats trip you, so you drop what you are carrying.
Three lives. Five loads. A second controller brings in the other mover; two
people side by side carry the bed and the sofa faster.

Inspired by the classic road-crossing arcade games; all characters, art, sounds
and music here are original to this project.
"""
import math

import pygame

from . import common as c
from . import move_art as art
from .common import H, W, Game, text

DOOR_X, DOOR_Y = 200, 42
TRUCK_X = 118
TRUCK = pygame.Rect(TRUCK_X - 6, 200, 78, 40)   # where you can reach the truck bed
BIKE_LANE = (54, 16)
ROADS = ((70, 1, 55), (96, -1, 70), (148, 1, 62), (174, -1, 80))   # y, direction, speed
LANE_H = 26
CAT_ROWS = (47, 137)
ITEMS = {  # points, speed factor, half width while carried
    "box": (100, 1.0, 4), "lamp": (150, 1.0, 4), "tv": (200, 0.9, 6),
    "table": (300, 0.8, 8), "bed": (400, 0.68, 11), "sofa": (500, 0.6, 12),
}
LOADS = [
    dict(name="Moving Day", items=["box", "lamp", "table"], speed=1.0, busy=1.0, trucks=0.0, bikes=1, cats=1),
    dict(name="Rush Hour", items=["box", "tv", "table", "bed"], speed=1.12, busy=1.25, trucks=0.3, bikes=1, cats=1),
    dict(name="Bike Lane Blues", items=["box", "lamp", "tv", "table", "bed"], speed=1.22, busy=1.3, trucks=0.3, bikes=2, cats=2),
    dict(name="Cat Parade", items=["box", "lamp", "tv", "table", "bed"], speed=1.34, busy=1.4, trucks=0.35, bikes=2, cats=4),
    dict(name="The Sofa", items=["box", "lamp", "tv", "table", "bed", "sofa"], speed=1.45, busy=1.5, trucks=0.4, bikes=2,
         cats=3, night=True),
]
CAR_COLORS = ((220, 60, 60), (70, 130, 230), (250, 210, 60), (120, 200, 120), (200, 90, 200), (240, 150, 40))
WALK = 78.0
PENO = "Is that Peno!?!!!"
# Black Warrior and Momma Rose wait in the pickup, and they have places to be.
HECKLES = (
    ("Black Warrior", "Hurry up, I gotta go to a community meeting!"),
    ("Momma Rose", "Yeah, I wanna go play mahjong!"),
    ("Black Warrior", "The city is not going to save itself!"),
    ("Momma Rose", "My mahjong tiles are getting cold!"),
    ("Black Warrior", "Lift with your legs!"),
    ("Momma Rose", "Careful with that lamp, it was my mother's!"),
    ("Black Warrior", "I could carry that with one hand. I won't. But I could."),
    ("Momma Rose", "You two are doing great. Faster, but great."),
    ("Black Warrior", "Look both ways! Then look again!"),
    ("Momma Rose", "Did somebody feed Peno?"),
)


class BigMove(Game):
    name = "big_move"
    title = "The Big Move"
    music = "big_move"
    title_color = (250, 220, 90)
    help_lines = ("D-pad: walk   Big button: pick up", "Carry it all across to the new place!", "Watch out for cats!")
    levels = tuple(ld["name"] for ld in LOADS)
    modes = ("Whitney", "Lucas")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.people = {k: {(f, d, cr): art.person(k, f, d, cr) for f in (0, 1) for d in ("down", "up", "left", "right")
                           for cr in (False, True)} for k in ("whitney", "lucas")}
        self.items_art = {k: art.item(k) for k in ITEMS}
        self.cars = {}
        self.cat_art = {(f, d): art.cat(f, d) for f in (0, 1) for d in (1, -1)}
        self.pickup = art.vehicle("pickup")
        self.intro_seen = False
        self.bg = None
        self.reset()

    # ------------------------------------------------------------ setup
    def reset(self):
        self.score = 0
        self.win = False
        self.lives = 3
        self.load_i = min(self.level_choice, len(LOADS) - 1)
        first = ("whitney", "lucas")[self.mode]
        self.players = [self.new_player(first, 0)]
        self.start_load()
        if not self.intro_seen:
            self.phase, self.pt = "intro", 0.0

    def new_player(self, who, slot):
        return {"who": who, "slot": slot, "x": 214.0 + 30 * slot, "y": 224.0, "dir": "up", "anim": 0.0,
                "carry": None, "stun": 0.0, "inv": 1.5, "say": None, "say_t": 0.0}

    def start_load(self):
        ld = self.load = LOADS[self.load_i]
        self.reach_level(self.load_i)
        self.truck_items = list(ld["items"])
        self.delivered = []
        self.dropped = []
        self.vehicles = []
        self.cats = []
        self.lane_t = {}
        self.cat_t = 1.0
        self.heckle, self.heckle_t, self.heckle_i = None, 5.0, 0
        self.load_time = 0.0
        self.carry_time = 0.0
        self.phase, self.pt = "play", 0.0
        self.banner = ("LOAD %d: %s" % (self.load_i + 1, ld["name"]), 2.5)
        self.bg = None
        for p in self.players:
            p.update(x=214.0 + 30 * p["slot"], y=224.0, carry=None, stun=0.0, inv=1.5, dir="up")
        for _ in range(240):                     # traffic is already flowing when you arrive
            self.update_traffic(1 / 20)

    def car_img(self, kind, col, face):
        key = (kind, col, face)
        if key not in self.cars:
            self.cars[key] = art.vehicle(kind, col, face)
        return self.cars[key]

    # ------------------------------------------------------------ update
    def update(self, dt, inp):
        self.pt += dt
        if self.phase == "intro":
            if self.pt > 11.5 or (self.pt > 0.4 and ("a" in inp.pressed or "b" in inp.pressed)):
                self.intro_seen = True
                self.phase, self.pt = "play", 0.0
            return
        if self.phase == "clear":
            if self.pt > 3.0:
                if self.load_i + 1 < len(LOADS):
                    self.load_i += 1
                    self.start_load()
                else:
                    self.win = True
                    self.game_over()
            return
        self.load_time += dt
        self.heckle_t -= dt                           # the two in the truck keep things moving
        if self.heckle_t <= 0:
            if self.heckle is None:
                self.heckle = HECKLES[self.heckle_i % len(HECKLES)]
                self.heckle_i += 1
                self.heckle_t = 3.2
            else:
                self.heckle, self.heckle_t = None, self.rng.uniform(6.0, 10.0)
        if self.banner:
            self.banner = (self.banner[0], self.banner[1] - dt) if self.banner[1] > dt else None
        p2 = getattr(inp, "p2", None)
        if p2 is not None and len(self.players) == 1 and ("a" in p2.pressed or "start" in p2.pressed):
            other = "lucas" if self.players[0]["who"] == "whitney" else "whitney"
            self.players.append(self.new_player(other, 1))
            self.sfx("select")
        self.update_traffic(dt)
        self.update_cats(dt)
        for p in self.players:
            src = inp if p["slot"] == 0 else p2
            if src is not None:
                self.update_player(p, dt, src)
            if self.state != "play" or self.phase != "play":
                return

    def update_traffic(self, dt):
        ld = self.load
        lanes = [("bike", BIKE_LANE[0], 1, 95)]
        if ld["bikes"] > 1:
            lanes.append(("bike2", BIKE_LANE[0], -1, 105))
        lanes += [("road%d" % i, y, d, s) for i, (y, d, s) in enumerate(ROADS)]
        for key, y, d, speed in lanes:
            t = self.lane_t.get(key, self.rng.uniform(0.0, 1.5)) - dt
            if t <= 0:
                bike = key.startswith("bike")
                kind = "bike" if bike else ("truck" if self.rng.random() < ld["trucks"] else "car")
                img = self.car_img(kind, self.rng.choice(CAR_COLORS), d)
                w = img.get_width()
                v = speed * ld["speed"] * self.rng.uniform(0.95, 1.05)
                self.vehicles.append({"kind": kind, "lane": key, "x": float(-w - 4 if d > 0 else W + 4), "y": y, "w": w,
                                      "h": BIKE_LANE[1] if bike else LANE_H, "dir": d, "v": v, "img": img, "rang": False})
                gap = self.rng.uniform(2.6, 5.0) if bike else self.rng.uniform(1.7, 3.4)
                t = gap / ld["busy"] + w / v
            self.lane_t[key] = t
        for v in self.vehicles:                   # nobody rear-ends the car in front
            ahead = [o for o in self.vehicles if o["lane"] == v["lane"] and o is not v and (o["x"] - v["x"]) * v["dir"] > 0]
            speed = v["v"]
            if ahead:
                o = min(ahead, key=lambda o: abs(o["x"] - v["x"]))
                gap = (o["x"] - v["x"] - v["w"]) if v["dir"] > 0 else (v["x"] - o["x"] - o["w"])
                if gap < 12:
                    speed = min(speed, o["v"])
            v["x"] += v["dir"] * speed * dt
            if v["kind"] == "bike" and not v["rang"] and self.players:
                if any(abs(p["y"] - (v["y"] + 12)) < 26 and 0 < (p["x"] - v["x"]) * v["dir"] < 110 for p in self.players):
                    v["rang"] = True
                    self.sfx("ring")
        self.vehicles = [v for v in self.vehicles if -90 < v["x"] < W + 90]

    def update_cats(self, dt):
        self.cat_t -= dt
        if self.cat_t <= 0 and len(self.cats) < self.load["cats"]:
            d = self.rng.choice((1, -1))
            self.cats.append({"x": -12.0 if d > 0 else W + 12.0, "y": self.rng.choice(CAT_ROWS) + self.rng.uniform(-3, 3),
                              "dir": d, "v": self.rng.uniform(26, 40), "anim": 0.0, "dart": 0.0, "mood": self.rng.uniform(1, 3),
                              "said": 0.0})
            self.cat_t = self.rng.uniform(2.0, 5.0)
        for ct in self.cats:
            ct["anim"] += dt * 8
            ct["said"] = max(0.0, ct["said"] - dt)
            ct["mood"] -= dt
            ct["dart"] = max(0.0, ct["dart"] - dt)
            if ct["mood"] <= 0:                    # cats do what they like
                ct["mood"] = self.rng.uniform(1.0, 3.0)
                r = self.rng.random()
                if r < 0.3 and 30 < ct["x"] < W - 30:
                    ct["dir"] = -ct["dir"]
                elif r < 0.7:
                    ct["dart"] = 0.5
            ct["x"] += ct["dir"] * (95 if ct["dart"] > 0 else ct["v"]) * dt
            for p in self.players:                 # "Is that Peno!?!!!"
                if ct["said"] <= 0 and math.hypot(p["x"] - ct["x"], p["y"] - ct["y"]) < 64:
                    ct["said"] = 9.0
                    p["say"], p["say_t"] = PENO, 1.8
                    self.sfx("meow")
        self.cats = [ct for ct in self.cats if -30 < ct["x"] < W + 30]

    def partner_helping(self, p):
        return any(o is not p and o["carry"] is None and o["stun"] <= 0 and
                   math.hypot(o["x"] - p["x"], o["y"] - p["y"]) < 24 for o in self.players)

    def update_player(self, p, dt, inp):
        p["inv"] = max(0.0, p["inv"] - dt)
        p["say_t"] = max(0.0, p["say_t"] - dt)
        if p["stun"] > 0:
            p["stun"] -= dt
            return
        dx = ("right" in inp.held) - ("left" in inp.held)
        dy = ("down" in inp.held) - ("up" in inp.held)
        speed = WALK
        if p["carry"]:
            f = ITEMS[p["carry"]][1]
            if f < 0.75 and self.partner_helping(p):
                f = 0.92                               # two people make light work of the big stuff
            speed *= f
        if dx or dy:
            n = math.hypot(dx, dy)
            p["x"] = max(8.0, min(W - 8.0, p["x"] + dx / n * speed * dt))
            p["y"] = max(DOOR_Y - 2.0, min(H - 6.0, p["y"] + dy / n * speed * dt))
            p["dir"] = ("down" if dy > 0 else "up") if dy else ("right" if dx > 0 else "left")
            p["anim"] += dt * 9
        if "a" in inp.pressed and not p["carry"]:
            near = [d for d in self.dropped if math.hypot(d["x"] - p["x"], d["y"] - p["y"]) < 18]
            if near:
                d = near[0]
                self.dropped.remove(d)
                p["carry"] = d["kind"]
                self.sfx("grab")
            elif TRUCK.collidepoint(p["x"], p["y"]) and self.truck_items:
                p["carry"] = self.truck_items.pop(0)
                self.carry_time = self.load_time
                self.sfx("grab")
        # through the door
        if p["carry"] and p["y"] <= DOOR_Y + 2 and abs(p["x"] - DOOR_X) < 16:
            kind = p["carry"]
            p["carry"] = None
            bonus = max(0, 150 - int(self.load_time - self.carry_time) * 5)
            self.score += ITEMS[kind][0] + bonus
            self.delivered.append(kind)
            self.bg = None
            self.sfx("coin")
            p["y"] = DOOR_Y + 6.0
            p["dir"] = "down"
            if not self.truck_items and not self.dropped and not any(q["carry"] for q in self.players):
                self.score += 250 + 100 * self.lives
                self.phase, self.pt = "clear", 0.0
                self.sfx("clear")
            return
        if p["inv"] > 0:
            return
        hw = ITEMS[p["carry"]][2] if p["carry"] else 4
        feet = pygame.Rect(int(p["x"]) - hw, int(p["y"]) - 5, hw * 2, 5)
        for v in self.vehicles:
            if feet.colliderect(pygame.Rect(int(v["x"]) + 3, v["y"] + 3, v["w"] - 6, v["h"] - 6)):
                self.run_over(p, v)
                return
        for ct in self.cats:
            if math.hypot(ct["x"] - p["x"], ct["y"] - (p["y"] - 3)) < 10:
                p["stun"], p["inv"] = 0.7, 1.4
                p["say"], p["say_t"] = "Whoa, kitty!", 1.0
                self.sfx("meow")
                if p["carry"]:
                    self.dropped.append({"kind": p["carry"], "x": p["x"], "y": p["y"]})
                    p["carry"] = None
                    self.sfx("thud")
                return

    def run_over(self, p, v):
        self.sfx("horn" if v["kind"] != "bike" else "ring")
        self.sfx("hurt")
        if p["carry"]:
            self.truck_items.insert(0, p["carry"])
            p["carry"] = None
        self.lives -= 1
        p.update(x=214.0 + 30 * p["slot"], y=224.0, dir="up", inv=2.2, stun=0.5, say="Ouch!", say_t=1.0)
        if self.lives <= 0:
            self.game_over()

    # ------------------------------------------------------------ draw
    def background(self):
        if self.bg is not None:
            return self.bg
        s = pygame.Surface((W, H))
        night = self.load.get("night")
        s.fill((70, 70, 78))
        pygame.draw.rect(s, (30, 40, 90) if night else (120, 170, 220), (0, 0, W, 40))
        pygame.draw.rect(s, (190, 120, 90), (90, 0, 220, 36))
        pygame.draw.rect(s, (160, 96, 70), (90, 0, 220, 3))
        slots = [104 + i * 34 for i in range(6) if i != 2] + [104 + 2 * 34]
        for i in range(6):
            wx = 104 + i * 34
            if abs(wx + 8 - DOOR_X) < 14:
                continue
            pygame.draw.rect(s, (255, 236, 150), (wx, 6, 16, 14))
            pygame.draw.rect(s, (120, 76, 40), (wx, 6, 16, 14), 1)
        for i, kind in enumerate(self.delivered[:5]):          # the windows fill up as things arrive
            im = self.items_art[kind]
            k = min(14 / im.get_width(), 11 / im.get_height())
            im = pygame.transform.scale(im, (max(1, int(im.get_width() * k)), max(1, int(im.get_height() * k))))
            s.blit(im, (slots[i] + 8 - im.get_width() // 2, 19 - im.get_height()))
        pygame.draw.rect(s, (90, 60, 40), (DOOR_X - 12, 12, 24, 24))
        pygame.draw.rect(s, (60, 40, 26), (DOOR_X - 10, 14, 20, 22))
        text(s, "NEW HOME", (DOOR_X, 1), 12, c.WHITE, center=True)
        pygame.draw.rect(s, (200, 196, 186), (0, 36, W, 18))
        for x in range(0, W, 40):
            pygame.draw.line(s, (180, 176, 166), (x, 36), (x, 53))
        pygame.draw.rect(s, (90, 150, 110), (0, BIKE_LANE[0], W, BIKE_LANE[1]))
        for x in range(0, W, 24):
            pygame.draw.line(s, (235, 245, 235), (x, 62), (x + 10, 62))
        for y, d, sp in ROADS:
            pygame.draw.rect(s, (60, 60, 68), (0, y, W, LANE_H))
            for x in range(0, W, 30):
                pygame.draw.line(s, (230, 220, 120), (x, y + LANE_H - 1), (x + 14, y + LANE_H - 1))
            for x in range(40, W, 120):                        # arrows show which way the lane runs
                pygame.draw.polygon(s, (86, 86, 96), [(x - 6 * d, y + 9), (x + 6 * d, y + 13), (x - 6 * d, y + 17)])
        pygame.draw.rect(s, (96, 160, 84), (0, 122, W, 26))
        for x in (30, 110, 290, 370):
            pygame.draw.circle(s, (60, 130, 60), (x, 134), 7)
            pygame.draw.circle(s, (80, 160, 76), (x - 2, 132), 4)
        pygame.draw.rect(s, (200, 196, 186), (0, 200, W, 40))
        pygame.draw.rect(s, (170, 166, 156), (0, 200, W, 2))
        self.bg = s
        return s

    def draw_truck(self, surf):
        tx, ty = TRUCK_X, 208
        for i, kind in enumerate(reversed(self.truck_items[:4])):
            im = self.items_art[kind]
            surf.blit(im, (tx + 14 - im.get_width() // 2 + (i % 2) * 6, ty + 10 - im.get_height() - i * 3))
        surf.blit(self.pickup, (tx, ty))

    def draw_player(self, surf, p):
        if p["inv"] > 0 and p["stun"] <= 0 and int(self.time * 14) % 2:
            return
        img = self.people[p["who"]][(int(p["anim"]) % 2, p["dir"], bool(p["carry"]))]
        if p["stun"] > 0:
            img = pygame.transform.rotate(img, 80)
        x, y = int(p["x"]), int(p["y"])
        pygame.draw.ellipse(surf, (40, 40, 48), (x - 7, y - 3, 14, 5))
        surf.blit(img, (x - img.get_width() // 2, y - img.get_height() + 1))
        if p["carry"]:
            im = self.items_art[p["carry"]]
            bob = int(p["anim"]) % 2
            surf.blit(im, (x - im.get_width() // 2, y - 30 - im.get_height() + bob))

    def draw(self, surf):
        if self.phase == "intro":
            self.draw_intro(surf)
            return
        surf.blit(self.background(), (0, 0))
        for d in self.dropped:
            im = self.items_art[d["kind"]]
            surf.blit(im, (int(d["x"]) - im.get_width() // 2, int(d["y"]) - im.get_height()))
            if int(self.time * 4) % 2:
                text(surf, "!", (int(d["x"]), int(d["y"]) - im.get_height() - 12), 16, c.YELLOW, center=True)
        things = [(v["y"] + v["h"], "v", v) for v in self.vehicles]
        things += [(ct["y"] + 2, "c", ct) for ct in self.cats] + [(p["y"], "p", p) for p in self.players]
        things.append((232, "t", None))
        for _, kind, o in sorted(things, key=lambda t: t[0]):
            if kind == "v":
                surf.blit(o["img"], (int(o["x"]), o["y"] + o["h"] - o["img"].get_height() - 1))
            elif kind == "c":
                surf.blit(self.cat_art[(int(o["anim"]) % 2, o["dir"])], (int(o["x"]) - 10, int(o["y"]) - 12))
            elif kind == "p":
                self.draw_player(surf, o)
            else:
                self.draw_truck(surf)
        if self.load.get("night"):
            self.draw_night(surf)
        for p in self.players:
            if p["say_t"] > 0 and p["say"]:
                art.bubble(surf, p["say"], p["x"] + 30, p["y"] - 52)
            elif (not p["carry"] and TRUCK.collidepoint(p["x"], p["y"]) and self.truck_items and int(self.time * 3) % 2):
                text(surf, "Big button: grab!", (int(p["x"]) + 46, int(p["y"]) - 44), 14, c.YELLOW, center=True)
        if self.heckle and self.phase == "play":
            who, line = self.heckle
            art.bubble(surf, line, TRUCK_X + 36, 192)
            text(surf, who, (TRUCK_X + 36, 176), 12, (255, 220, 110), center=True)
        text(surf, "SCORE %d" % int(self.score), (6, 226), 14, c.WHITE)
        left = len(self.truck_items) + len(self.dropped) + sum(1 for p in self.players if p["carry"])
        text(surf, "LOAD %d  %d to go" % (self.load_i + 1, left), (W // 2 + 30, 226), 14, (250, 220, 90), center=True)
        for i in range(self.lives):
            pygame.draw.circle(surf, (230, 70, 90), (W - 12 - i * 13, 232), 4)
            pygame.draw.circle(surf, (255, 170, 180), (W - 13 - i * 13, 231), 1)
        if self.banner:
            text(surf, self.banner[0], (W // 2, 108), 26, c.YELLOW, center=True)
        if self.phase == "clear":
            self.draw_clear(surf)

    def draw_night(self, surf):
        dark = pygame.Surface((W, H), pygame.SRCALPHA)
        dark.fill((8, 12, 48, 120))
        for v in self.vehicles:
            if v["kind"] == "bike":
                continue
            fx = v["x"] + (v["w"] if v["dir"] > 0 else 0)
            cy = v["y"] + v["h"] - 8
            pygame.draw.polygon(dark, (255, 240, 170, 30), [(fx, cy - 2), (fx + 46 * v["dir"], cy - 12), (fx + 46 * v["dir"], cy + 8)])
        for p in self.players:
            pygame.draw.circle(dark, (8, 12, 48, 50), (int(p["x"]), int(p["y"]) - 12), 22)
        surf.blit(dark, (0, 0))
        k = int(self.time * 300)
        for i in range(34):                                   # rain
            x = (i * 53 + k) % (W + 40) - 20
            y = (i * 97 + k * 2) % H
            pygame.draw.line(surf, (150, 170, 220), (x, y), (x - 2, y + 6))

    def draw_clear(self, surf):
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        surf.blit(shade, (0, 0))
        pygame.draw.rect(surf, (236, 214, 180), (70, 60, 260, 120), border_radius=6)
        pygame.draw.rect(surf, (150, 110, 80), (70, 150, 260, 30), border_bottom_left_radius=6, border_bottom_right_radius=6)
        pygame.draw.rect(surf, (140, 200, 240), (270, 72, 40, 36))
        pygame.draw.line(surf, (255, 255, 255), (290, 72), (290, 108))
        x = 84
        for kind in self.delivered:                           # the room, furnished
            im = self.items_art[kind]
            im = pygame.transform.scale(im, (im.get_width() * 3 // 2, im.get_height() * 3 // 2))
            surf.blit(im, (x, 168 - im.get_height()))
            x += im.get_width() + 4
        text(surf, "LOAD %d DONE!" % (self.load_i + 1), (W // 2, 30), 30, c.YELLOW, center=True)
        last = self.load_i + 1 >= len(LOADS)
        text(surf, "Home sweet home!" if last else "Next: %s" % LOADS[self.load_i + 1]["name"], (W // 2, 192), 18, c.WHITE, center=True)

    # ------------------------------------------------------------ opening scene
    def draw_city(self, surf, off):
        surf.fill((130, 180, 230))
        for i in range(9):
            x = int((i * 70 - off * 0.4) % (W + 140)) - 70
            hgt = 60 + (i * 37) % 50
            pygame.draw.rect(surf, (150 + (i * 23) % 60, 130, 150), (x, 150 - hgt, 56, hgt))
            for wy in range(150 - hgt + 8, 142, 14):
                for wx in range(x + 8, x + 50, 14):
                    pygame.draw.rect(surf, (240, 230, 170), (wx, wy, 6, 8))
        pygame.draw.rect(surf, (90, 150, 90), (0, 150, W, 14))
        pygame.draw.rect(surf, (60, 60, 68), (0, 164, W, 76))
        for x in range(-40, W + 40, 40):
            pygame.draw.line(surf, (230, 220, 120), (x - int(off) % 40, 200), (x + 20 - int(off) % 40, 200), 2)

    def draw_loaded_truck(self, surf, x, y, riders, crew=True):
        """The white pickup, double size, with Momma Rose driving and Quick in the back."""
        big = pygame.transform.scale2x(self.pickup)
        if crew:
            try:
                from . import bw_art
                quick = bw_art.hero("idle0", True, 1)
                q = pygame.transform.smoothscale(quick, (quick.get_width() * 2 // 3, quick.get_height() * 2 // 3))
                surf.blit(q, (x + 6, y + 20 - q.get_height() + 6), (0, 0, q.get_width(), q.get_height() - 14))
            except Exception:
                pass
            sofa = self.items_art["sofa"]
            surf.blit(sofa, (x + 22, y + 6))
        surf.blit(big, (x, y))
        if crew:
            head = pygame.transform.scale(art.rose_head(), (19, 17))
            surf.blit(head, (x + 84, y + 6))
        for i, who in enumerate(riders):
            hd = self.people[who][(0, "down", False)].subsurface((2, 0, 14, 13))
            surf.blit(hd, (x + 66 + i * 0, y + 8) if i == 0 else (x + 30, y + 0))

    def draw_intro(self, surf):
        t = self.pt
        if t < 6.6:                                           # the old apartment
            surf.fill((150, 190, 230))
            pygame.draw.rect(surf, (150, 140, 120), (20, 30, 190, 140))
            pygame.draw.rect(surf, (120, 110, 96), (20, 30, 190, 6))
            for wy in (50, 100):
                for wx in (40, 100, 160):
                    pygame.draw.rect(surf, (90, 110, 130), (wx, wy, 26, 30))
                    pygame.draw.line(surf, (60, 70, 80), (wx + 13, wy), (wx + 13, wy + 30))
            pygame.draw.rect(surf, (80, 56, 40), (100, 130, 30, 40))
            text(surf, "OLD PLACE", (115, 16), 14, c.WHITE, center=True)
            pygame.draw.rect(surf, (110, 150, 80), (0, 170, W, 70))
            pygame.draw.rect(surf, (190, 186, 176), (0, 196, W, 16))
            for i, (mx, my) in enumerate(((30, 184), (70, 226), (150, 182), (190, 228), (236, 186), (60, 190), (300, 226), (210, 220))):
                pygame.draw.ellipse(surf, (96, 62, 30), (mx, my, 10, 6))          # dog waste, everywhere
                pygame.draw.ellipse(surf, (120, 80, 40), (mx + 2, my - 3, 6, 5))
                for k in range(2):
                    wob = int(math.sin(self.time * 6 + i + k) * 2)
                    pygame.draw.line(surf, (150, 170, 90), (mx + 3 + k * 4 + wob, my - 6), (mx + 3 + k * 4 - wob, my - 12))
            self.draw_loaded_truck(surf, 262, 168, ())
            run = max(0.0, t - 4.2)
            for i, who in enumerate(("whitney", "lucas")):
                x = 110 + i * 26 + run * 95
                if x > 300:
                    continue
                walking = run > 0
                img = self.people[who][(int(self.time * 10) % 2 if walking else 0, "right" if walking else "down", False)]
                img = pygame.transform.scale2x(img)
                hop = -abs(math.sin(self.time * 12)) * 3 if walking else 0
                surf.blit(img, (int(x), 150 + hop))
            if 0.4 < t < 2.4:
                art.bubble(surf, "I am tired of all this dog waste!", 150, 132)
            elif 2.5 < t < 4.2:
                art.bubble(surf, "Babe, we are out of here!", 190, 132)
        else:                                                 # the drive across town
            arrive = t > 9.2
            off = (t - 6.6) * 150 if not arrive else (9.2 - 6.6) * 150
            self.draw_city(surf, off)
            bob = 0 if arrive else int(math.sin(self.time * 18) * 1.5)
            self.draw_loaded_truck(surf, 130, 152 + bob, ("whitney", "lucas"))
            if arrive:
                text(surf, "NEW HOME, across the freeway...", (W // 2, 20), 18, c.YELLOW, center=True)
                art.bubble(surf, "Everybody out. That sofa is not", 210, 118)
                art.bubble(surf, "going to carry itself!", 210, 134)
        if int(self.time * 2) % 2:
            text(surf, "Big button: skip", (W - 60, 228), 12, c.WHITE, center=True)


def make(**kw):
    return BigMove(**kw)
