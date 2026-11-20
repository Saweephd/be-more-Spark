"""Soldiers vs Spies: a side-scrolling run-and-gun for one or two players.

Miles (Navy SEAL, DEVGRU) and Felix (Army, Delta Force) accept their orders,
fly in, parachute down and fight across five missions: an aircraft carrier,
an army base, an airfield, a snowy mountain outpost and the spies' island.

    D-pad      run, aim (up, diagonals), crouch      big circle  jump
    triangle   fire (hold for rapid fire)            small circle pause
Player two joins on a second gamepad (press its A button). Pick-ups: S spread
shot, R rapid fire, 1UP an extra life. Finished missions unlock.

All characters, art, sounds and music are original to this project. Hits are
cartoon style: enemies vanish in a puff.
"""
import math

import pygame

from . import common as c
from .common import H, W, Game, text

GROUND = 206
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
POINTS = {"runner": 100, "shooter": 200, "drone": 150, "jeep": 300, "sled": 250, "boat": 300}
HP = {"runner": 1, "shooter": 2, "drone": 1, "jeep": 3, "sled": 2, "boat": 3}
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
                "inv": 0.0, "dead": 0.0, "chute": True, "anim": 0.0, "out": False}

    def build_level(self):
        L = self.level
        lv = LEVELS[L]
        rng = __import__("random").Random(500 + L)
        length = lv["length"]
        self.length = length
        self.platforms = []
        x = 260
        while x < length - 420:
            w = rng.choice((56, 72, 90))
            y = rng.choice((168, 168, 140))
            self.platforms.append((x, y, w))
            x += rng.randint(170, 260)
        spawns = []
        for (px, py, pw) in self.platforms:
            if rng.random() < 0.6:
                spawns.append((px + pw / 2, "shooter", py))
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
            spawns.append((500 + i * 800, "pickup:" + kind, 146))
        self.spawns = sorted(spawns)

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
                  "plat": None, "chute": True, "dead": 0.0, "inv": 2.5, "weapon": "N", "crouch": False})

    # ---------- per-frame ----------
    def update(self, dt, inp):
        self.pt += dt
        if self.banner[1] > 0:
            self.banner = (self.banner[0], self.banner[1] - dt)
        self.puffs = [[x, y, r + 30 * dt, t - dt, col] for x, y, r, t, col in self.puffs if t > dt]
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
        if 1.8 < self.pt and self.pt - dt <= 1.8:
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
        if move:
            p["face"] = move
        if p["chute"]:
            p["x"] += move * 55 * dt
            p["y"] += 60 * dt
            floor = self.floor_at(p["x"], p["y"] - 2, p)
            if p["y"] >= floor:
                p["y"], p["chute"], p["on"] = floor, False, True
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
                    self.sfx("jump")
            if not p["on"]:
                p["vy"] += GRAV * dt
                old = p["y"]
                p["y"] += p["vy"] * dt
                if p["vy"] > 0:
                    floor = self.floor_at(p["x"], old, p)
                    if p["y"] >= floor:
                        p["y"], p["vy"], p["on"] = floor, 0.0, True
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
                self.puffs.append([pk["x"], pk["y"], 3.0, 0.6, (250, 230, 120)])
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

    def gun_pos(self, p):
        h = p["hero"]["height"] * (0.6 if p["crouch"] else 1.0)
        return p["x"] + p["aim"][0] * 7, p["y"] - h * 0.62 + p["aim"][1] * 6

    def fire(self, p):
        gx, gy = self.gun_pos(p)
        ax, ay = p["aim"]
        base = math.atan2(ay, ax)
        angles = [base]
        if p["weapon"] == "S":
            angles = [base + math.radians(d) for d in (-24, -12, 0, 12, 24)]
        for a in angles:
            self.bullets.append({"x": gx, "y": gy, "vx": math.cos(a) * 290, "vy": math.sin(a) * 290, "slot": p["slot"]})
        p["cool"] = 0.09 if p["weapon"] == "R" else p["hero"]["fire"]
        self.sfx("shot")

    def kill_player(self, p):
        if p["inv"] > 0 or p["dead"] or p["out"]:
            return
        p["lives"] -= 1
        p["dead"] = 1.4
        self.puffs.append([p["x"], p["y"] - 12, 4.0, 0.8, (240, 240, 240)])
        self.sfx("hurt")

    # ---------- enemies ----------
    def spawn_due(self, dt):
        edge = self.cam + W + 20
        while self.spawns and self.spawns[0][0] <= edge:
            x, kind, y = self.spawns.pop(0)
            if kind.startswith("pickup:"):
                self.pickups.append({"x": x, "y": y, "kind": kind.split(":")[1], "t": 0.0})
            else:
                self.add_enemy(kind, x, y)
        if self.boss is None:
            self.wave_t -= dt
            if self.wave_t <= 0:
                self.wave_t = max(1.0, 2.6 - 0.3 * self.level) * (0.8 if len(self.players) > 1 else 1.0)
                side = 1 if self.rng.random() < 0.8 else -1
                self.add_enemy("runner", self.cam + (W + 14 if side > 0 else -14), GROUND)

    def add_enemy(self, kind, x, y):
        w, h = {"runner": (11, 27), "shooter": (11, 27), "drone": (18, 8), "jeep": (34, 18), "sled": (28, 14),
                "boat": (40, 14)}[kind]
        self.enemies.append({"kind": kind, "x": float(x), "y": float(y), "w": w, "h": h, "hp": HP[kind], "cool": 1.0 +
                             self.rng.random(), "t": self.rng.random() * 6, "base": float(y), "face": -1, "flash": 0.0})

    def nearest_player(self, x):
        live = [p for p in self.players if not p["out"] and not p["dead"]]
        return min(live, key=lambda p: abs(p["x"] - x)) if live else None

    def aim_shot(self, x, y, speed=None):
        p = self.nearest_player(x)
        if p is None:
            return
        speed = speed or (110 + 10 * self.level)
        tx, ty = p["x"], p["y"] - p["hero"]["height"] * 0.55
        d = math.hypot(tx - x, ty - y) or 1
        self.ebullets.append({"x": x, "y": y, "vx": (tx - x) / d * speed, "vy": (ty - y) / d * speed, "g": 0.0})
        self.sfx("eshot")

    def rect(self, e):
        if e["kind"] in ("drone", "boat"):
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
                if target:
                    e["face"] = 1 if target["x"] > e["x"] else -1
                e["x"] += e["face"] * (62 + 6 * self.level) * dt
            elif k == "shooter":
                if target:
                    e["face"] = 1 if target["x"] > e["x"] else -1
                if e["cool"] <= 0 and abs(e["x"] - (self.cam + W / 2)) < W / 2:
                    e["cool"] = max(1.0, 2.0 - 0.15 * self.level) * self.rng.uniform(0.8, 1.3)
                    self.aim_shot(e["x"] + e["face"] * 8, e["y"] - 15)
            elif k == "drone":
                e["x"] -= 48 * dt
                e["y"] = e["base"] + math.sin(e["t"] * 2.2) * 14
                if target and abs(target["x"] - e["x"]) < 12 and e["cool"] <= 0:
                    e["cool"] = 1.4
                    self.ebullets.append({"x": e["x"], "y": e["y"] + 5, "vx": 0.0, "vy": 120.0, "g": 0.0})
            elif k in ("jeep", "sled"):
                e["x"] -= (120 if k == "jeep" else 165) * dt
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
                        self.puffs.append([e["x"], e["y"] - e["h"] / 2, 4.0, 0.6, (240, 240, 240)])
                        self.sfx("boom" if e["kind"] in ("jeep", "sled", "boat") else "zap")
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

    # ---------- bosses ----------
    def start_boss(self):
        kind = LEVELS[self.level]["boss"]
        base_hp = {"heli": 40, "truck": 45, "jet": 50, "bunker": 54, "gunboat": 60}[kind]
        hp = int(base_hp * (1.35 if len(self.players) > 1 else 1.0))
        x = self.length - 90
        spec = {"heli": (74, 30, 80.0), "truck": (72, 36, float(GROUND) - 18), "jet": (120, 30, float(GROUND) - 15),
                "bunker": (84, 64, float(GROUND) - 32), "gunboat": (110, 34, 214.0)}[kind]
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
        b = self.boss
        r = self.boss_rect()
        return [pygame.Rect(r.x + 6 + i * 26, r.y + 14, 18, 12) for i in range(3)]

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
                        self.puffs.append([pr.centerx, pr.centery, 6.0, 0.8, (255, 200, 120)])
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
                self.puffs.append([b["x"] + self.rng.uniform(-b["w"] / 2, b["w"] / 2),
                                   b["y"] + self.rng.uniform(-b["h"] / 2, b["h"] / 2), 5.0, 1.2, (255, 190, 90)])
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
    def draw_title_art(self, surf):
        self.draw_backdrop(surf, "carrier", 0)
        self.draw_soldier(surf, 150, GROUND, self.new_player("miles", 0) | {"aim": (1, 0), "chute": False})
        self.draw_soldier(surf, 240, GROUND, self.new_player("felix", 1) | {"aim": (-1, 0), "face": -1, "chute": False})

    def draw(self, surf):
        getattr(self, "draw_" + {"drop": "play", "clear": "play"}.get(self.phase, self.phase))(surf)

    def draw_select(self, surf):
        surf.fill((24, 34, 30))
        text(surf, "CHOOSE YOUR OPERATOR", (W // 2, 12), 26, c.YELLOW, center=True)
        for i, who in enumerate(("miles", "felix")):
            x = 110 + i * 180
            sel = who == self.choice
            pygame.draw.rect(surf, (70, 140, 90) if sel else (40, 60, 50), (x - 70, 40, 140, 140), border_radius=6)
            if sel:
                pygame.draw.rect(surf, c.YELLOW, (x - 70, 40, 140, 140), 2, border_radius=6)
            big = pygame.Surface((40, 40), pygame.SRCALPHA)
            self.draw_soldier(big, 20, 39, self.new_player(who, 0) | {"aim": (1, 0), "chute": False})
            surf.blit(pygame.transform.scale(big, (100, 100)), (x - 50, 44))
            hero = HEROES[who]
            text(surf, hero["name"], (x, 146), 22, c.WHITE, center=True)
            text(surf, hero["unit"], (x, 164), 14, (200, 230, 200), center=True)
        text(surf, "Left/right: choose   Big button: go", (W // 2, 190), 16, c.WHITE, center=True)
        lvl = "Start at mission %d of %d (up/down)" % (self.start_level, self.unlocked) if self.unlocked > 1 else "Mission 1"
        text(surf, lvl, (W // 2, 206), 16, (190, 220, 255), center=True)
        text(surf, "Player 2 ready!" if self.two else "Player 2: press A on the second gamepad", (W // 2, 222), 14,
             (250, 200, 120), center=True)

    def draw_briefing(self, surf):
        surf.fill((14, 18, 16))
        pygame.draw.rect(surf, (226, 214, 180), (30, 12, W - 60, H - 30))
        pygame.draw.rect(surf, (170, 40, 40), (W - 120, 18, 80, 16))
        text(surf, "TOP SECRET", (W - 80, 20), 16, c.WHITE, center=True, shadow=False)
        lines = ["ORDERS"] + ["%s %s, %s" % ("To:" if i == 0 else "      ", p["hero"]["name"], p["hero"]["unit"])
                             for i, p in enumerate(self.players)] + [""] + [
                 "Spies have stolen the Golden Codebook.",
                 "Track them from the carrier to their island hideout.",
                 "Recover the codebook. Bring everyone home."]
        lines = [x for x in lines if x is not None]
        shown = int(self.pt * 50)
        y = 40
        for line in lines:
            part = line[:max(0, shown)]
            shown -= len(line)
            text(surf, part, (42, y), 18 if line == "ORDERS" else 16, (30, 30, 30), shadow=False)
            y += 22
        if self.pt > 1.0 and int(self.pt * 2) % 2 == 0:
            text(surf, "Big button: ACCEPT YOUR ORDERS", (W // 2, H - 40), 20, (30, 110, 40), center=True, shadow=False)

    def draw_plane(self, surf):
        th = THEMES[LEVELS[self.level]["theme"]]
        surf.fill(th["sky"])
        for i in range(6):
            cx = (i * 90 - int(self.pt * 60)) % (W + 80) - 40
            pygame.draw.ellipse(surf, (240, 240, 245), (cx, 30 + (i * 37) % 120, 50, 14))
        px = -120 + self.pt * 170
        py = 70
        pygame.draw.rect(surf, (90, 100, 90), (px, py, 120, 22), border_radius=8)      # cargo plane
        pygame.draw.polygon(surf, (70, 80, 70), [(px + 40, py + 6), (px + 70, py + 6), (px + 60, py - 22), (px + 48, py - 22)])
        pygame.draw.polygon(surf, (70, 80, 70), [(px, py), (px - 12, py - 18), (px + 8, py)])
        pygame.draw.circle(surf, (180, 210, 230), (int(px + 112), py + 8), 4)
        if self.pt > 1.6:
            for i, p in enumerate(self.players):
                t = self.pt - 1.6 - i * 0.25
                if t > 0:
                    jx = px - 120 * (t) + 40
                    jy = py + 20 + t * 70
                    if t > 0.5:
                        pygame.draw.arc(surf, (230, 230, 230), (jx - 10, jy - 24, 20, 18), 0, math.pi, 3)
                    self.draw_soldier(surf, jx, jy, p | {"aim": (1, 0)})
        text(surf, "MISSION %d: %s" % (self.level + 1, LEVELS[self.level]["name"]), (W // 2, 200), 22, c.WHITE,
             center=True)

    def draw_victory(self, surf):
        surf.fill((20, 30, 60))
        for i in range(24):
            x = (i * 53 + int(self.pt * 80)) % W
            y = (i * 31 + int(self.pt * 40)) % 120
            pygame.draw.circle(surf, [(250, 200, 80), (120, 220, 255), (250, 120, 160)][i % 3], (x, y), 2)
        text(surf, "MISSION ACCOMPLISHED", (W // 2, 50), 30, c.YELLOW, center=True)
        text(surf, "The Golden Codebook is safe.", (W // 2, 90), 20, c.WHITE, center=True)
        text(surf, "Everyone comes home.", (W // 2, 110), 20, c.WHITE, center=True)
        for i, p in enumerate(self.players):
            self.draw_soldier(surf, W // 2 - 20 + i * 40, 190, p | {"aim": (0, -1), "dead": 0, "chute": False})

    def draw_backdrop(self, surf, theme, cam):
        th = THEMES[theme]
        surf.fill(th["sky"])
        off = int(cam * 0.3)
        if theme == "carrier":
            pygame.draw.rect(surf, (40, 90, 150), (0, 150, W, 90))
            for i in range(-1, 6):
                x = i * 120 - off % 120
                pygame.draw.polygon(surf, (70, 74, 82), [(x, 150), (x + 30, 120), (x + 60, 150)])
        elif theme == "base":
            for i in range(-1, 8):
                x = i * 70 - off % 70
                pygame.draw.rect(surf, (120, 90, 70), (x, 120, 50, 40))
                pygame.draw.polygon(surf, (90, 60, 50), [(x - 4, 120), (x + 25, 104), (x + 54, 120)])
            for x in range(-(off % 8), W, 8):
                pygame.draw.line(surf, (110, 110, 110), (x, 168), (x + 8, 184))
        elif theme == "airfield":
            for i in range(-1, 5):
                x = i * 150 - off % 150
                pygame.draw.rect(surf, (140, 140, 150), (x, 110, 110, 60))
                pygame.draw.ellipse(surf, (120, 120, 130), (x, 96, 110, 30))
                pygame.draw.rect(surf, (60, 60, 70), (x + 30, 130, 50, 40))
        elif theme == "snow":
            for i in range(-1, 6):
                x = i * 110 - off % 110
                pygame.draw.polygon(surf, (150, 160, 190), [(x, 170), (x + 55, 70), (x + 110, 170)])
                pygame.draw.polygon(surf, (250, 250, 255), [(x + 40, 98), (x + 55, 70), (x + 70, 98)])
            for i in range(40):
                sx = (i * 47 + int(self.time * 20) - off) % W
                sy = (i * 29 + int(self.time * 40)) % H
                surf.set_at((sx, sy), (255, 255, 255))
        else:
            pygame.draw.circle(surf, (255, 220, 120), (300, 70), 24)
            for i in range(-1, 6):
                x = i * 100 - off % 100
                pygame.draw.rect(surf, (110, 80, 50), (x + 40, 120, 4, 50))
                for a in range(0, 360, 60):
                    pygame.draw.line(surf, th["far"], (x + 42, 120),
                                     (x + 42 + int(16 * math.cos(math.radians(a))), 120 + int(10 * math.sin(math.radians(a)))), 3)

    def draw_play(self, surf):
        lv = LEVELS[self.level]
        th = THEMES[lv["theme"]]
        cam = int(self.cam)
        self.draw_backdrop(surf, lv["theme"], cam)
        pygame.draw.rect(surf, th["ground"], (0, GROUND, W, H - GROUND))
        pygame.draw.rect(surf, th["edge"], (0, GROUND, W, 2))
        if lv["theme"] == "carrier":                     # flight deck markings
            for x in range(-(cam % 36), W, 36):
                pygame.draw.rect(surf, (230, 200, 60), (x, GROUND + 10, 18, 2))
            pygame.draw.line(surf, (235, 235, 235), (0, GROUND + 22), (W, GROUND + 22), 1)
        if lv["theme"] == "island":
            pygame.draw.rect(surf, (40, 110, 170), (0, SEA_TOP, W, H - SEA_TOP))
            for x in range(-(cam % 24), W, 24):
                pygame.draw.line(surf, (120, 190, 230), (x, SEA_TOP + 6), (x + 10, SEA_TOP + 6))
        elif lv["theme"] == "airfield":
            for x in range(-(cam % 40), W, 40):
                pygame.draw.rect(surf, (240, 240, 240), (x, GROUND + 14, 20, 3))
        for px, py, pw in self.platforms:
            sx = px - cam
            if -pw < sx < W:
                pygame.draw.rect(surf, th["plat"], (sx, py, pw, 8))
                pygame.draw.rect(surf, c.INK, (sx, py, pw, 8), 1)
                pygame.draw.line(surf, th["plat"], (sx + 4, py + 8), (sx + 4, GROUND), 2)
                pygame.draw.line(surf, th["plat"], (sx + pw - 4, py + 8), (sx + pw - 4, GROUND), 2)
        for pk in self.pickups:
            pk["t"] += 1 / 60
            y = pk["y"] + math.sin(pk["t"] * 3) * 3
            pygame.draw.ellipse(surf, (220, 60, 60), (pk["x"] - cam - 9, y - 6, 18, 12))
            text(surf, pk["kind"], (int(pk["x"] - cam), int(y) - 6), 14, c.WHITE, center=True, shadow=False)
        if self.boss is not None and self.boss["hp"] > 0:
            self.draw_boss(surf, cam, th)
        for e in self.enemies:
            self.draw_enemy(surf, e, cam, th)
        for p in self.players:
            if not p["out"] and not p["dead"] and not (p["inv"] > 0 and int(self.time * 12) % 2 and not p["chute"]):
                self.draw_soldier(surf, p["x"] - cam, p["y"], p)
        for b in self.bullets:
            pygame.draw.circle(surf, (255, 240, 120), (int(b["x"] - cam), int(b["y"])), 2)
        for b in self.ebullets:
            pygame.draw.circle(surf, (255, 90, 80), (int(b["x"] - cam), int(b["y"])), 3)
        for x, y, r, t, col in self.puffs:
            pygame.draw.circle(surf, col, (int(x - cam), int(y)), int(r))
        self.draw_hud(surf)
        if self.banner[1] > 0 and self.state != "over":
            text(surf, self.banner[0], (W // 2, 60), 24, c.YELLOW, center=True)
        if self.phase == "clear":
            text(surf, "MISSION COMPLETE!", (W // 2, 90), 32, c.YELLOW, center=True)

    def draw_hud(self, surf):
        pygame.draw.rect(surf, (16, 20, 18), (0, 0, W, 15))
        text(surf, "%d" % int(self.score), (W // 2 - 20, 1), 16, c.WHITE)
        for i, p in enumerate(self.players):
            x = 4 if i == 0 else W - 120
            label = "%s %s" % (p["hero"]["name"], "OUT" if p["out"] else "x%d" % max(0, p["lives"]))
            if p["weapon"] != "N":
                label += "  [%s]" % p["weapon"]
            text(surf, label, (x, 1), 16, (200, 240, 200) if i == 0 else (250, 210, 140))
        if self.boss is not None and self.boss["hp"] > 0:
            b = self.boss
            pygame.draw.rect(surf, (60, 20, 20), (100, 20, 200, 6))
            pygame.draw.rect(surf, (240, 70, 60), (100, 20, int(200 * b["hp"] / b["max"]), 6))

    def draw_soldier(self, surf, x, feet, p):
        hero = p["hero"]
        h = hero["height"] * (0.62 if p.get("crouch") else 1.0)
        k = hero["height"] / 24.0
        x, feet = int(x), int(feet)
        def sx(v):
            return int(round(v * k))
        top = feet - int(h)
        uni, vest = hero["uniform"], hero["vest"]
        if p.get("chute"):
            pygame.draw.arc(surf, (230, 232, 236), (x - 16, top - 26, 32, 26), 0, math.pi, 4)
            pygame.draw.line(surf, (200, 200, 200), (x - 15, top - 13), (x - 3, top + 4))
            pygame.draw.line(surf, (200, 200, 200), (x + 15, top - 13), (x + 3, top + 4))
        leg_h = int(h * 0.38)
        step = int(p.get("anim", 0) * 10) % 2 if p.get("on") else 0
        pygame.draw.rect(surf, uni, (x - sx(4) + step, feet - leg_h, sx(3), leg_h))
        pygame.draw.rect(surf, uni, (x + sx(1) - step, feet - leg_h, sx(3), leg_h))
        pygame.draw.rect(surf, (40, 34, 30), (x - sx(5) + step, feet - 2, sx(4), 2))
        pygame.draw.rect(surf, (40, 34, 30), (x + sx(1) - step, feet - 2, sx(4), 2))
        body_top = top + int(h * 0.26)
        pygame.draw.rect(surf, uni, (x - sx(5), body_top, sx(10), feet - leg_h - body_top + 1))
        pygame.draw.rect(surf, vest, (x - sx(4), body_top + 2, sx(8), max(2, int(h * 0.22))))
        head = int(h * 0.24)
        f = 1 if p.get("face", 1) > 0 else -1
        pygame.draw.rect(surf, SKIN, (x - sx(3), top + 2, sx(7), head))
        pygame.draw.rect(surf, BLOND, (x - sx(4), top, sx(9), sx(3)))                 # blond hair
        pygame.draw.rect(surf, BLOND_D, (x - sx(4) if f > 0 else x + sx(2), top + 1, sx(3), sx(4)))
        pygame.draw.rect(surf, c.INK, (x + (sx(1) if f > 0 else -sx(2)), top + sx(4), 2, 2))   # eye
        ax, ay = p.get("aim", (1, 0))
        gx, gy = x + ax * sx(2), body_top + sx(3)
        pygame.draw.line(surf, (34, 34, 38), (gx, gy), (gx + ax * sx(10), gy + ay * sx(10)), 3)

    def draw_enemy(self, surf, e, cam, th):
        x, y = int(e["x"] - cam), int(e["y"])
        k = e["kind"]
        flash = e["flash"] > 0
        if k in ("runner", "shooter"):
            suit = (240, 240, 240) if flash else ((26, 26, 30) if k == "shooter" else th["guard"])
            top = y - 27
            pygame.draw.rect(surf, suit, (x - 5, top + 7, 10, 20))
            pygame.draw.rect(surf, (20, 20, 24), (x - 1, top + 18, 2, 9))              # gap between the legs
            if k == "shooter":
                pygame.draw.rect(surf, (240, 240, 240), (x - 1, top + 8, 3, 7))    # white shirt and tie
                pygame.draw.rect(surf, (170, 30, 40), (x, top + 9, 1, 5))
            pygame.draw.rect(surf, SKIN, (x - 4, top, 8, 7))
            pygame.draw.rect(surf, c.INK, (x - 4, top + 2, 8, 2))                 # sunglasses
            if k == "runner":
                pygame.draw.rect(surf, th["guard"] if not flash else c.WHITE, (x - 5, top - 2, 10, 3))
            pygame.draw.line(surf, c.INK, (x, top + 12), (x + e["face"] * 10, top + 12), 3)
        elif k == "drone":
            col = c.WHITE if flash else (60, 60, 70)
            pygame.draw.rect(surf, col, (x - 6, y - 3, 12, 6))
            for dx in (-9, 9):
                pygame.draw.line(surf, (180, 180, 190), (x + dx - 4, y - 5), (x + dx + 4, y - 5), 2)
            pygame.draw.circle(surf, (240, 60, 60), (x, y + 2), 1)
        elif k in ("jeep", "sled"):
            col = c.WHITE if flash else ((80, 96, 60) if k == "jeep" else (200, 50, 50))
            r = self.rect(e)
            r.x -= cam
            pygame.draw.rect(surf, col, r, border_radius=3)
            if k == "jeep":
                for wx in (r.x + 6, r.right - 6):
                    pygame.draw.circle(surf, c.INK, (wx, r.bottom), 4)
                pygame.draw.rect(surf, (40, 56, 76), (r.x + 4, r.y + 3, 8, 6))
            else:
                pygame.draw.line(surf, c.INK, (r.x - 2, r.bottom + 1), (r.right + 2, r.bottom + 1), 2)
                pygame.draw.rect(surf, (26, 26, 30), (r.centerx - 3, r.y - 8, 6, 8))
        elif k == "boat":
            col = c.WHITE if flash else (60, 60, 70)
            pygame.draw.polygon(surf, col, [(x - 20, y - 4), (x + 20, y - 4), (x + 14, y + 6), (x - 16, y + 6)])
            pygame.draw.rect(surf, (26, 26, 30), (x - 2, y - 12, 6, 8))
            pygame.draw.line(surf, (200, 230, 255), (x + 20, y + 5), (x + 34, y + 7), 2)

    def draw_boss(self, surf, cam, th):
        b = self.boss
        r = self.boss_rect()
        r.x -= cam
        flash = b["flash"] > 0
        k = b["kind"]
        dark = (250, 250, 250) if flash else (40, 44, 50)
        if k == "heli":
            pygame.draw.ellipse(surf, dark, (r.x, r.y + 4, r.w - 20, r.h - 6))
            pygame.draw.rect(surf, dark, (r.right - 26, r.centery - 2, 26, 5))
            pygame.draw.circle(surf, (120, 200, 240), (r.x + 12, r.centery + 2), 6)
            blade = int(math.sin(self.time * 40) * 30)
            pygame.draw.line(surf, (200, 200, 200), (r.centerx - 10 - blade, r.y + 2), (r.centerx - 10 + blade, r.y + 2), 2)
        elif k == "truck":
            pygame.draw.rect(surf, (250, 250, 250) if flash else (70, 80, 60), r, border_radius=4)
            pygame.draw.rect(surf, dark, (r.x + 10, r.y - 10, 24, 10))
            pygame.draw.line(surf, dark, (r.x + 10, r.y - 6), (r.x - 8, r.y - 12), 4)
            for wx in (r.x + 10, r.centerx, r.right - 10):
                pygame.draw.circle(surf, c.INK, (wx, r.bottom), 7)
        elif k == "jet":
            pygame.draw.ellipse(surf, (250, 250, 250) if flash else (180, 186, 196), r)
            pygame.draw.polygon(surf, (150, 156, 166), [(r.centerx, r.y + 6), (r.centerx + 30, r.y - 18), (r.centerx + 44, r.y + 6)])
            pygame.draw.rect(surf, (40, 56, 76), (r.x + 8, r.y + 8, 16, 6))
            text(surf, "SPY AIR", (r.centerx, r.centery - 2), 14, (170, 40, 40), center=True, shadow=False)
        elif k == "bunker":
            pygame.draw.rect(surf, (250, 250, 250) if flash else (120, 124, 130), r)
            pygame.draw.rect(surf, (236, 240, 248), (r.x - 4, r.y - 6, r.w + 8, 8))       # snow on the roof
            for i, pr in enumerate(self.port_rects()):
                pr.x -= cam
                pygame.draw.rect(surf, (20, 20, 24) if b["ports"][i] > 0 else (90, 70, 60), pr)
                if b["ports"][i] > 0:
                    pygame.draw.rect(surf, (240, 70, 60), (pr.x + 7, pr.y + 4, 4, 4))
        elif k == "gunboat":
            pygame.draw.polygon(surf, (250, 250, 250) if flash else (60, 64, 72),
                                [(r.x, r.y + 4), (r.right, r.y + 4), (r.right - 12, r.bottom), (r.x + 8, r.bottom)])
            pygame.draw.rect(surf, (90, 94, 102), (r.centerx - 16, r.y - 12, 32, 16))
            pygame.draw.line(surf, dark, (r.x + 20, r.y), (r.x + 4, r.y - 10), 4)
            if int(b["t"]) % 2 == 0:       # the spymaster pops out of the hatch
                pygame.draw.rect(surf, (26, 26, 30), (r.centerx - 4, r.y - 24, 9, 12))
                pygame.draw.rect(surf, SKIN, (r.centerx - 3, r.y - 30, 7, 6))
                pygame.draw.rect(surf, c.INK, (r.centerx - 3, r.y - 28, 7, 2))

    def render(self, surf):
        super().render(surf)
        if self.state == "over" and self.win:
            text(surf, "Codebook recovered!", (W // 2, 30), 22, c.YELLOW, center=True)


def make(**kw):
    return Soldiers(**kw)


if __name__ == "__main__":
    c.main(make)
