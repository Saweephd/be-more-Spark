"""Soldiers vs Spies: a side-scrolling run-and-gun for one or two players.

Miles (Navy SEAL, DEVGRU) and Felix (Army, Delta Force) accept their orders,
fly in, parachute down and fight across five missions: an aircraft carrier,
an army base, an airfield, a snowy mountain outpost and the spies' island.

    D-pad      run, aim (up, diagonals), crouch      big circle  jump
    triangle   fire (hold for rapid fire)            small circle pause
Player two joins on a second gamepad (press its A button). Pick-ups: S spread
shot, R rapid fire, 1UP an extra life. Finished missions unlock.

Shoot the flying capsules to drop the power-ups, and watch for turrets set
into the cliffs. All characters, art, sounds and music are original to this
project. Hits are cartoon style: enemies vanish in a puff.
"""
import math

import pygame

from . import common as c
from . import soldiers_art as art
from .common import H, W, Game

GROUND = 206
LAND_SAFE = 3.0          # seconds of safety after a parachute lands
SEA_TOP = 216
GRAV = 760.0

HEROES = {
    "miles": {"name": "Miles", "unit": "Navy SEAL, DEVGRU", "height": 33, "jump": -310.0, "fire": 0.2,
              "uniform": (70, 92, 78), "vest": (36, 44, 40), "perk": "jumps higher"},
    "felix": {"name": "Felix", "unit": "Delta Force, the Unit", "height": 28, "jump": -290.0, "fire": 0.15,
              "uniform": (168, 148, 104), "vest": (84, 70, 50), "perk": "fires faster"},
}
SKIN = (240, 202, 172)
BLOND = (246, 214, 108)
BLOND_D = (214, 176, 70)

LEVELS = [
    {"name": "The Aircraft Carrier", "theme": "carrier", "special": "drone", "boss": "heli", "length": 2700},
    {"name": "The Army Base", "theme": "base", "special": "jeep", "boss": "truck", "length": 2900},
    {"name": "The Airfield", "theme": "airfield", "special": "drone", "boss": "jet", "length": 3000},
    {"name": "The Mountain Outpost", "theme": "snow", "special": "sled", "boss": "bunker", "length": 3100},
    {"name": "The Spies' Island", "theme": "island", "special": "boat", "boss": "gunboat", "length": 3200},
]
THEMES = {
    "carrier": {"sky": (120, 170, 220), "far": (90, 130, 170), "ground": (110, 112, 120), "edge": (230, 200, 60),
                "plat": (90, 92, 100), "guard": (90, 96, 110)},
    "base": {"sky": (230, 150, 100), "far": (150, 110, 90), "ground": (130, 110, 80), "edge": (90, 76, 54),
             "plat": (150, 130, 90), "guard": (96, 106, 70)},
    "airfield": {"sky": (150, 200, 235), "far": (120, 150, 170), "ground": (70, 72, 78), "edge": (240, 240, 240),
                 "plat": (170, 90, 60), "guard": (110, 110, 120)},
    "snow": {"sky": (180, 196, 220), "far": (220, 228, 240), "ground": (236, 240, 248), "edge": (180, 196, 220),
             "plat": (120, 90, 70), "guard": (220, 224, 232)},
    "island": {"sky": (250, 160, 110), "far": (60, 120, 80), "ground": (230, 206, 150), "edge": (200, 176, 120),
               "plat": (110, 100, 90), "guard": (80, 110, 70)},
}
POINTS = {"runner": 100, "shooter": 200, "drone": 150, "jeep": 300, "sled": 250, "boat": 300, "turret": 500,
          "capsule": 100}
HP = {"runner": 1, "shooter": 2, "drone": 1, "jeep": 3, "sled": 2, "boat": 3, "turret": 6, "capsule": 1}
LEDGE_1, LEDGE_2 = 160, 114
UNLOCK_KEY = "soldiers_vs_spies_level"


