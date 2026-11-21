"""Black Warrior, Level 1: Tower Row. A Double Dragon style beat 'em up.

Quick walks Tower Row with his face showing; when a fight starts he pulls on
his cat mask. He fights up the street, through the Trillion Tower lobby and up
the glass elevator to the penthouse, where the Trillion Heir waits. When the
Heir is beaten, Quick opens a rift into the Ninth Dominion, draws the katana
Daybreak and cuts the chain on the family vault. The city wins fair taxation
and Tower Row changes.

    D-pad              walk anywhere on the street; tap left or right twice to dodge
    Triangle (B)       punch combo; pick up a weapon, swing it
    Big circle (A)     kick combo; throw a held weapon or a grabbed enemy
    A and B together   jump (then A flying kick, B diving elbow); hold for a special
    B behind you       back elbow (hold away from the enemy)
    Walk into a dazed enemy to grab: B knees, A throws
    Hold B one second while Mazee is here: her team attack
    Small circle       pause; skips a cutscene you have already seen

Enemies are knocked out with stars over their heads, never hurt for real.
All art, sounds and music are original to this project.
"""
import math

import pygame

from . import bw_art as art
from . import common as c
from .common import H, W, Game

GRAV = 620.0
JUMP_V = 236.0
TOP, BOTTOM = art.FLOOR_TOP + 6, art.FLOOR_BOTTOM - 2
MAX_HP = 100
SEEN_KEY = "black_warrior_seen_l1"

# name: (duration, active from, active to, reach, damage, knocks down, sound, pose)
MOVES = {
    "jab": (0.20, 0.05, 0.12, 24, 6, False, "punch", "jab"),
    "cross": (0.22, 0.06, 0.14, 26, 7, False, "punch", "cross"),
    "upper": (0.34, 0.08, 0.18, 24, 10, True, "punch", "upper"),
    "kick": (0.26, 0.07, 0.16, 30, 7, False, "kick", "kick"),
    "round": (0.28, 0.08, 0.17, 32, 8, False, "kick", "round"),
    "spin": (0.40, 0.12, 0.24, 34, 12, True, "kick", "spin"),
    "backel": (0.26, 0.06, 0.15, 24, 10, True, "punch", "backel"),
    "knee": (0.22, 0.06, 0.12, 22, 7, False, "punch", "knee"),
    "swing": (0.30, 0.08, 0.18, 40, 14, True, "bonk", "swing"),
}
B_COMBO = ("jab", "cross", "upper")
A_COMBO = ("kick", "round", "spin")
ENEMY = {   # hp, speed, reach, damage, cooldown, points
    "valet": (30, 46, 22, 6, 1.3, 300),
    "security": (42, 40, 24, 8, 1.5, 500),
    "butler": (34, 54, 20, 5, 1.6, 400),
}
SCENES = [
    {"name": "street", "length": art.STREET_LEN,
     "zones": [{"at": 240, "waves": [["valet", "valet"], ["valet", "security", "valet"]]},
               {"at": 820, "waves": [["security", "valet"], ["valet", "security", "security"]]}],
     "weapons": [(470, 200, "bat"), (1000, 180, "pipe")], "token": (650, 196)},
    {"name": "lobby", "length": art.LOBBY_LEN,
     "zones": [{"at": 200, "waves": [["butler", "security"], ["butler", "valet", "butler"], ["security", "butler"]]}],
     "weapons": [(330, 196, "pipe")], "token": None},
]
ELEVATOR_STOPS = {15: ["valet", "butler"], 30: ["security", "valet", "butler"], 45: ["security", "security", "butler"]}
INTRO = [("QUICK", False, "Tower Row. The Trillion Heir's private kingdom."),
         ("QUICK", False, "Rent's up, the bus is cut, the school roof leaks..."),
         ("QUICK", False, "...and he pays less tax than the diner."),
         ("QUICK", False, "Time somebody sent him a bill.")]
BOSS_TALK = [("THE TRILLION HEIR", None, "Who let you in? This floor is for people born here."),
             ("QUICK", True, "Nice chair. Did you earn it, or did Grandpa leave it to you?"),
             ("THE TRILLION HEIR", None, "Butlers! Show this person the stairs!"),
             ("QUICK", True, "Your free ride ends tonight.")]
CUT_PHASES = ("katana", "reform")


class Fighter:
    def __init__(self, x, y):
        self.x, self.y, self.z = float(x), float(y), 0.0
        self.vx, self.vz = 0.0, 0.0
        self.face = 1
        self.state, self.st = "idle", 0.0
        self.anim = 0.0
        self.flash = 0.0


class Enemy(Fighter):
    _ids = 0

    def __init__(self, kind, x, y):
        super().__init__(x, y)
        Enemy._ids += 1
        self.id = Enemy._ids
        self.kind = kind
        hp, self.speed, self.reach, self.dmg, self.cool_max, self.points = ENEMY[kind]
        self.hp = self.max_hp = hp
        self.cool = 0.8
        self.recent = []          # times of recent hits, for dazing
        self.thrown = False
        self.attacking = False

    @property
    def alive(self):
        return self.state != "out"


class Quick(Fighter):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.hp = MAX_HP
        self.lives = 3
        self.meter = 0.0
        self.masked = False
        self.inv = 0.0
        self.move = None
        self.hit_ids = set()
        self.combo = {"a": 0, "b": 0}
        self.combo_t = 9.0
        self.air = None
        self.weapon = None
        self.held = None
        self.knees = 0
        self.recent = []