class Soldiers(Game):
    name = "soldiers_vs_spies"
    title = "Soldiers vs Spies"
    players_max = 2
    help_lines = ("D-pad: run and aim   Big button: jump", "Triangle: fire (hold it down)",
                  "Second gamepad: press A to join in", "Accept your orders, soldier!")
    title_color = (130, 220, 120)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.unlocked = max(1, min(5, int(c.load_scores(self.scores_path).get(UNLOCK_KEY, 1))))
        self.reset()

    @property
    def music(self):
        return "soldiers_boss" if getattr(self, "boss_on", False) else "soldiers"

    # ---------- setup ----------
    def reset(self):
        self.score = 0
        self.win = False
        self.phase, self.pt = "select", 0.0
        self.choice = "miles"
        self.start_level = self.unlocked
        self.level = self.start_level - 1
        self.players = []
        self.two = False
        self.boss_on = False
        self.clear_world()

    def clear_world(self):
        self.cam = 0.0
        self.enemies, self.bullets, self.ebullets, self.puffs, self.pickups = [], [], [], [], []
        self.platforms, self.spawns = [], []
        self.boss = None
        self.boss_on = False
        self.wave_t = 3.0
        self.banner = ("", 0.0)

    def new_player(self, who, slot):
        hero = HEROES[who]
        return {"who": who, "slot": slot, "hero": hero, "x": 0.0, "y": -40.0, "vx": 0.0, "vy": 0.0, "on": False,
                "plat": None, "face": 1, "crouch": False, "aim": (1, 0), "cool": 0.0, "weapon": "N", "lives": 3,
                "inv": 0.0, "dead": 0.0, "chute": True, "anim": 0.0, "out": False, "flip": False, "flash": 0.0}

    def build_level(self):
        """Contra-style terrain: rocky ledges in two tiers above a continuous ground, turrets set into the cliffs."""
        L = self.level
        lv = LEVELS[L]
        rng = __import__("random").Random(500 + L)
        length = lv["length"]
        self.length = length
        self.platforms = []
        spawns = []
        x = 280
        while x < length - 520:
            w1 = rng.choice((96, 128, 160, 192))
            self.platforms.append((x, LEDGE_1, w1))
            if rng.random() < 0.55:
                spawns.append((x + w1 * 0.6, "shooter", LEDGE_1))
            if x > 600 and (L > 0 or rng.random() < 0.5):
                spawns.append((x + 14, "turret", 184))
            if w1 >= 128 and rng.random() < 0.65:
                w2 = rng.choice((64, 80, 96))
                x2 = x + rng.randint(20, max(21, w1 - w2 - 6))
                self.platforms.append((x2, LEDGE_2, w2))
                if rng.random() < 0.5:
                    spawns.append((x2 + w2 / 2, "shooter", LEDGE_2))
                elif L >= 2 and x > 600:
                    spawns.append((x2 + 14, "turret", 138))
            x += w1 + rng.randint(120, 230)
        x = 420
        while x < length - 400:
            spawns.append((x, "shooter", GROUND))
            if lv["special"] in ("drone",):
                spawns.append((x + 120, "drone", rng.randint(60, 100)))
            elif lv["special"] in ("jeep", "sled"):
                spawns.append((x + 160, lv["special"], GROUND))
            elif lv["special"] == "boat":
                spawns.append((x + 100, "boat", 228))
            x += rng.randint(300, 420) - 25 * L
        for i, kind in enumerate(("S", "R", "1UP" if L % 2 == 0 else "S")):
            spawns.append((480 + i * 800, "capsule:" + kind, 64 + 10 * i))
        self.spawns = sorted(spawns, key=lambda sp: sp[0])

    def begin_level(self):
        self.clear_world()
        self.build_level()
        self.phase, self.pt = "drop", 0.0
        for i, p in enumerate(self.players):
            if p["out"]:
                continue
            self.respawn(p, 40 + i * 30)
        self.banner = ("MISSION %d: %s" % (self.level + 1, LEVELS[self.level]["name"]), 3.0)
        self.sound.music("soldiers")

    def respawn(self, p, x=None):
        p.update({"x": self.cam + (x if x is not None else 60), "y": -30.0, "vx": 0.0, "vy": 0.0, "on": False,
                  "plat": None, "chute": True, "dead": 0.0, "inv": 2.5, "weapon": "N", "crouch": False,
                  "flip": False})

    def boom(self, x, y, big=False):
        self.puffs.append([float(x), float(y), 0.0, big])

    # ---------- per-frame ----------
    def update(self, dt, inp):
        self.pt += dt
        if self.banner[1] > 0:
            self.banner = (self.banner[0], self.banner[1] - dt)
        for b in self.puffs:
            b[2] += dt
        self.puffs = [b for b in self.puffs if b[2] < 0.42]
        getattr(self, "phase_" + self.phase)(dt, inp)

    def p2_input(self, inp):
        return getattr(inp, "p2", None)

    def phase_select(self, dt, inp):
        if "left" in inp.pressed or "right" in inp.pressed:
            self.choice = "felix" if self.choice == "miles" else "miles"
            self.sfx("move")
        if "up" in inp.pressed and self.start_level < self.unlocked:
            self.start_level += 1
            self.sfx("move")
        if "down" in inp.pressed and self.start_level > 1:
            self.start_level -= 1
            self.sfx("move")
        p2 = self.p2_input(inp)
        if p2 is not None and ("a" in p2.pressed or "start" in p2.pressed) and not self.two:
            self.two = True
            self.sfx("select")
        if self.pt > 0.3 and "a" in inp.pressed:
            other = "felix" if self.choice == "miles" else "miles"
            self.players = [self.new_player(self.choice, 0)]
            if self.two:
                self.players.append(self.new_player(other, 1))
            self.level = self.start_level - 1
            self.phase, self.pt = "briefing", 0.0
            self.sfx("select")

    def phase_briefing(self, dt, inp):
        if self.pt > 1.0 and "a" in inp.pressed:
            self.sfx("orders")
            self.phase, self.pt = "plane", 0.0

    def phase_plane(self, dt, inp):
        if self.pt < dt * 1.5:
            self.sfx("drone")
        if 1.5 < self.pt and self.pt - dt <= 1.5:
            self.sfx("whoosh")
        if self.pt > 3.4 or (self.pt > 0.5 and "a" in inp.pressed):
            self.begin_level()

    def phase_drop(self, dt, inp):
        self.phase_play(dt, inp)
        if all(not p["chute"] or p["out"] for p in self.players):
            self.phase = "play"

    def phase_play(self, dt, inp):
        self.join_check(inp)
        for p in self.players:
            if not p["out"]:
                src = inp if p["slot"] == 0 else self.p2_input(inp)
                self.update_player(p, dt, src)
        alive = [p for p in self.players if not p["out"] and not p["dead"]]
        lead = max([p["x"] for p in alive], default=self.cam + 100)
        max_cam = self.length - W
        self.cam = max(self.cam, min(max_cam, lead - 150))
        if self.cam >= max_cam - 1 and self.boss is None:
            self.start_boss()
        if self.phase == "play":
            self.spawn_due(dt)
        self.update_enemies(dt)
        self.update_bullets(dt)
        self.update_pickups(dt)
        if self.boss is not None and self.boss["hp"] > 0:
            self.update_boss(dt)
        if all(p["out"] for p in self.players):
            self.game_over()

    def join_check(self, inp):
        p2 = self.p2_input(inp)
        if p2 is not None and len(self.players) == 1 and ("a" in p2.pressed or "start" in p2.pressed):
            other = "felix" if self.players[0]["who"] == "miles" else "miles"
            np_ = self.new_player(other, 1)
            self.players.append(np_)
            self.respawn(np_, 70)
            self.sfx("select")

    def phase_clear(self, dt, inp):
        self.update_bullets(dt)
        b = self.boss
        if b is not None and self.pt < 1.6 and self.rng.random() < 0.35:
            self.boom(b["x"] + self.rng.uniform(-b["w"] / 2, b["w"] / 2), b["y"] + self.rng.uniform(-b["h"] / 2, b["h"] / 2),
                      self.rng.random() < 0.5)
        if self.pt > 3.5:
            if self.level >= len(LEVELS) - 1:
                self.phase, self.pt = "victory", 0.0
                self.sfx("win")
            else:
                self.level += 1
                self.phase, self.pt = "plane", 0.0

    def phase_victory(self, dt, inp):
        if self.pt > 5.0 or (self.pt > 1.5 and "a" in inp.pressed):
            self.win = True
            self.game_over()

    # ---------- players ----------
    def update_player(self, p, dt, inp):
        held = inp.held if inp is not None else set()
        pressed = inp.pressed if inp is not None else set()
        hero = p["hero"]
        p["inv"] = max(0.0, p["inv"] - dt)
        p["cool"] = max(0.0, p["cool"] - dt)
        p["flash"] = max(0.0, p["flash"] - dt)
        if p["dead"]:
            p["dead"] -= dt
            if p["dead"] <= 0:
                if p["lives"] <= 0:
                    p["out"] = True
                else:
                    self.respawn(p)
            return
        left, right = "left" in held, "right" in held
        up, down = "up" in held, "down" in held
        move = (1 if right else 0) - (1 if left else 0)
        p["_moving"] = bool(move)
        if move:
            p["face"] = move
        if p["chute"]:
            p["x"] += move * 70 * dt
            p["y"] += (170 if down else 95) * dt
            floor = self.floor_at(p["x"], p["y"] - 2, p)
            if p["y"] >= floor:
                p["y"], p["chute"], p["on"] = floor, False, True
                p["inv"] = max(p["inv"], LAND_SAFE)      # safe time starts when you touch down
        else:
            p["crouch"] = down and p["on"] and not move
            speed = 0 if p["crouch"] else 82
            p["x"] += move * speed * dt
            if move and p["on"]:
                p["anim"] += dt
            if "a" in pressed and p["on"]:
                if down and p["plat"] is not None:          # drop through a platform
                    p["y"] += 3
                    p["on"], p["plat"] = False, None
                else:
                    p["vy"], p["on"], p["plat"] = hero["jump"], False, None
                    p["flip"] = True
                    self.sfx("jump")
            if not p["on"]:
                p["vy"] += GRAV * dt
                old = p["y"]
                p["y"] += p["vy"] * dt
                if p["vy"] > 0:
                    floor = self.floor_at(p["x"], old, p)
                    if p["y"] >= floor:
                        p["y"], p["vy"], p["on"] = floor, 0.0, True
                        p["flip"] = False
            elif p["plat"] is not None:
                px, py, pw = p["plat"]
                if not (px - 4 <= p["x"] <= px + pw + 4):
                    p["on"], p["plat"] = False, None
        p["x"] = max(self.cam + 6, min(self.cam + W - 10, p["x"]))
        # aim: eight directions
        ax = move if move else (0 if (up and not move) else p["face"])
        ay = -1 if up else (1 if down and not p["on"] else 0)
        if up and not move:
            ax = 0
        if ax == 0 and ay == 0:
            ax = p["face"]
        p["aim"] = (ax, ay)
        if "b" in held and p["cool"] <= 0 and not p["chute"]:
            self.fire(p)
        # pick-ups
        for pk in self.pickups:
            if not pk.get("taken") and abs(pk["x"] - p["x"]) < 12 and abs(pk["y"] - (p["y"] - 12)) < 18:
                pk["taken"] = True
                if pk["kind"] == "1UP":
                    p["lives"] += 1
                else:
                    p["weapon"] = pk["kind"]
                self.sfx("powerup")
        self.pickups = [pk for pk in self.pickups if not pk.get("taken")]

    def floor_at(self, x, prev_y, p=None):
        """The surface a falling player lands on: a platform crossed this frame, else the ground."""
        best = GROUND
        for plat in self.platforms:
            px, py, pw = plat
            if px <= x <= px + pw and prev_y <= py + 1 and py < best:
                best = py
                if p is not None:
                    p["plat"] = plat
        if best == GROUND and p is not None:
            p["plat"] = None
        return best

    def pose_of(self, p):
        """The picture for a player right now: (pose, aim name), or ('tuck', None) mid-somersault."""
        if p["chute"]:
            return "fall", "fwd"
        if not p["on"] and p["flip"]:
            return "tuck", None
        ax, ay = p["aim"]
        aim = "up" if (ax == 0 and ay < 0) else ("dup" if ay < 0 else ("ddn" if ay > 0 else "fwd"))
        if p["crouch"]:
            return "kneel", "fwd"
        if not p["on"]:
            return "fall", aim
        if self.moving(p):
            return art.RUN[int(p["anim"] * 9) % 4], aim
        return "stand", aim

    def moving(self, p):
        return p.get("_moving", False)

    def gun_pos(self, p):
        pose, aim = self.pose_of(p)
        ax, ay = p["aim"]
        if pose == "tuck":
            return p["x"] + ax * 8, p["y"] - 8 + ay * 8
        face = 1 if (ax > 0 or (ax == 0 and p["face"] > 0)) else -1
        dx, hgt = art.muzzle_offset(p["who"], pose, aim, face)
        return p["x"] + dx, p["y"] - hgt

    def fire(self, p):
        gx, gy = self.gun_pos(p)
        ax, ay = p["aim"]
        base = math.atan2(ay, ax)
        angles = [base]
        if p["weapon"] == "S":
            angles = [base + math.radians(d) for d in (-24, -12, 0, 12, 24)]
        for a in angles:
            self.bullets.append({"x": gx, "y": gy, "vx": math.cos(a) * 290, "vy": math.sin(a) * 290, "slot": p["slot"],
                                 "big": p["weapon"] == "S"})
        p["cool"] = 0.09 if p["weapon"] == "R" else p["hero"]["fire"]
        p["flash"] = 0.06
        self.sfx("shot")

    def kill_player(self, p):
        if p["inv"] > 0 or p["dead"] or p["out"]:
            return
        p["lives"] -= 1
        p["dead"] = 1.4
        self.boom(p["x"], p["y"] - 12)
        self.sfx("hurt")
        self.breather(p["x"])

    def breather(self, x):
        """A fair restart: clear enemy fire, scatter runners near the drop zone, pause the next wave."""
        self.ebullets = []
        for e in self.enemies:
            if e["kind"] == "runner" and abs(e["x"] - x) < 140:
                e["hp"] = 0
                self.boom(e["x"], e["y"] - 12)
        self.wave_t = max(self.wave_t, 3.5)

    # ---------- enemies ----------
    def spawn_due(self, dt):
        edge = self.cam + W + 20
        while self.spawns and self.spawns[0][0] <= edge:
            x, kind, y = self.spawns.pop(0)
            if kind.startswith("pickup:"):
                self.pickups.append({"x": x, "y": y, "kind": kind.split(":")[1], "t": 0.0})
            elif kind.startswith("capsule:"):
                self.add_enemy("capsule", self.cam - 16, y)
                self.enemies[-1]["drop"] = kind.split(":")[1]
            else:
                self.add_enemy(kind, x, y)
                if kind == "turret":
                    self.enemies[-1]["cool"] = 2.2
        if self.boss is None:
            self.wave_t -= dt
            if self.wave_t <= 0:
                self.wave_t = max(1.0, 2.6 - 0.3 * self.level) * (0.8 if len(self.players) > 1 else 1.0)
                side = 1 if self.rng.random() < 0.8 else -1
                self.add_enemy("runner", self.cam + (W + 14 if side > 0 else -14), GROUND)

    def add_enemy(self, kind, x, y):
        w, h = {"runner": (11, 27), "shooter": (11, 27), "drone": (20, 10), "jeep": (40, 20), "sled": (34, 16),
                "boat": (44, 16), "turret": (18, 18), "capsule": (18, 12)}[kind]
        self.enemies.append({"kind": kind, "x": float(x), "y": float(y), "w": w, "h": h, "hp": HP[kind], "cool": 1.0 +
                             self.rng.random(), "t": self.rng.random() * 6, "base": float(y), "face": -1, "flash": 0.0})

    def nearest_player(self, x, targetable=False):
        live = [p for p in self.players if not p["out"] and not p["dead"]]
        if targetable:          # don't shoot at someone parachuting in or still in their safe time
            live = [p for p in live if not p["chute"] and p["inv"] <= 0.4]
        return min(live, key=lambda p: abs(p["x"] - x)) if live else None

    def aim_shot(self, x, y, speed=None):
        p = self.nearest_player(x, targetable=True)
        if p is None:
            return
        speed = speed or (100 + 8 * self.level)
        tx = p["x"] + self.rng.uniform(-14, 14)
        ty = p["y"] - p["hero"]["height"] * 0.55 + self.rng.uniform(-8, 8)
        d = math.hypot(tx - x, ty - y) or 1
        self.ebullets.append({"x": x, "y": y, "vx": (tx - x) / d * speed, "vy": (ty - y) / d * speed, "g": 0.0})
        self.sfx("eshot")

    def rect(self, e):
        if e["kind"] in ("drone", "boat", "turret", "capsule"):
            return pygame.Rect(e["x"] - e["w"] / 2, e["y"] - e["h"] / 2, e["w"], e["h"])
        return pygame.Rect(e["x"] - e["w"] / 2, e["y"] - e["h"], e["w"], e["h"])

    def player_rect(self, p):
        h = p["hero"]["height"] * (0.6 if p["crouch"] else 1.0)
        return pygame.Rect(p["x"] - 4, p["y"] - h, 8, h)

    def update_enemies(self, dt):
        for e in self.enemies:
            e["t"] += dt
            e["cool"] -= dt
            e["flash"] = max(0.0, e["flash"] - dt)
            k = e["kind"]
            target = self.nearest_player(e["x"])
            if k == "runner":
                if target and not e.get("set"):      # pick a direction once, then commit to it
                    e["face"], e["set"] = (1 if target["x"] > e["x"] else -1), True
                e["x"] += e["face"] * (58 + 5 * self.level) * dt
            elif k == "shooter":
                if target:
                    e["face"] = 1 if target["x"] > e["x"] else -1
                if e["cool"] <= 0 and abs(e["x"] - (self.cam + W / 2)) < W / 2:
                    e["cool"] = max(1.0, 2.0 - 0.15 * self.level) * self.rng.uniform(0.8, 1.3)
                    self.aim_shot(e["x"] + e["face"] * 8, e["y"] - 15)
            elif k == "drone":
                e["x"] -= 48 * dt
                e["y"] = e["base"] + math.sin(e["t"] * 2.2) * 14
                aimed = self.nearest_player(e["x"], targetable=True)
                if aimed and abs(aimed["x"] - e["x"]) < 12 and e["cool"] <= 0:
                    e["cool"] = 1.6
                    self.ebullets.append({"x": e["x"], "y": e["y"] + 5, "vx": 0.0, "vy": 120.0, "g": 0.0})
            elif k in ("jeep", "sled"):
                e["x"] -= (120 if k == "jeep" else 165) * dt
            elif k == "turret":
                if target:
                    e["angle"] = math.atan2(target["y"] - 14 - e["y"], target["x"] - e["x"])
                if e["cool"] <= 0 and self.cam + 10 < e["x"] < self.cam + W - 10:
                    e["cool"] = max(1.3, 2.4 - 0.2 * self.level) * self.rng.uniform(0.9, 1.2)
                    a = round(e.get("angle", math.pi) / (math.pi / 6)) * (math.pi / 6)
                    self.aim_shot(e["x"] + math.cos(a) * 12, e["y"] + math.sin(a) * 12)
            elif k == "capsule":
                e["x"] += 112 * dt
                e["y"] = e["base"] + math.sin(e["t"] * 2.6) * 18
            elif k == "boat":
                e["x"] -= 85 * dt
                e["y"] = e["base"] + math.sin(e["t"] * 3) * 2
                if e["cool"] <= 0 and self.cam < e["x"] < self.cam + W:
                    e["cool"] = 1.5
                    self.aim_shot(e["x"], e["y"] - 6)
            if k in ("runner", "jeep", "sled"):
                r = self.rect(e)
                for p in self.players:
                    if not p["out"] and not p["dead"] and not p["chute"] and r.colliderect(self.player_rect(p)):
                        self.kill_player(p)
        self.enemies = [e for e in self.enemies if self.cam - 80 < e["x"] < self.cam + W + 400 and e["hp"] > 0]

    def update_bullets(self, dt):
        for b in self.bullets:
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            hit = False
            for e in self.enemies:
                if e["hp"] > 0 and self.rect(e).collidepoint(b["x"], b["y"]):
                    e["hp"] -= 1
                    e["flash"] = 0.1
                    hit = True
                    if e["hp"] <= 0:
                        self.score += POINTS[e["kind"]]
                        r = self.rect(e)
                        big = e["kind"] in ("jeep", "sled", "boat", "turret")
                        self.boom(r.centerx, r.centery, big)
                        self.sfx("boom" if big else "zap")
                        if e["kind"] == "capsule":
                            self.pickups.append({"x": e["x"], "y": e["y"], "kind": e.get("drop", "S"), "t": 0.0,
                                                 "vy": -110.0})
                    else:
                        self.sfx("tick")
                    break
            if not hit and self.boss is not None and self.boss["hp"] > 0:
                hit = self.hit_boss(b)
            if hit:
                b["dead"] = True
        self.bullets = [b for b in self.bullets if not b.get("dead") and self.cam - 10 < b["x"] < self.cam + W + 10
                        and -10 < b["y"] < H + 10]
        for b in self.ebullets:
            b["vy"] += b["g"] * dt
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            for p in self.players:
                if not p["out"] and not p["dead"] and not p["chute"] and self.player_rect(p).collidepoint(b["x"], b["y"]):
                    self.kill_player(p)
                    b["dead"] = True
                    break
        self.ebullets = [b for b in self.ebullets if not b.get("dead") and self.cam - 20 < b["x"] < self.cam + W + 20
                         and -30 < b["y"] < H + 10]

    def update_pickups(self, dt):
        for pk in self.pickups:
            if "vy" in pk:
                old = pk["y"]
                pk["vy"] += 420 * dt
                pk["y"] += pk["vy"] * dt
                pk["x"] += 30 * dt
                if pk["vy"] > 0:
                    floor = self.floor_at(pk["x"], old + 7) - 7
                    if pk["y"] >= floor:
                        pk["y"] = floor
                        del pk["vy"]

    # ---------- bosses ----------
    def start_boss(self):
        kind = LEVELS[self.level]["boss"]
        base_hp = {"heli": 40, "truck": 45, "jet": 50, "bunker": 54, "gunboat": 60}[kind]
        hp = int(base_hp * (1.35 if len(self.players) > 1 else 1.0))
        x = self.length - 90
        spec = {"heli": (74, 30, 80.0), "truck": (72, 36, float(GROUND) - 18), "jet": (120, 30, float(GROUND) - 15),
                "bunker": (80, 70, float(GROUND) - 35), "gunboat": (110, 34, 214.0)}[kind]
        self.boss = {"kind": kind, "x": float(x), "y": spec[2], "w": spec[0], "h": spec[1], "hp": hp, "max": hp,
                     "t": 0.0, "cool": 2.0, "flash": 0.0, "home": float(x),
                     "ports": [18, 18, 18] if kind == "bunker" else None}
        if kind == "bunker":
            self.boss["hp"] = self.boss["max"] = 54
        self.boss_on = True
        self.sound.music("soldiers_boss")
        self.banner = ("BOSS!", 2.0)

    def boss_rect(self):
        b = self.boss
        return pygame.Rect(b["x"] - b["w"] / 2, b["y"] - b["h"] / 2, b["w"], b["h"])

    def port_rects(self):
        r = self.boss_rect()
        return [pygame.Rect(r.x + 12 + i * 22, r.y + 30, 16, 10) for i in range(3)]

    def hit_boss(self, bullet):
        b = self.boss
        if b["kind"] == "bunker":
            for i, pr in enumerate(self.port_rects()):
                if b["ports"][i] > 0 and pr.collidepoint(bullet["x"], bullet["y"]):
                    b["ports"][i] -= 1
                    b["hp"] = sum(b["ports"])
                    b["flash"] = 0.08
                    self.sfx("tick")
                    if b["ports"][i] == 0:
                        self.boom(pr.centerx, pr.centery, True)
                        self.sfx("boom")
                    self.check_boss_dead()
                    return True
            return self.boss_rect().collidepoint(bullet["x"], bullet["y"])     # walls stop bullets
        if self.boss_rect().collidepoint(bullet["x"], bullet["y"]):
            b["hp"] -= 1
            b["flash"] = 0.08
            self.sfx("tick")
            self.check_boss_dead()
            return True
        return False

    def check_boss_dead(self):
        b = self.boss
        if b["hp"] <= 0:
            self.score += 5000 + 1000 * self.level
            for i in range(6):
                self.boom(b["x"] + self.rng.uniform(-b["w"] / 2, b["w"] / 2),
                          b["y"] + self.rng.uniform(-b["h"] / 2, b["h"] / 2), True)
            self.sfx("boom")
            self.enemies, self.ebullets = [], []
            self.boss_on = False
            self.phase, self.pt = "clear", 0.0
            c.save_score(UNLOCK_KEY, min(5, self.level + 2), self.scores_path)
            self.unlocked = max(self.unlocked, min(5, self.level + 2))
            self.sound.stop_music()
            self.sfx("clear")

    def update_boss(self, dt):
        b = self.boss
        b["t"] += dt
        b["cool"] -= dt
        b["flash"] = max(0.0, b["flash"] - dt)
        k, t = b["kind"], b["t"]
        rate = max(0.7, 1.6 - 0.1 * self.level)
        if k == "heli":
            b["x"] = b["home"] - 40 + math.sin(t * 0.7) * 40
            b["y"] = 78 + math.sin(t * 1.9) * 22
            if b["cool"] <= 0:
                b["cool"] = rate
                for i in range(3):
                    self.aim_shot(b["x"] - 20, b["y"] + 10 + i * 2, 120 + 15 * i)
        elif k == "truck":
            b["x"] = b["home"] - 60 + math.sin(t * 0.8) * 60
            if b["cool"] <= 0:
                b["cool"] = rate
                for vx in (-80, -130, -180):
                    self.ebullets.append({"x": b["x"] - 10, "y": b["y"] - 20, "vx": float(vx), "vy": -200.0, "g": 380.0})
                self.sfx("eshot")
        elif k == "jet":
            b["x"] = b["home"] - 30 + math.sin(t * 0.5) * 30
            if b["cool"] <= 0:
                b["cool"] = rate * 0.8
                for a in (-12, 0, 12):
                    r = math.radians(180 + a)
                    self.ebullets.append({"x": b["x"] - b["w"] / 2, "y": b["y"] - 4, "vx": math.cos(r) * 130,
                                          "vy": math.sin(r) * 130, "g": 0.0})
                self.sfx("eshot")
        elif k == "bunker":
            if b["cool"] <= 0:
                b["cool"] = rate * 0.7
                live = [i for i, hp in enumerate(b["ports"]) if hp > 0]
                if live:
                    pr = self.port_rects()[self.rng.choice(live)]
                    self.aim_shot(pr.x, pr.centery)
        elif k == "gunboat":
            b["y"] = 214 + math.sin(t * 2.2) * 3
            b["x"] = b["home"] - 20 + math.sin(t * 0.6) * 20
            if b["cool"] <= 0:
                b["cool"] = rate
                if int(t) % 2:
                    for vx in (-100, -160):
                        self.ebullets.append({"x": b["x"] - 30, "y": b["y"] - 18, "vx": float(vx), "vy": -230.0, "g": 400.0})
                    self.sfx("eshot")
                else:
                    self.aim_shot(b["x"], b["y"] - 24)
        if k in ("truck", "jet"):
            r = self.boss_rect()
            for p in self.players:
                if not p["out"] and not p["dead"] and r.colliderect(self.player_rect(p)):
                    self.kill_player(p)

        # ---------- drawing ----------
    def theme(self):
        return LEVELS[self.level]["theme"]

    def draw_title_art(self, surf):
        th = "island"
        cam = 40 + self.time * 10
        art.draw_backdrop(surf, th, cam, self.time)
        art.draw_ledge(surf, th, 230 - (cam % 1), LEDGE_2, 96, cam)
        art.draw_ledge(surf, th, 190, LEDGE_1, 190, cam)
        art.draw_ground(surf, th, cam)
        surf.blit(art.turret(math.pi * 0.9), (204, 172))
        miles = self.new_player("miles", 0) | {"aim": (1, -1), "chute": False, "on": True}
        felix = self.new_player("felix", 1) | {"aim": (1, 0), "chute": False, "on": True, "_moving": True,
                                              "anim": self.time}
        self.draw_soldier(surf, 270, LEDGE_2, miles)
        self.draw_soldier(surf, 90, GROUND, felix)
        art.muzzle(surf, 112, GROUND - 26, self.time)
        for i in range(4):
            bx = 140 + i * 30 + (self.time * 140) % 60
            surf.fill((255, 250, 200), (int(bx), GROUND - 26, 3, 2))
        small, big = art.booms()
        surf.blit(big[int(self.time * 10) % 6], (330, 150))

    def draw(self, surf):
        getattr(self, "draw_" + {"drop": "play", "clear": "play"}.get(self.phase, self.phase))(surf)

    def draw_select(self, surf):
        art.scene_select(surf, self.pt, self.choice, HEROES, self.start_level, self.unlocked, self.two)

    def briefing_lines(self):
        lines = ["ORDERS"]
        for i, p in enumerate(self.players):
            lines.append("%s %s, %s" % ("To:" if i == 0 else "     ", p["hero"]["name"], p["hero"]["unit"]))
        lines += ["", "Spies stole the Golden Codebook.", "Follow them from the carrier",
                  "to their hideout on the island.", "",
                  "Mission %d: %s" % (self.level + 1, LEVELS[self.level]["name"]),
                  "Recover the codebook.", "Bring everyone home."]
        return lines

    def draw_briefing(self, surf):
        art.scene_briefing(surf, self.pt, self.players, self.level, self.briefing_lines())

    def draw_plane(self, surf):
        lv = LEVELS[self.level]
        art.scene_plane(surf, self.pt, lv["theme"], self.level, lv["name"], self.players)

    def draw_victory(self, surf):
        art.scene_victory(surf, self.pt, self.players)

    def draw_play(self, surf):
        th = self.theme()
        cam = int(self.cam)
        art.draw_backdrop(surf, th, self.cam, self.time)
        for px_, py_, pw in sorted(self.platforms, key=lambda pl: pl[1]):
            sx = px_ - cam
            if -pw < sx < W:
                art.draw_ledge(surf, th, sx, py_, pw, cam)
        art.draw_ground(surf, th, cam)
        if th == "island":
            pygame.draw.rect(surf, (30, 96, 166), (0, SEA_TOP, W, H - SEA_TOP))
            for i in range(14):
                x = (i * 37 - cam) % (W + 20) - 10
                pygame.draw.line(surf, (130, 196, 240), (x, SEA_TOP + 4 + (i % 3) * 7), (x + 9, SEA_TOP + 4 + (i % 3) * 7))
        for e in self.enemies:
            if e["kind"] == "turret":
                self.draw_enemy(surf, e, cam)
        if self.boss is not None and self.boss["hp"] > 0:
            self.draw_boss(surf, cam)
        for pk in self.pickups:
            pk["t"] += 1 / 60
            img = art.pickup_badge(pk["kind"], pk["t"])
            bob = 0 if "vy" in pk else math.sin(pk["t"] * 4) * 2
            surf.blit(img, (int(pk["x"] - cam - img.get_width() / 2), int(pk["y"] + bob - img.get_height() / 2)))
        for e in self.enemies:
            if e["kind"] != "turret":
                self.draw_enemy(surf, e, cam)
        for p in self.players:
            if p["out"]:
                continue
            if p["dead"]:
                if int(self.time * 10) % 2:
                    img = art.lying(p["who"], p["face"])
                    surf.blit(img, (int(p["x"] - cam - img.get_width() / 2), int(p["y"] - img.get_height() + 1)))
                continue
            if p["inv"] > 0 and int(self.time * 12) % 2 and not p["chute"]:
                continue
            self.draw_soldier(surf, p["x"] - cam, p["y"], p)
        for b in self.bullets:
            x, y = int(b["x"] - cam), int(b["y"])
            if b.get("big"):
                pygame.draw.circle(surf, (240, 60, 40), (x, y), 3)
                pygame.draw.circle(surf, (255, 240, 200), (x, y), 1)
            else:
                surf.fill((255, 250, 190), (x - 1, y - 1, 3, 3))
                surf.set_at((x, y), (255, 255, 255))
        for b in self.ebullets:
            x, y = int(b["x"] - cam), int(b["y"])
            pygame.draw.circle(surf, art.OUT, (x, y), 3)
            pygame.draw.circle(surf, (240, 50, 40), (x, y), 2)
            surf.set_at((x - 1, y - 1), (255, 220, 200))
        small, big = art.booms()
        for x, y, age, is_big in self.puffs:
            frames = big if is_big else small
            img = frames[min(5, int(age / 0.07))]
            surf.blit(img, (int(x - cam - img.get_width() / 2), int(y - img.get_height() / 2)))
        self.draw_hud(surf)
        if self.banner[1] > 0 and self.state != "over":
            art.say(surf, self.banner[0], (W // 2, 54), 24, c.YELLOW)
        if self.phase == "clear":
            art.say(surf, "MISSION COMPLETE!", (W // 2, 84), 34, c.YELLOW)

    def draw_hud(self, surf):
        medal = art.medal()
        for i, p in enumerate(self.players):
            right = i == 1
            x = W - 8 if right else 6
            art.say(surf, "%dP" % (i + 1), (x - 14 if right else x, 2), 14, (120, 200, 255) if not right else (255, 170, 120),
                    center=False)
            if p["out"]:
                art.say(surf, "OUT", (x - 40 if right else x + 18, 2), 14, (200, 200, 200), center=False)
                continue
            for k in range(min(6, max(0, p["lives"]))):
                mx = x - 26 - k * 10 if right else x + 18 + k * 10
                surf.blit(medal, (mx, 2))
            if p["weapon"] != "N":
                badge = art.pickup_badge(p["weapon"], 0)
                surf.blit(badge, (x - 40 - 6 * 10 if right else x + 18 + 6 * 10, 2))
        art.say(surf, "%06d" % int(self.score), (W // 2, 2), 16, (255, 255, 255))
        if self.boss is not None and self.boss["hp"] > 0:
            b = self.boss
            pygame.draw.rect(surf, art.OUT, (139, 19, 122, 8))
            pygame.draw.rect(surf, (90, 20, 20), (140, 20, 120, 6))
            pygame.draw.rect(surf, (240, 70, 60), (140, 20, int(120 * b["hp"] / b["max"]), 6))
            pygame.draw.line(surf, (255, 170, 150), (140, 20), (140 + int(120 * b["hp"] / b["max"]), 20))

    def draw_soldier(self, surf, x, feet, p):
        pose, aim = self.pose_of(p)
        face = p["face"]
        if aim and p["aim"][0]:
            face = 1 if p["aim"][0] > 0 else -1
        if pose == "tuck":
            img = art.tuck(p["who"], int(self.time * 14), face)
            surf.blit(img, (int(x - img.get_width() / 2), int(feet - 22)))
            return
        if p.get("chute"):
            ch = art.chute()
            surf.blit(ch, (int(x - ch.get_width() / 2), int(feet - p["hero"]["height"] - 26)))
        img, ax = art.figure(p["who"], pose, aim, face)
        surf.blit(img, (int(x - ax), int(feet - img.get_height() + 1)))
        if p.get("flash", 0) > 0:
            dx, hgt = art.muzzle_offset(p["who"], pose, aim, face)
            art.muzzle(surf, x + dx, feet - hgt, 0)

    def draw_enemy(self, surf, e, cam):
        x, y = e["x"] - cam, e["y"]
        k = e["kind"]
        flash = e["flash"] > 0
        if k in ("runner", "shooter"):
            if k == "runner":
                fr = int(e["t"] * 10) % 4
                img, ax = art.figure("guard", art.RUN[fr], "fwd", e["face"], self.theme(), 1 if fr % 2 else -1)
            else:
                t = self.nearest_player(e["x"])
                aim = "fwd"
                if t is not None:
                    dy = (t["y"] - 14) - (e["y"] - 18)
                    dx = abs(t["x"] - e["x"]) + 1
                    aim = "dup" if dy < -dx * 0.6 else ("ddn" if dy > dx * 0.6 else "fwd")
                img, ax = art.figure("spy", "stand", aim, e["face"])
            if flash:
                img = art.white(img)
            surf.blit(img, (int(x - ax), int(y - img.get_height() + 1)))
            return
        if k == "turret":
            img = art.turret(e.get("angle", math.pi), flash)
        elif k == "capsule":
            img = art.capsule(e["t"])
        elif k == "drone":
            img = art.drone(e["t"])
        elif k == "jeep":
            img = art.jeep()
        elif k == "sled":
            img = art.sled()
        else:
            img = art.boat()
        if flash and k != "turret":
            img = art.white(img)
        if k in ("jeep", "sled"):
            surf.blit(img, (int(x - img.get_width() / 2), int(y - img.get_height() + 2)))
        else:
            surf.blit(img, (int(x - img.get_width() / 2), int(y - img.get_height() / 2)))
            if k == "boat":
                for i in range(3):
                    surf.fill((240, 250, 255), (int(x + 22 + i * 5), int(y + 6 + i % 2), 4, 1))

    def draw_boss(self, surf, cam):
        b = self.boss
        k = b["kind"]
        img = art.boss_sprite(k, self.time, b["hp"] / float(b["max"]))
        if b["flash"] > 0:
            img = art.white(img) if k != "bunker" else img
        r = self.boss_rect()
        x = r.centerx - cam - img.get_width() / 2
        if k in ("truck", "jet", "bunker"):
            y = r.bottom - img.get_height() + 6
        elif k == "gunboat":
            y = r.bottom - img.get_height() + 6
        else:
            y = r.centery - img.get_height() / 2
        surf.blit(img, (int(x), int(y)))
        if k == "bunker":
            for i, pr in enumerate(self.port_rects()):
                pr = pr.move(-cam, 0)
                pygame.draw.rect(surf, art.OUT, pr.inflate(2, 2))
                if b["ports"][i] > 0:
                    pygame.draw.rect(surf, (20, 20, 26), pr)
                    hot = b["flash"] > 0 and int(self.time * 30) % 2
                    pygame.draw.circle(surf, (255, 255, 255) if hot else (240, 60, 50), pr.center, 3)
                    pygame.draw.line(surf, (150, 154, 166), pr.center, (pr.x - 4, pr.centery + 2), 2)
                else:
                    pygame.draw.rect(surf, (70, 58, 50), pr)
                    pygame.draw.line(surf, (40, 30, 26), pr.topleft, pr.bottomright)
        if k == "gunboat" and int(b["t"]) % 2 == 0:
            spy = art.spymaster()
            surf.blit(spy, (int(r.centerx - cam - 2), int(y - 12)))
        if k in ("heli", "jet", "truck") and b["hp"] < b["max"] * 0.4 and int(self.time * 8) % 2:
            surf.fill((80, 80, 84), (int(r.centerx - cam + 6), int(r.y - 4), 5, 5))

    def render(self, surf):
        super().render(surf)
        if self.state == "over" and self.win:
            art.say(surf, "Codebook recovered!", (W // 2, 30), 22, c.YELLOW)


def make(**kw):
    return Soldiers(**kw)


if __name__ == "__main__":
    c.main(make)