class BlackWarrior(Game):
    name = "black_warrior"
    title = "Black Warrior"
    title_color = (79, 180, 255)
    help_lines = ("Triangle: punch   Big button: kick", "Both together: jump (hold: special)",
                  "Tap a direction twice: dodge", "Right the wrongs.")

    @property
    def music(self):
        if getattr(self, "phase", "") in ("boss", "boss_intro"):
            return "bw_boss"
        if getattr(self, "phase", "") in ("reform", "complete"):
            return "bw_reform"
        return "black_warrior"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.seen = bool(c.load_scores(self.scores_path).get(SEEN_KEY, 0))
        self.reset()

    # ------------------------------------------------------------ setup
    def reset(self):
        self.score = 0
        self.win = False
        self.scene_i = 0
        self.p = Quick(60, 196)
        self.enemies, self.projs, self.fx, self.weapons = [], [], [], []
        self.bubbles = []
        self.boss = None
        self.mazee = None
        self.token = None
        self.load_scene(0)
        self.phase, self.pt = "intro", 0.0
        self.talk, self.talk_i = INTRO, 0
        self.go_t = 0.0
        self.chord = None
        self.pending = None
        self.b_hold = 0.0
        self.last_tap = {"left": -9.0, "right": -9.0}
        self.floor = 0.0
        self.stop_i = 0
        self.doors = 0.0
        self.fade = 0.0
        self.cont_t = 0.0
        self.resume_phase = "walk"

    def load_scene(self, i):
        self.scene_i = i
        self.enemies, self.projs, self.weapons = [], [], []
        self.cam = 0.0
        if i < len(SCENES):
            sc = SCENES[i]
            self.length = sc["length"]
            self.zones = [dict(z, done=False, wave=0) for z in sc["zones"]]
            self.weapons = [{"x": float(x), "y": float(y), "kind": k} for x, y, k in sc["weapons"]]
            tk = sc["token"]
            self.token = {"x": float(tk[0]), "y": float(tk[1]), "t": 0.0} if tk else None
        else:
            self.length = W
            self.zones = []
            self.token = None
        self.zone = None
        self.bubbles = []
        self.p.x, self.p.y, self.p.z = 40.0, 196.0, 0.0
        if self.mazee is not None:
            self.mazee = None

    @property
    def scene(self):
        return ["street", "lobby", "elevator", "penthouse"][self.scene_i]

    # ------------------------------------------------------------ frame
    def step(self, dt, inp):
        if self.state == "play" and self.phase in CUT_PHASES and "start" in inp.pressed and self.seen:
            inp.pressed.discard("start")
            self.skip_cutscene()
        super().step(dt, inp)

    def update(self, dt, inp):
        self.pt += dt
        self.fade = max(0.0, self.fade - dt)
        self.go_t = max(0.0, self.go_t - dt)
        for f in self.fx:
            f[3] -= dt
        self.fx = [f for f in self.fx if f[3] > 0]
        for b in self.bubbles:
            b[2] -= dt
        self.bubbles = [b for b in self.bubbles if b[2] > 0]
        getattr(self, "phase_" + self.phase)(dt, inp)

    # ------------------------------------------------------------ story phases
    def phase_intro(self, dt, inp):
        self.talk_step(inp, lambda: self.set_phase("walk"))

    def talk_step(self, inp, done):
        if self.pt > 0.3 and ("a" in inp.pressed or "b" in inp.pressed):
            line = self.talk[self.talk_i][2]
            if self.pt * 45 < len(line):
                self.pt = 99.0             # first press finishes the line
            else:
                self.talk_i += 1
                self.pt = 0.0
                self.sfx("move")
                if self.talk_i >= len(self.talk):
                    done()

    def set_phase(self, ph):
        self.phase, self.pt = ph, 0.0
        if ph in ("boss", "reform"):
            self.sound.music(self.music)

    def phase_mask_on(self, dt, inp):
        if self.pt < dt * 1.5:
            self.sfx("mask")
        if self.pt > 0.3:
            self.p.masked = True
        if self.pt > 0.6:
            self.set_phase(self.after_mask)

    def phase_mask_off(self, dt, inp):
        self.update_world(dt, inp, control=True)
        if self.pt > 0.3:
            self.p.masked = False
        if self.pt > 0.5:
            self.set_phase("walk")

    def put_mask_on(self, then):
        self.after_mask = then
        self.p.state, self.p.move = "idle", None
        self.set_phase("mask_on")

    # ------------------------------------------------------------ street and lobby
    def phase_walk(self, dt, inp):
        self.update_world(dt, inp, control=True)
        p = self.p
        if self.scene_i >= len(SCENES):
            return
        nxt = next((z for z in self.zones if not z["done"]), None)
        if nxt is not None and self.cam >= nxt["at"] - 1:
            self.zone = nxt
            self.cam = float(nxt["at"])
            self.put_mask_on("fight")
            self.spawn_wave()
            return
        lead = p.x - 150
        self.cam = max(self.cam, min(float(self.length - W), lead if nxt is None else min(lead, nxt["at"])))
        if nxt is None and p.x > self.length - 24:
            self.next_scene()

    def phase_fight(self, dt, inp):
        self.update_world(dt, inp, control=True)
        if self.phase != "fight":
            return
        if not any(e.alive for e in self.enemies):
            z = self.zone
            z["wave"] += 1
            if z["wave"] < len(z["waves"]):
                self.spawn_wave()
            else:
                z["done"] = True
                self.zone = None
                self.go_t = 3.0
                self.set_phase("mask_off")
                self.sfx("clear")

    def spawn_wave(self):
        z = self.zone
        kinds = z["waves"][z["wave"]]
        for i, k in enumerate(kinds):
            side = 1 if i % 2 == 0 else -1
            x = self.cam + (W + 20 + i * 18 if side > 0 else -20 - i * 18)
            y = TOP + 10 + (i * 23) % (BOTTOM - TOP - 10)
            self.enemies.append(Enemy(k, x, y))

    def next_scene(self):
        self.mazee_leave(silent=True)
        if self.scene_i == 0:
            self.load_scene(1)
            self.set_phase("walk")
        else:
            self.load_scene(2)
            self.floor, self.stop_i, self.doors = 0.0, 0, 0.0
            self.stop_spawned = False
            self.p.x, self.p.y = W / 2, 200.0
            self.put_mask_on("elevator")
        self.fade = 0.6

    # ------------------------------------------------------------ elevator set piece
    def phase_elevator(self, dt, inp):
        self.update_world(dt, inp, control=True)
        if self.phase != "elevator":
            return
        stops = sorted(ELEVATOR_STOPS)
        target = stops[self.stop_i] if self.stop_i < len(stops) else 60
        busy = any(e.alive for e in self.enemies)
        if self.floor < target:
            self.doors = max(0.0, self.doors - dt * 3)
            if self.doors <= 0 and not busy:
                self.floor = min(float(target), self.floor + dt * 6)
                if self.floor >= target:
                    self.sfx("ding")
                    if target == 60:
                        self.to_penthouse()
                        return
        elif self.stop_i < len(stops):
            self.doors = min(1.0, self.doors + dt * 3)
            if self.doors >= 1.0 and not busy and not getattr(self, "stop_spawned", False):
                for i, k in enumerate(ELEVATOR_STOPS[target]):
                    x = 15 if i % 2 == 0 else W - 15
                    self.enemies.append(Enemy(k, x, TOP + 12 + i * 20))
                self.stop_spawned = True
            elif self.doors >= 1.0 and not busy and self.stop_spawned:
                self.stop_i += 1
                self.stop_spawned = False

    def to_penthouse(self):
        self.load_scene(3)
        self.p.x, self.p.y = 90.0, 200.0
        self.fade = 0.6
        self.boss = {"x": 300.0, "y": 190.0, "z": 34.0, "hp": 260, "max": 260, "state": "float", "st": 0.0,
                     "flash": 0.0, "summons": 0, "vx": 0.0, "cycle": 0, "hat": False}
        self.talk, self.talk_i = BOSS_TALK, 0
        self.set_phase("boss_intro")

    # ------------------------------------------------------------ boss
    def phase_boss_intro(self, dt, inp):
        self.boss["st"] += dt
        self.talk_step(inp, lambda: self.set_phase("boss"))

    def phase_boss(self, dt, inp):
        self.update_world(dt, inp, control=True)
        if self.phase == "boss":
            self.update_boss(dt)

    def update_boss(self, dt):
        b, p = self.boss, self.p
        b["st"] += dt
        b["flash"] = max(0.0, b["flash"] - dt)
        if b["hp"] <= 0:
            self.begin_katana()
            return
        for frac in (0.66, 0.33):
            if b["hp"] < b["max"] * frac and b["summons"] < (1 if frac == 0.66 else 2):
                b["summons"] += 1
                for side in (-1, 1):
                    self.enemies.append(Enemy("butler", W / 2 + side * (W / 2 + 15), TOP + 20 + side * 15 + 20))
                self.bubble("Butlers!", b["x"], b["y"] - b["z"] - 70, 1.4)
        s = b["state"]
        if s == "float":
            b["z"] += (34 - b["z"]) * min(1.0, dt * 3)
            want_x = p.x + (90 if b["x"] >= p.x else -90)
            want_x = max(50, min(W - 50, want_x))
            b["x"] += max(-60 * dt, min(60 * dt, want_x - b["x"]))
            b["y"] += max(-40 * dt, min(40 * dt, p.y - b["y"]))
            if b["st"] > 2.2:
                b["state"], b["st"] = ("coins", 0.0) if b["cycle"] % 2 == 0 else ("ram", 0.0)
                b["cycle"] += 1
        elif s == "coins":
            if b["st"] > 0.5 and not b.get("thrown"):
                b["thrown"] = True
                d = 1 if p.x > b["x"] else -1
                for k in range(5):
                    self.projs.append({"kind": "coin", "x": b["x"] + d * 20, "y": p.y + (k - 2) * 9, "z": b["z"] + 30,
                                       "vx": d * (110 + k * 12), "vz": 60.0, "g": 260.0, "dmg": 6, "owner": "enemy"})
                self.sfx("coin")
            if b["st"] > 1.0:
                b["thrown"] = False
                b["state"], b["st"] = "tired", 0.0
        elif s == "tired":                 # the throne sinks low: now he can be hit from the ground
            b["z"] += (6 - b["z"]) * min(1.0, dt * 5)
            if b["st"] > 2.4:
                b["state"], b["st"] = "float", 0.0
        elif s == "ram":
            if b["st"] < 0.6:
                b["z"] += (44 - b["z"]) * min(1.0, dt * 4)
                b["vx"] = 230.0 if p.x > b["x"] else -230.0
                b["y"] += max(-50 * dt, min(50 * dt, p.y - b["y"]))
            else:
                b["z"] += (10 - b["z"]) * min(1.0, dt * 8)
                b["x"] += b["vx"] * dt
                if abs(b["x"] - p.x) < 26 and abs(b["y"] - p.y) < 12 and p.z < 30:
                    self.hurt_player(14, b["x"], knock=True)
                if b["x"] < 30 or b["x"] > W - 30 or b["st"] > 2.4:
                    b["x"] = max(30.0, min(W - 30.0, b["x"]))
                    b["state"], b["st"] = "tired", 0.0

    def boss_hit(self, dmg, from_air, sx, sy):
        b = self.boss
        if b is None or b["hp"] <= 0:
            return False
        if b["z"] > 14 and not from_air:
            return False
        b["hp"] = max(0, b["hp"] - dmg)
        b["flash"] = 0.08
        self.score += dmg * 10
        if self.p.state not in ("special", "flurry"):
            self.p.meter = min(3.0, self.p.meter + 0.05)
        self.fx.append(["spark", sx, sy, 0.15, True])
        return True

    # ------------------------------------------------------------ katana and reform
    def begin_katana(self):
        self.enemies, self.projs = [], []
        p, b = self.p, self.boss
        p.state, p.move, p.z, p.weapon = "cut", None, 0.0, None
        p.x, p.y, p.face = 150.0, 204.0, 1
        b["x"], b["y"], b["state"] = 300.0, 196.0, "beaten"
        self.set_phase("katana")
        self.sound.stop_music()
        self.sfx("rift")

    def phase_katana(self, dt, inp):
        t, b, p = self.pt, self.boss, self.p
        b["st"] += dt
        if 2.6 <= t < 3.0:
            p.x = min(318.0, p.x + dt * 480)
        if 3.0 <= t and t - dt < 3.0:
            self.sfx("slash")
        if 3.4 <= t and t - dt < 3.4:
            self.sfx("boom")
        if t > 3.4:
            b["z"] = max(0.0, b["z"] - dt * 30)
        if t > 4.6 and not b["hat"]:
            b["hat"] = True
            self.bubble("My... first job?", b["x"], 70, 1.8)
        if 6.0 <= t and t - dt < 6.0:
            self.sfx("rift")
        if 6.8 <= t and t - dt < 6.8:
            self.sfx("mask")
            self.bubble("Welcome to the working world.", p.x, 120, 2.2)
        p.masked = t < 6.9
        if t > 9.2:
            self.finish_katana()

    def finish_katana(self):
        if not self.seen:
            self.seen = True
            c.save_score(SEEN_KEY, 1, self.scores_path)
        self.score += 10000
        self.set_phase("reform")

    def skip_cutscene(self):
        if self.phase == "katana":
            self.boss["hat"] = True
            self.p.masked = False
            self.finish_katana()
        elif self.phase == "reform":
            self.complete()

    def phase_reform(self, dt, inp):
        if self.pt > 3.5 and self.pt - dt <= 3.5:
            self.sfx("start")
        if self.pt > 11.0 or (self.pt > 4.0 and self.seen and "a" in inp.pressed):
            self.complete()

    def complete(self):
        self.set_phase("complete")
        self.sfx("win")

    def phase_complete(self, dt, inp):
        if self.pt > 3.0 or (self.pt > 1.0 and "a" in inp.pressed):
            self.win = True
            self.game_over()

    # ------------------------------------------------------------ continue
    def phase_continue(self, dt, inp):
        if self.pt > 0.6 and ("a" in inp.pressed or "start" in inp.pressed):
            p = self.p
            p.lives, p.hp, p.inv, p.state, p.st = 3, MAX_HP, 2.5, "idle", 0.0
            self.score = 0
            self.enemies = [e for e in self.enemies if e.alive]
            for e in self.enemies:
                e.hp = e.max_hp
            self.set_phase(self.resume_phase)
            self.sfx("start")
        elif self.pt > 9.9:
            self.game_over()

    # ------------------------------------------------------------ the world: Quick, enemies, Mazee, things
    def update_world(self, dt, inp, control):
        p = self.p
        p.inv = max(0.0, p.inv - dt)
        p.combo_t += dt
        p.flash = max(0.0, p.flash - dt)
        if control:
            self.read_input(dt, inp)
        self.update_hero(dt, inp)
        for e in self.enemies:
            self.update_enemy(e, dt)
        self.enemies = [e for e in self.enemies if e.alive or e.st < 0.9]
        self.update_projs(dt)
        self.update_mazee(dt)
        self.check_pickups()

    def lo(self):
        return self.cam + 10 if self.scene_i < 2 else 12.0

    def hi(self):
        return self.cam + W - 10 if self.scene_i < 2 else W - 12.0

    def read_input(self, dt, inp):
        p = self.p
        held, pressed = inp.held, inp.pressed
        # a quick tap of A or B waits two frames to see whether the other joins it (a jump)
        for btn in ("a", "b"):
            if btn in pressed:
                other = "b" if btn == "a" else "a"
                if self.chord is None and (other in held or other in pressed or
                                           (self.pending and self.pending[0] == other)):
                    self.chord = 0.0
                    self.pending = None
                    break
                if self.chord is None and self.pending is None:
                    self.pending = [btn, 0.0]
        if self.chord is not None:
            if "a" in held and "b" in held:
                self.chord += dt
                if self.chord >= 0.45 and p.meter >= 1.0 and self.can_act():
                    self.start_special()
                    self.chord = None
            else:
                if self.chord < 0.45 or p.meter < 1.0:
                    self.start_jump(inp)
                self.chord = None
            return
        if self.pending is not None:
            self.pending[1] += dt
            if self.pending[1] >= 0.04:
                btn = self.pending[0]
                self.pending = None
                self.press(btn, inp)
        # team attack: hold B for a second while Mazee is here
        if "b" in held and "a" not in held and self.mazee is not None and self.mazee["state"] == "fight":
            self.b_hold += dt
            if self.b_hold >= 1.0:
                self.b_hold = 0.0
                self.team_attack()
        else:
            self.b_hold = 0.0
        for d in ("left", "right"):
            if d in pressed:
                if self.time - self.last_tap[d] < 0.25 and self.can_act():
                    self.start_dodge(1 if d == "right" else -1)
                self.last_tap[d] = self.time

    def can_act(self):
        return self.p.state in ("idle", "walk")

    def press(self, btn, inp):
        p = self.p
        if p.state == "jump":
            if p.air is None:
                p.air = "kick" if btn == "a" else "elbow"
                self.sfx("whiff")
            return
        if p.state == "grab":
            if btn == "b":
                self.start_move("knee")
            else:
                self.throw_held(inp)
            return
        if not self.can_act():
            return
        if btn == "b":
            if p.weapon is None and self.try_pickup():
                return
            if p.weapon is not None:
                self.start_move("swing")
                return
            away = ("left" in inp.held and p.face > 0) or ("right" in inp.held and p.face < 0)
            if away and self.enemy_behind():
                self.start_move("backel")
                return
        elif p.weapon is not None:
            self.throw_weapon()
            return
        combo = B_COMBO if btn == "b" else A_COMBO
        if p.combo_t > 0.6:
            p.combo[btn] = 0
        self.start_move(combo[p.combo[btn] % 3])
        p.combo[btn] = (p.combo[btn] + 1) % 3

    def start_move(self, name):
        p = self.p
        p.state, p.st, p.move = "atk", 0.0, name
        p.hit_ids = set()

    def start_jump(self, inp):
        p = self.p
        if not self.can_act():
            return
        p.state, p.st = "jump", 0.0
        p.vz = JUMP_V
        move = ("right" in inp.held) - ("left" in inp.held)
        p.vx = move * 80.0
        p.air = None
        p.hit_ids = set()
        self.sfx("jump")

    def start_dodge(self, d):
        p = self.p
        p.state, p.st, p.face = "dodge", 0.0, d
        p.vx = d * 190.0
        p.inv = max(p.inv, 0.32)
        self.sfx("dash")

    def start_special(self):
        p = self.p
        if p.meter >= 3.0:
            p.state, p.st = "flurry", 0.0
            p.meter = 0.0
            p.inv = 1.8
        else:
            p.state, p.st = "special", 0.0
            p.meter -= 1.0
            p.inv = 0.7
        p.hit_ids = set()
        self.sfx("special")

    def enemy_behind(self):
        p = self.p
        return any(e.alive and abs(e.y - p.y) <= 10 and 0 < (e.x - p.x) * -p.face <= 30 for e in self.enemies)

    def try_pickup(self):
        p = self.p
        for w in self.weapons:
            if abs(w["x"] - p.x) < 14 and abs(w["y"] - p.y) < 9:
                in_reach = any(e.alive and e.state not in ("down", "fly") and abs(e.y - p.y) <= 9
                               and 0 < (e.x - p.x) * p.face <= 26 for e in self.enemies)
                if in_reach:
                    return False
                self.weapons.remove(w)
                p.weapon = {"kind": w["kind"], "uses": 8}
                self.sfx("grab")
                return True
        return False

    def throw_weapon(self):
        p = self.p
        self.projs.append({"kind": p.weapon["kind"], "x": p.x + p.face * 10, "y": p.y, "z": 24.0, "vx": p.face * 260.0,
                           "vz": 30.0, "g": 120.0, "dmg": 18, "owner": "player", "spin": 0.0})
        p.weapon = None
        p.state, p.st, p.move = "atk", 0.0, "cross"
        p.hit_ids = {-1}
        self.sfx("throw")

    def throw_held(self, inp):
        p, e = self.p, self.p.held
        d = 1 if "right" in inp.held else (-1 if "left" in inp.held else p.face)
        self.launch(e, d, 210.0, 12)
        p.held = None
        p.state, p.st, p.move = "throw", 0.0, None
        self.sfx("throw")

    def launch(self, e, d, speed, dmg):
        e.hp -= dmg
        e.state, e.st = "fly", 0.0
        e.vx, e.vz, e.z = d * speed, 170.0, max(e.z, 6.0)
        e.thrown = True
        self.score += dmg * 10

    def update_hero(self, dt, inp):
        p = self.p
        p.st += dt
        held = inp.held if self.phase in ("walk", "fight", "elevator", "boss", "mask_off") else set()
        s = p.state
        if s in ("idle", "walk"):
            mx = ("right" in held) - ("left" in held)
            my = ("down" in held) - ("up" in held)
            if mx:
                p.face = mx
            p.x += mx * 78 * dt
            p.y += my * 46 * dt
            p.state = "walk" if (mx or my) else "idle"
            p.anim += dt if (mx or my) else dt * 0.5
            if p.state == "walk":
                self.try_grab()
        elif s == "atk":
            dur, a0, a1, reach, dmg, knock, snd, pose = MOVES[p.move]
            if a0 <= p.st <= a1 and -1 not in p.hit_ids:
                self.resolve_attack(reach, dmg, knock, snd, -p.face if p.move == "backel" else p.face)
            if p.st >= dur:
                if p.move == "knee" and p.held is not None:
                    p.state, p.st = "grab", 0.0
                    p.knees += 1
                    if p.knees >= 3:
                        self.launch(p.held, p.face, 120.0, 4)
                        p.held, p.knees = None, 0
                        p.state = "idle"
                else:
                    p.state, p.move = "idle", None
        elif s == "jump":
            p.z += p.vz * dt
            p.vz -= GRAV * dt
            p.x += p.vx * dt
            if p.air == "kick":
                self.resolve_attack(28, 10, True, "kick", p.face, air=True)
            if p.z <= 0:
                p.z, p.vz, p.vx = 0.0, 0.0, 0.0
                if p.air == "elbow":
                    self.resolve_attack(20, 12, True, "thud", p.face, air=True, downed=True, both=True)
                p.state, p.st, p.air = "idle", 0.0, None
                self.sfx("land")
        elif s == "dodge":
            p.x += p.vx * dt
            p.vx *= 0.9
            if p.st > 0.3:
                p.state = "idle"
        elif s == "grab":
            e = p.held
            if e is None or not e.alive or p.st > 1.6:
                if e is not None and e.state == "held":
                    e.state, e.st = "idle", 0.0
                p.held, p.state = None, "idle"
            else:
                e.x, e.y, e.face = p.x + p.face * 16, p.y, -p.face
        elif s == "throw":
            if p.st > 0.3:
                p.state = "idle"
        elif s == "special":
            if p.st > 0.12:
                self.resolve_attack(42, 18, True, "kick", p.face, radius=True)
            if p.st > 0.6:
                p.state = "idle"
        elif s == "flurry":
            for k, at in enumerate((0.3, 0.7, 1.1)):
                if p.st >= at and p.st - dt < at:
                    for e in self.enemies:
                        if e.alive and e.state not in ("down", "fly") and self.cam - 10 < e.x < self.cam + W + 10:
                            self.damage_enemy(e, 12, knock=(k == 2), d=1 if e.x > p.x else -1)
                    if self.boss is not None:
                        self.boss_hit(16, True, self.boss["x"], self.boss["y"] - self.boss["z"] - 40)
                    self.sfx("punch")
            if p.st > 1.6:
                p.state = "idle"
        elif s == "hit":
            if p.st > 0.28:
                p.state = "idle"
        elif s == "fly":
            p.z += p.vz * dt
            p.vz -= GRAV * dt
            p.x += p.vx * dt
            if p.z <= 0:
                p.z = 0.0
                p.state, p.st = "down", 0.0
                self.sfx("thud")
        elif s == "down":
            if p.st > 1.0:
                if p.hp <= 0:
                    p.lives -= 1
                    if p.lives <= 0:
                        self.resume_phase = self.phase
                        self.set_phase("continue")
                        return
                    p.hp = MAX_HP
                    p.inv = 2.5
                p.state, p.st = "getup", 0.0
        elif s == "getup":
            if p.st > 0.35:
                p.state = "idle"
                p.inv = max(p.inv, 1.0)
        p.x = max(self.lo(), min(self.hi(), p.x))
        p.y = max(TOP, min(BOTTOM, p.y))

    def try_grab(self):
        p = self.p
        for e in self.enemies:
            if e.state == "dazed" and abs(e.y - p.y) < 8 and 0 < (e.x - p.x) * p.face < 26:
                p.state, p.st, p.held, p.knees = "grab", 0.0, e, 0
                e.state, e.st = "held", 0.0
                self.sfx("grab")
                return

    def resolve_attack(self, reach, dmg, knock, snd, d, air=False, downed=False, both=False, radius=False):
        p = self.p
        hit_any = False
        for e in self.enemies:
            if not e.alive or e.id in p.hit_ids or e.state in ("fly", "held") and e is not p.held:
                continue
            if e.state == "down" and not downed:
                continue
            if e.state != "down" and downed is False and e.z > 26:
                continue
            dy = abs(e.y - p.y)
            dx = (e.x - p.x) * d
            if radius:
                ok = dy <= 14 and abs(e.x - p.x) <= reach
            elif both:
                ok = dy <= 10 and abs(e.x - p.x) <= reach
            else:
                ok = dy <= 9 and 0 < dx <= reach
            if p.held is e:
                ok = p.move == "knee"
            if ok:
                p.hit_ids.add(e.id)
                self.damage_enemy(e, dmg, knock, 1 if e.x > p.x else -1)
                hit_any = True
                self.fx.append(["spark", e.x, e.y - 30 - e.z, 0.12, knock])
        b = self.boss
        if b is not None and b["hp"] > 0 and -2 not in p.hit_ids and self.phase == "boss":
            dy = abs(b["y"] - p.y)
            dx = (b["x"] - p.x) * d
            if dy <= 12 and (-10 < dx <= reach + 22 or radius and abs(b["x"] - p.x) < reach + 20):
                if self.boss_hit(dmg, air or p.z > 10, b["x"] - d * 14, b["y"] - b["z"] - 40):
                    p.hit_ids.add(-2)
                    hit_any = True
        if hit_any:
            self.sfx(snd)
            p.combo_t = 0.0
            if p.move == "swing" and p.weapon is not None:
                p.weapon["uses"] -= 1
                if p.weapon["uses"] <= 0:
                    p.weapon = None
        return hit_any

    def damage_enemy(self, e, dmg, knock, d, gain=True):
        e.hp -= dmg
        e.flash = 0.08
        self.score += dmg * 10
        if gain and self.p.state not in ("special", "flurry"):
            self.p.meter = min(3.0, self.p.meter + 0.07)
        e.recent = [t for t in e.recent if self.time - t < 1.2] + [self.time]
        e.attacking = False
        if e is self.p.held and not knock and e.hp > 0:
            return
        if knock or e.hp <= 0:
            e.state, e.st = "fly", 0.0
            e.vx, e.vz = d * 90.0, 150.0
            e.z = max(e.z, 2.0)
        elif len(e.recent) >= 3:
            e.state, e.st = "dazed", 0.0
            e.recent = []
            e.x += d * 3
        else:
            e.state, e.st = "hurt", 0.0
            e.x += d * 4

    def hurt_player(self, dmg, from_x, knock=False):
        p = self.p
        if p.inv > 0 or p.state in ("down", "fly", "getup", "cut"):
            return
        p.hp = max(0, p.hp - dmg)
        p.meter = min(3.0, p.meter + 0.06)
        p.flash = 0.1
        p.recent = [t for t in p.recent if self.time - t < 1.0] + [self.time]
        if p.held is not None:
            p.held.state, p.held.st = "idle", 0.0
            p.held = None
        p.move, p.air = None, None
        self.sfx("hurt")
        d = 1 if p.x > from_x else -1
        if knock or p.hp <= 0 or len(p.recent) >= 3:
            p.state, p.st = "fly", 0.0
            p.vx, p.vz, p.z = d * 80.0, 140.0, max(p.z, 2.0)
            p.inv = 0.0
            p.recent = []
        else:
            p.state, p.st = "hit", 0.0
            p.x += d * 4

    def update_enemy(self, e, dt):
        e.st += dt
        e.flash = max(0.0, e.flash - dt)
        p = self.p
        s = e.state
        if s == "out":
            return
        if s == "fly":
            e.z += e.vz * dt
            e.vz -= GRAV * dt
            e.x += e.vx * dt
            if e.thrown:                      # a thrown enemy bowls over the others
                for o in self.enemies:
                    if o is not e and o.alive and o.state not in ("fly", "down") and abs(o.y - e.y) < 11 and abs(o.x - e.x) < 14:
                        self.damage_enemy(o, 14, True, 1 if e.vx > 0 else -1)
                        self.sfx("thud")
            if e.z <= 0:
                e.z = 0.0
                e.thrown = False
                if e.hp <= 0:
                    e.state, e.st = "out", 0.0
                    self.score += e.points
                    self.fx.append(["ko", e.x, e.y, 0.9, False])
                else:
                    e.state, e.st = "down", 0.0
                self.sfx("thud")
            e.x = max(self.lo() - 30, min(self.hi() + 30, e.x))
            return
        if s == "down":
            if e.st > 0.8:
                e.state, e.st = "getup", 0.0
            return
        if s == "getup":
            if e.st > 0.35:
                e.state, e.st = "idle", 0.0
                e.cool = 0.6
            return
        if s in ("hurt",):
            if e.st > 0.3:
                e.state, e.st = "idle", 0.0
            return
        if s == "dazed":
            if e.st > 1.4:
                e.state, e.st = "idle", 0.0
            return
        if s in ("held", "bitten"):
            if s == "bitten" and e.st > 0.9:
                e.state, e.st = "idle", 0.0
            return
        e.cool -= dt
        if p.state in ("down", "fly", "cut") or self.phase not in ("fight", "elevator", "boss", "walk", "mask_off"):
            e.state = "idle"
            return
        if s == "attack":
            if e.st >= 0.28 and not getattr(e, "swung", False):
                e.swung = True
                if e.kind == "butler" and abs(e.x - p.x) > 40:
                    self.projs.append({"kind": "tray", "x": e.x + e.face * 10, "y": e.y, "z": 24.0, "vx": e.face * 160.0,
                                       "vz": 0.0, "g": 0.0, "dmg": e.dmg + 2, "owner": "enemy"})
                    self.sfx("throw")
                elif abs(e.y - p.y) <= 8 and 0 < (p.x - e.x) * e.face <= e.reach + 4 and p.z < 20:
                    self.hurt_player(e.dmg, e.x, knock=(e.kind == "security" and self.rng.random() < 0.25))
            if e.st >= 0.5:
                e.state, e.st = "idle", 0.0
                e.swung = False
                e.attacking = False
                e.cool = e.cool_max * self.rng.uniform(0.8, 1.3)
            return
        attackers = sum(1 for o in self.enemies if o.attacking and o is not e)
        side = 1 if e.x > p.x else -1
        e.face = -side
        ranged = e.kind == "butler" and abs(e.x - p.x) > 50
        if e.attacking or attackers < 2:
            e.attacking = True
            tx = p.x + side * (e.reach - 2)
            if e.kind == "butler" and e.hp > 0 and (e.id % 2 == 0):
                tx = p.x + side * 90
        else:
            tx = p.x + side * 70
        if not (self.lo() < tx < self.hi()):        # stay where Quick can reach: never stand off screen
            tx = p.x - side * (e.reach - 2 if e.attacking else 70)
        tx = max(self.lo() + 8, min(self.hi() - 8, tx))
        ty = p.y
        dx, dy = tx - e.x, ty - e.y
        moving = abs(dx) > 3 or abs(dy) > 2
        if moving:
            e.x += max(-e.speed * dt, min(e.speed * dt, dx))
            e.y += max(-e.speed * 0.7 * dt, min(e.speed * 0.7 * dt, dy))
            e.anim += dt
            e.state = "walk"
        else:
            e.state = "idle"
        aligned = abs(e.y - p.y) <= 6
        if e.attacking and e.cool <= 0 and aligned and (abs(e.x - p.x) <= e.reach + 4 or ranged and e.id % 2 == 0):
            e.state, e.st = "attack", 0.0
            e.swung = False
        e.y = max(TOP, min(BOTTOM, e.y))

    def update_projs(self, dt):
        p = self.p
        for pr in self.projs:
            pr["x"] += pr["vx"] * dt
            pr["vz"] -= pr["g"] * dt
            pr["z"] += pr["vz"] * dt
            if "spin" in pr:
                pr["spin"] += dt * 900
            if pr["owner"] == "enemy":
                if abs(pr["x"] - p.x) < 9 and abs(pr["y"] - p.y) < 8 and abs(pr["z"] - (p.z + 22)) < 20:
                    if p.inv <= 0 and p.state not in ("down", "fly", "dodge"):
                        self.hurt_player(pr["dmg"], pr["x"] - pr["vx"])
                        pr["dead"] = True
            else:
                for e in self.enemies:
                    if e.alive and e.state not in ("down", "fly") and abs(pr["x"] - e.x) < 11 and abs(pr["y"] - e.y) < 9:
                        self.damage_enemy(e, pr["dmg"], True, 1 if pr["vx"] > 0 else -1)
                        self.sfx("bonk")
                        pr["dead"] = True
                        break
                if not pr.get("dead") and self.boss is not None and self.boss["hp"] > 0:
                    b = self.boss
                    if abs(pr["x"] - b["x"]) < 26 and abs(pr["y"] - b["y"]) < 12:
                        self.boss_hit(pr["dmg"], True, pr["x"], b["y"] - b["z"] - 40)
                        pr["dead"] = True
            if pr["z"] <= 0:
                pr["dead"] = True
                if pr["owner"] == "player":
                    self.weapons.append({"x": pr["x"], "y": pr["y"], "kind": pr["kind"]})
        lo, hi = self.lo() - 40, self.hi() + 40
        self.projs = [pr for pr in self.projs if not pr.get("dead") and lo < pr["x"] < hi]

    def check_pickups(self):
        p, tk = self.p, self.token
        if tk is not None and abs(tk["x"] - p.x) < 14 and abs(tk["y"] - p.y) < 10 and p.z < 20:
            self.token = None
            self.summon_mazee()
        if tk is not None:
            tk["t"] += 1 / 60.0

    # ------------------------------------------------------------ Mazee
    def summon_mazee(self):
        p = self.p
        self.mazee = {"x": self.cam - 30, "y": p.y + 8, "state": "enter", "t": 15.0, "st": 0.0, "face": 1,
                      "target": None, "anim": 0.0, "fling": None}
        self.sfx("bark")
        self.sfx("powerup")
        self.bubble("Hey Mazee!", p.x, p.y - 64, 1.6)
        self.fx.append(["fence", self.cam + 8, p.y, 0.5, False])

    def mazee_leave(self, silent=False):
        m = self.mazee
        if m is None or m["state"] == "leave":
            return
        m["state"], m["st"] = "leave", 0.0
        if not silent:
            self.bubble("Thanks for the assist, Mazee! Good girl!", self.p.x, self.p.y - 64, 2.4)
            self.sfx("bark")
        else:
            self.mazee = None

    def team_attack(self):
        m = self.mazee
        targets = [e for e in self.enemies if e.alive and e.state not in ("fly", "down")]
        if not targets:
            return
        e = min(targets, key=lambda o: abs(o.x - m["x"]) + abs(o.y - m["y"]))
        m["state"], m["st"], m["fling"] = "fetch", 0.0, e
        e.state, e.st = "held", 0.0
        self.bubble("Fetch, Mazee!", self.p.x, self.p.y - 64, 1.2)
        self.sfx("bark")

    def update_mazee(self, dt):
        m = self.mazee
        if m is None:
            return
        p = self.p
        m["st"] += dt
        m["anim"] += dt
        if m["state"] == "leave":
            m["x"] -= 220 * dt
            m["face"] = -1
            if m["x"] < self.cam - 60:
                self.mazee = None
            return
        if m["state"] != "fetch":
            m["t"] -= dt
            if m["t"] <= 0:
                self.mazee_leave()
                return
        if m["state"] == "enter":
            m["x"] += 260 * dt
            if m["x"] > p.x - 40:
                m["state"] = "fight"
            return
        if m["state"] == "fetch":              # Fetch and Fling
            e = m["fling"]
            if not e.alive:
                m["state"] = "fight"
                return
            tx = p.x + p.face * 22
            e.x += (tx - e.x) * min(1.0, dt * 6)
            e.y += (p.y - e.y) * min(1.0, dt * 6)
            m["x"], m["y"], m["face"] = e.x - 14 * (1 if tx > e.x else -1), e.y + 2, 1 if tx > e.x else -1
            if m["st"] > 0.6:
                p.state, p.st, p.move = "atk", 0.0, "spin"
                p.hit_ids = {e.id, -1}
                self.launch(e, p.face, 260.0, 20)
                self.fx.append(["spark", e.x, e.y - 30, 0.2, True])
                self.sfx("kick")
                self.score += 1000
                m["state"] = "fight"
                m["t"] = min(m["t"], 0.8)
            return
        targets = [e for e in self.enemies if e.alive and e.state not in ("fly", "down", "held")]
        if not targets:
            tx, ty = p.x - 36 * p.face, p.y + 6
            m["x"] += max(-150 * dt, min(150 * dt, tx - m["x"]))
            m["y"] += max(-80 * dt, min(80 * dt, ty - m["y"]))
            m["face"] = p.face
            return
        e = min(targets, key=lambda o: abs(o.x - m["x"]) + abs(o.y - m["y"]))
        dx, dy = e.x - m["x"], e.y - m["y"]
        m["face"] = 1 if dx > 0 else -1
        if abs(dx) > 16 or abs(dy) > 5:
            m["x"] += max(-170 * dt, min(170 * dt, dx - m["face"] * 12))
            m["y"] += max(-100 * dt, min(100 * dt, dy))
        elif m["st"] > 0.5:
            m["st"] = 0.0
            e.state, e.st = "bitten", 0.0
            e.hp -= 5
            e.flash = 0.08
            self.score += 50
            self.p.meter = min(3.0, self.p.meter + 0.03)
            self.sfx("bark" if self.rng.random() < 0.3 else "punch")
            if e.hp <= 0:
                self.damage_enemy(e, 0, True, m["face"])

    def bubble(self, msg, x, y, t):
        self.bubbles.append([msg, (x, y), t])

    # ------------------------------------------------------------ drawing
    def draw_title_art(self, surf):
        art.street(surf, 980 + math.sin(self.time * 0.3) * 20, self.time)
        big = pygame.transform.scale(art.portrait(True), (120, 120))
        surf.blit(big, (W - 126, H - 126))
        pygame.draw.rect(surf, art.BLUE[2], (W - 126, H - 126, 120, 120), 2)

    def draw(self, surf):
        sc = self.scene
        if self.phase == "reform":
            self.draw_reform(surf)
            return
        if sc in ("street", "lobby"):
            (art.street if sc == "street" else art.lobby)(surf, self.cam, self.time)
        elif sc == "elevator":
            art.elevator(surf, self.floor, self.time, self.doors)
        else:
            vault = 1.0 if (self.phase in ("katana",) and self.pt > 3.0) else 0.0
            art.penthouse(surf, self.time, vault)
        if self.phase == "katana":
            self.draw_katana(surf)
        else:
            self.draw_world(surf)
        if self.phase in ("intro", "boss_intro"):
            self.draw_talk(surf)
        if self.phase not in ("intro", "katana", "complete"):
            self.draw_hud(surf)
        if self.go_t > 0 and int(self.time * 3) % 2 == 0 and self.phase in ("walk", "mask_off"):
            art.say(surf, "GO", (W - 34, 96), 22, (255, 220, 80))
            pygame.draw.polygon(surf, (255, 220, 80), [(W - 20, 98), (W - 10, 104), (W - 20, 110)])
        if self.phase == "continue":
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 150))
            surf.blit(shade, (0, 0))
            art.say(surf, "CONTINUE?", (W // 2, 80), 36, (255, 220, 80))
            art.say(surf, str(max(0, 9 - int(self.pt))), (W // 2, 116), 40, (255, 255, 255))
            art.say(surf, "Big button: keep fighting", (W // 2, 160), 18, (220, 220, 235))
        if self.phase == "complete":
            art.say(surf, "LEVEL 1 COMPLETE", (W // 2, 90), 34, (255, 220, 80))
            art.say(surf, "Tower Row: Fair Tax Act", (W // 2, 128), 20, (255, 255, 255))
        if self.fade > 0:
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, int(255 * min(1.0, self.fade / 0.6))))
            surf.blit(shade, (0, 0))

    def sprite_for(self, p):
        s = p.state
        if s == "cut":
            return art.hero("idle0", p.masked, p.face)
        if self.phase in ("mask_on", "mask_off"):
            seq = ["idle0", "mask1", "mask2", "mask2", "idle0"]
            k = min(4, int(self.pt / 0.12))
            if self.phase == "mask_off":
                k = 4 - k
            return art.hero(seq[k], k >= 3, p.face)
        pose = "idle0"
        if s == "idle":
            pose = "idle0" if int(p.anim * 3) % 2 == 0 else "idle1"
        elif s == "walk":
            pose = "walk%d" % (int(p.anim * 8) % 4)
        elif s == "atk":
            pose = MOVES[p.move][7] if p.move else "idle0"
        elif s == "jump":
            pose = {"kick": "jumpk", "elbow": "elbow"}.get(p.air, "tuck")
        elif s in ("hit",):
            pose = "hit"
        elif s in ("fly", "down"):
            return art.lying(art.hero("hit", p.masked, p.face))
        elif s == "getup":
            pose = "getup"
        elif s == "grab":
            pose = "grab"
        elif s == "throw":
            pose = "throw"
        elif s == "dodge":
            pose = "dodge"
        elif s == "special":
            return art.hero("spin", p.masked, 1 if int(p.st * 14) % 2 == 0 else -1)
        elif s == "flurry":
            pose = ("jab", "cross", "kick", "round", "upper", "spin")[int(p.st * 12) % 6]
        return art.hero(pose, p.masked, p.face)

    def blit_fighter(self, surf, img, x, y, z, face):
        ax = art.HX + 1 if face > 0 else img.get_width() - 2 - art.HX
        if img.get_width() > 70:        # lying down: centered
            surf.blit(img, (int(x - img.get_width() / 2), int(y - z - img.get_height() + 4)))
            return
        surf.blit(img, (int(x - ax), int(y - z - (art.FEET_Y + 1))))

    def enemy_sprite(self, e):
        s = e.state
        if e.kind == "butler":
            img = art.butler(int(e.anim * 8), e.face, s == "attack")
            if s in ("fly", "down", "out"):
                img = art.lying(img)
            return img
        if s in ("fly", "down", "out"):
            return art.lying(art.goon(e.kind, "hit", e.face))
        pose = {"walk": "walk%d" % (int(e.anim * 8) % 4), "attack": "jab" if e.st > 0.15 else "idle1",
                "hurt": "hit", "dazed": "idle1", "held": "hit", "bitten": "hit", "getup": "getup"}.get(s, "idle0")
        return art.goon(e.kind, pose, e.face)

    def draw_world(self, surf):
        cam = int(self.cam) if self.scene_i < 2 else 0
        items = []
        for w in self.weapons:
            items.append((w["y"], 0, "weapon", w))
        if self.token is not None:
            items.append((self.token["y"], 1, "token", self.token))
        for e in self.enemies:
            items.append((e.y, 2, "enemy", e))
        if self.mazee is not None:
            items.append((self.mazee["y"], 3, "mazee", self.mazee))
        items.append((self.p.y, 4, "hero", self.p))
        if self.boss is not None and self.phase in ("boss", "boss_intro"):
            items.append((self.boss["y"], 1, "boss", self.boss))
        items.sort(key=lambda it: (it[0], it[1]))
        for _, _, kind, o in items:
            if kind == "weapon":
                surf.blit(art.weapon_img(o["kind"]), (int(o["x"] - cam - 12), int(o["y"] - 4)))
            elif kind == "token":
                art.shadow(surf, o["x"] - cam, o["y"], 18)
                surf.blit(art.token(o["t"]), (int(o["x"] - cam - 12), int(o["y"] - 30 + math.sin(o["t"] * 3) * 3)))
            elif kind == "enemy":
                if not o.alive and int(o.st * 12) % 2:
                    continue
                art.shadow(surf, o.x - cam, o.y)
                img = self.enemy_sprite(o)
                if o.flash > 0:
                    img = art.white(img)
                self.blit_fighter(surf, img, o.x - cam, o.y, o.z, o.face)
                if o.state == "dazed":
                    art.stars(surf, o.x - cam, o.y - 52, self.time)
            elif kind == "mazee":
                img = art.mazee(int(o["anim"] * 10), o["face"], o["state"] in ("fight", "fetch"))
                art.shadow(surf, o["x"] - cam, o["y"], 40)
                surf.blit(img, (int(o["x"] - cam - img.get_width() / 2), int(o["y"] - img.get_height() + 3)))
            elif kind == "boss":
                img = art.trillion_heir(self.time, o["state"] == "tired", o["hat"])
                if o["flash"] > 0:
                    img = art.white(img)
                art.shadow(surf, o["x"], o["y"], 56)
                surf.blit(img, (int(o["x"] - img.get_width() / 2), int(o["y"] - o["z"] - img.get_height() + 10)))
            else:
                p = o
                if p.inv > 0 and int(self.time * 16) % 2 and p.state not in ("special", "flurry", "dodge"):
                    continue
                art.shadow(surf, p.x - cam, p.y)
                img = self.sprite_for(p)
                if p.flash > 0:
                    img = art.white(img)
                self.blit_fighter(surf, img, p.x - cam, p.y, p.z, p.face)
                if p.weapon is not None and p.state not in ("fly", "down"):
                    ang = 300 if p.state == "atk" and p.move == "swing" and p.st > 0.08 else 45
                    wimg = art.weapon_img(p.weapon["kind"], ang if p.face > 0 else 180 - ang)
                    surf.blit(wimg, (int(p.x - cam + p.face * 10 - wimg.get_width() / 2), int(p.y - p.z - 32)))
                if p.state == "special":
                    pygame.draw.circle(surf, art.BLUE[2], (int(p.x - cam), int(p.y - 22)), 24 + int(p.st * 30) % 8, 2)
                if p.state == "flurry" and int(p.st * 20) % 2:
                    flash = pygame.Surface((W, H), pygame.SRCALPHA)
                    flash.fill((120, 200, 255, 50))
                    surf.blit(flash, (0, 0))
        for pr in self.projs:
            x, y = int(pr["x"] - cam), int(pr["y"] - pr["z"])
            art.shadow(surf, pr["x"] - cam, pr["y"], 10)
            if pr["kind"] == "coin":
                surf.blit(art.coin(), (x - 4, y - 4))
            elif pr["kind"] == "tray":
                surf.blit(art.tray(), (x - 6, y - 3))
            else:
                img = art.weapon_img(pr["kind"], pr.get("spin", 0))
                surf.blit(img, (x - img.get_width() // 2, y - img.get_height() // 2))
        for kind, x, y, t, big in self.fx:
            if kind == "spark":
                art.spark(surf, x - cam, y, big)
            elif kind == "ko":
                art.stars(surf, x - cam, y - 14, self.time)
            elif kind == "fence":
                for k in range(8):
                    surf.fill((150, 154, 166), (int(x - cam + k * 5 + (0.5 - t) * 80), int(y - 30 - k * 3), 3, 2))
        for msg, (x, y), t in self.bubbles:
            art.bubble(surf, msg, x - cam, y)

    def draw_talk(self, surf):
        if self.talk_i >= len(self.talk):
            return
        who, masked, line = self.talk[self.talk_i]
        box = pygame.Rect(4, 150, 392, 86)
        pygame.draw.rect(surf, art.OUT, box)
        pygame.draw.rect(surf, (24, 22, 40), box.inflate(-4, -4))
        pygame.draw.rect(surf, art.BLUE[1], box.inflate(-4, -4), 1)
        img = art.heir_portrait() if masked is None else art.portrait(masked)
        surf.blit(pygame.transform.scale(img, (78, 78)), (8, 154))
        pygame.draw.rect(surf, art.GOLD[2] if masked is None else art.BLUE[2], (8, 154, 78, 78), 1)
        art.say(surf, who, (94, 156), 18, art.GOLD[2] if masked is None else (255, 220, 80), center=False)
        shown = line[:int(self.pt * 45)]
        words, lines, cur = shown.split(" "), [], ""
        for w_ in words:
            if art.font(16).size(cur + " " + w_)[0] > 290:
                lines.append(cur)
                cur = w_
            else:
                cur = (cur + " " + w_).strip()
        lines.append(cur)
        for i, ln in enumerate(lines[:3]):
            surf.blit(art.font(16).render(ln, False, (240, 240, 250)), (94, 176 + i * 15))
        if self.pt * 45 >= len(line) and int(self.time * 2) % 2 == 0:
            pygame.draw.polygon(surf, (255, 220, 80), [(380, 222), (388, 222), (384, 228)])

    def draw_hud(self, surf):
        p = self.p
        key = ("hudp", p.masked)
        small = art._cache.get(key)
        if small is None:
            small = art._cache[key] = pygame.transform.smoothscale(art.portrait(p.masked), (24, 24))
        box = pygame.Rect(4, 4, 24, 24)
        pygame.draw.rect(surf, art.OUT, box.inflate(2, 2))
        surf.blit(small, box)
        pygame.draw.rect(surf, art.BLUE[2], box, 1)
        art.say(surf, "QUICK x%d" % max(0, p.lives), (32, 2), 14, (240, 240, 250), center=False)
        segs = int(math.ceil(p.hp / 10.0))
        for i in range(10):
            r = pygame.Rect(32 + i * 7, 14, 6, 5)
            pygame.draw.rect(surf, art.OUT, r.inflate(2, 2))
            pygame.draw.rect(surf, art.BLUE[2] if i < segs else (40, 40, 60), r)
            if i < segs:
                pygame.draw.line(surf, art.BLUE[3], r.topleft, (r.right - 1, r.top))
        for i in range(3):
            r = pygame.Rect(32 + i * 23, 22, 21, 4)
            pygame.draw.rect(surf, art.OUT, r.inflate(2, 2))
            fill = max(0.0, min(1.0, p.meter - i))
            pygame.draw.rect(surf, (60, 50, 40), r)
            if fill > 0:
                glow = (255, 240, 160) if fill >= 1 and int(self.time * 6) % 2 else (255, 210, 120)
                pygame.draw.rect(surf, glow, (r.x, r.y, int(r.w * fill), r.h))
        art.say(surf, "%07d" % int(self.score), (W // 2, 2), 18, (255, 255, 255))
        label = {"street": "TOWER ROW", "lobby": "TRILLION TOWER LOBBY", "elevator": "THE GLASS ELEVATOR",
                 "penthouse": "THE PENTHOUSE"}[self.scene]
        art.say(surf, label, (W // 2, 18), 14, art.GOLD[2])
        m = self.mazee
        if m is not None and m["state"] != "leave":
            g = pygame.Rect(W - 28, 4, 24, 24)
            pygame.draw.rect(surf, art.OUT, g.inflate(2, 2))
            pygame.draw.rect(surf, (40, 40, 70), g)
            head = pygame.transform.scale(art.mazee(0), (40, 18))
            surf.blit(head, (g.x - 14, g.y + 4), area=pygame.Rect(14, 0, 24, 18))
            ring = max(0.0, m["t"] / 15.0)
            pygame.draw.arc(surf, art.BLUE[2], g.inflate(8, 8), math.pi / 2, math.pi / 2 + math.tau * ring, 2)
            art.say(surf, "MAZEE", (W - 66, 4), 14, (240, 240, 250), center=False)
        b = self.boss
        if b is not None and self.phase == "boss":
            art.say(surf, "THE TRILLION HEIR", (W // 2, 214), 14, art.GOLD[2])
            pygame.draw.rect(surf, art.OUT, (99, 227, 202, 8))
            pygame.draw.rect(surf, (70, 20, 30), (100, 228, 200, 6))
            pygame.draw.rect(surf, art.GOLD[2], (100, 228, int(200 * b["hp"] / b["max"]), 6))

    def draw_katana(self, surf):
        t, p, b = self.pt, self.p, self.boss
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((6, 8, 30, int(min(150, t * 160)) if t < 6.5 else int(max(0, 150 - (t - 6.5) * 150))))
        surf.blit(dim, (0, 0))
        img = art.trillion_heir(self.time, True, b["hat"])
        art.shadow(surf, b["x"], b["y"], 56)
        surf.blit(img, (int(b["x"] - img.get_width() / 2), int(b["y"] - b["z"] - img.get_height() + 10)))
        rx, ry = 120, 160
        if t < 6.0:
            size = min(1.0, t)
        elif t < 6.4:
            size = (t - 6.0) / 0.4
        else:
            size = max(0.0, 1 - (t - 6.4) / 0.5)
        if t < 2.6 or 6.0 <= t < 6.9:
            art.rift(surf, rx, ry, size, self.time)
        pose = "idle0"
        if 1.0 <= t < 2.6:
            pose = "draw"
        elif 2.6 <= t < 6.0:
            pose = "strike"
        elif 6.0 <= t < 6.8:
            pose = "draw"
        elif t >= 7.6:
            pose = "victory"
        vic = art.hero(pose, p.masked, p.face)
        art.shadow(surf, p.x, p.y)
        self.blit_fighter(surf, vic, p.x, p.y, 0, p.face)
        if 1.2 <= t < 2.6:
            grow = min(1.0, (t - 1.2) / 0.8)
            art.katana(surf, (p.x - 10, p.y - 36), math.radians(200 - 40 * grow), 14 + 30 * grow)
        elif 2.6 <= t < 6.0:
            art.katana(surf, (p.x + 14, p.y - 30), math.radians(-10), 44)
        if 1.2 <= t < 2.6:              # close-up: the masked portrait, lenses blazing
            k = min(1.0, (t - 1.2) / 0.25)
            px_ = int(-150 + 160 * k)
            panel = pygame.Rect(px_, 30, 150, 110)
            pygame.draw.rect(surf, art.OUT, panel.inflate(4, 4))
            surf.blit(pygame.transform.scale(art.portrait(True), (150, 150)), panel.topleft, area=pygame.Rect(0, 20, 150, 110))
            pygame.draw.rect(surf, art.BLUE[2], panel, 2)
            art.say(surf, "DAYBREAK", (px_ + 236, 70), 34, art.BLUE[3])
        if 2.9 <= t < 3.4:              # the strike: a white flash and one long cut across the vault chain
            a = int(255 * (1 - (t - 2.9) / 0.5))
            flash = pygame.Surface((W, H), pygame.SRCALPHA)
            flash.fill((255, 255, 255, a))
            surf.blit(flash, (0, 0))
            pygame.draw.line(surf, art.BLUE[3], (40, 120), (380, 60), 3)
        if 3.4 <= t < 6.5:              # gold pours from the vault down to the city
            for k in range(40):
                ct = (t - 3.4) * 1.3 + k * 0.08
                cx = 316 + math.sin(k * 1.7) * 30 + ct * 18
                cy = 86 + (ct % 2.0) * 90
                if cy < 236:
                    surf.blit(art.coin(), (int(cx), int(cy)))
            if t > 4.0:
                art.say(surf, "To the schools!", (316, 18), 16, art.GOLD[3])
        for msg, (x, y), tt in self.bubbles:
            art.bubble(surf, msg, x, y)
        if t > 8.4:
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, int(min(255, (t - 8.4) * 320))))
            surf.blit(shade, (0, 0))

    def draw_reform(self, surf):
        t = self.pt
        if t < 3.5:
            art.street(surf, 1060, self.time)
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 160))
            surf.blit(shade, (0, 0))
            art.newspaper(surf, ["FAIR TAX ACT", "PASSES"], "Largest fortunes finally pay their share", t)
            return
        k = t - 3.5
        cam = 120 + k * 40
        art.street(surf, cam, self.time, morning=True)
        art.bus(surf, int(-90 + k * 70) % 560 - 80, 166)
        for i in range(5):
            x = (i * 97 + k * (25 + i * 6)) % (W + 60) - 30
            y = 186 + (i * 13) % 40
            art.shadow(surf, x, y)
            img = art.citizen(i, "walk%d" % (int(k * 8 + i) % 4), 1)
            surf.blit(img, (int(x - art.HX - 1), int(y - art.FEET_Y - 1)))
        vic = art.hero("victory" if int(k) % 4 == 0 else "idle0", False, 1)
        art.shadow(surf, 200, 212)
        surf.blit(vic, (200 - art.HX - 1, 212 - art.FEET_Y - 1))
        box = pygame.Rect(30, 18, W - 60, 40)
        pygame.draw.rect(surf, art.OUT, box.inflate(2, 2), border_radius=4)
        pygame.draw.rect(surf, (250, 246, 236), box, border_radius=4)
        art.say(surf, "Schools repaired. New buses.", (W // 2, 22), 18, (40, 40, 60), outline=(250, 246, 236))
        art.say(surf, "The library stays open late.", (W // 2, 38), 18, (40, 40, 60), outline=(250, 246, 236))


def make(**kw):
    return BlackWarrior(**kw)


if __name__ == "__main__":
    c.main(make)
