"""Black Warrior: a Double Dragon style beat 'em up in six levels.

Quick walks the city with his face showing; when a fight starts he pulls on his
cat mask. Each level takes on one wrong in the city: Tower Row (the Trillion
Heir), Mercy General (the Capitalist Pig), the Gig Docks (Mister Poverty), the
Old Ward (Madame Eviction), Smokestack Bend (Baron Smog) and City Hall (the Big
Lie). Each has a set piece, a tag team guest, a boss and a katana finish from
the Ninth Dominion, and each win changes the city.

    D-pad              walk anywhere on the street; tap left or right twice to dodge
    Triangle (B)       punch combo; pick up a weapon, swing it
    Big circle (A)     kick combo; throw a held weapon or a grabbed enemy
    A and B together   jump (then A flying kick, B diving elbow)
    Hold A and B       charge a special, one stage per full meter bar; let go to fire:
                         1 bar  Sky Pound: leap off the top of the screen, crash down fist first
                         2 bars Blue Roar: a roar and a blue discharge rippling out from Quick
                         3 bars Crimson Cyclone: a humming red katana spin through the crowd
    B behind you       back elbow (hold away from the enemy)
    Mixed combos       B B A rising knee, A A B hammer fist, B A B cat claw, A B A tail sweep;
                       B during a dodge pounces
    Walk into a dazed enemy to grab: B knees, A throws
    Hold B one second while a guest is here: their team attack
    Small circle       pause; skips a cutscene you have already seen

Enemies are knocked out with stars over their heads, never hurt for real.
All art, sounds and music are original to this project.
"""
import math

import pygame

from . import bw_art as art
from . import bw_bosses as bosses
from . import bw_cast as cast
from . import bw_fx as fx
from . import bw_guests as guests
from . import bw_stages as stages
from . import common as c
from .bw_levels import ENEMY, GUEST_ORDER, GUESTS, LEVELS
from .common import H, W, Game

GRAV = 620.0
JUMP_V = 236.0
TOP, BOTTOM = art.FLOOR_TOP + 6, art.FLOOR_BOTTOM - 2
MAX_HP = 100
UNLOCK_KEY = "black_warrior_level"
SEEN_KEY = "black_warrior_seen_l%d"

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
    # mixed-button finishers
    "launch": (0.34, 0.07, 0.17, 26, 12, True, "kick", "knee"),
    "hammer": (0.38, 0.14, 0.24, 26, 14, True, "thud", "elbow"),
    "claw": (0.32, 0.05, 0.24, 28, 7, False, "punch", "cross"),
    "tail": (0.40, 0.10, 0.26, 34, 11, True, "kick", "round"),
    "pounce": (0.32, 0.04, 0.20, 32, 12, True, "punch", "jab"),
}
# Mix punches (B) and kicks (A) for a finisher: the last three presses pick it.
MIXES = {
    ("b", "b", "a"): ("launch", "RISING KNEE"),
    ("a", "a", "b"): ("hammer", "HAMMER FIST"),
    ("b", "a", "b"): ("claw", "CAT CLAW"),
    ("a", "b", "a"): ("tail", "TAIL SWEEP"),
}
MIX_GAP = 0.6             # most time allowed between presses in a mix
B_COMBO = ("jab", "cross", "upper")
A_COMBO = ("kick", "round", "spin")
CUT_PHASES = ("katana", "reform", "ending")
SPECIALS = ("special", "flurry", "charge", "skypound", "roar", "cyclone")
CHARGE_START = 0.3        # hold A+B this long to start charging (a quick tap is a jump)
CHARGE_STEP = 0.6         # each further stage takes this long
SKY = {"crouch": 0.14, "up": 0.46, "hang": 0.74, "hit": 0.9, "end": 1.25, "top": 230.0}
ROAR = {"blast": 0.38, "speed": 330.0, "reach": 210.0, "end": 1.4}
CYC = {"spin": 0.32, "stop": 1.62, "end": 1.95, "tick": 0.13, "reach": 48}
PLAY_PHASES = ("walk", "fight", "ride", "boss", "mask_off")


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
        hp, self.speed, self.reach, self.dmg, self.cool_max, self.points, self.style = ENEMY[kind]
        self.hp = self.max_hp = hp
        self.cool = 0.8
        self.recent = []
        self.thrown = False
        self.attacking = False
        self.swung = False
        self.riding = False
        if self.style == "flyer":
            self.z = 22.0
        elif self.style == "puff":
            self.z = 6.0

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
        self.seq, self.seq_t = [], -9.0
        self.charge = 0
        self.target = None
        self.tick = 0.0


class BlackWarrior(Game):
    name = "black_warrior"
    title = "Black Warrior"
    title_color = (79, 180, 255)
    help_lines = ("Triangle: punch   Big button: kick", "Both together: jump (hold: special)",
                  "Tap a direction twice: dodge", "Right the wrongs.")

    @property
    def music(self):
        ph = getattr(self, "phase", "")
        if ph in ("boss", "boss_intro"):
            return "bw_boss"
        if ph in ("reform", "complete", "ending"):
            return "bw_reform"
        return "black_warrior"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.unlocked = max(1, min(len(LEVELS), int(c.load_scores(self.scores_path).get(UNLOCK_KEY, 1))))
        self.reset()

    # ------------------------------------------------------------ setup
    def reset(self):
        self.score = 0
        self.win = False
        self.p = Quick(60, 196)
        self.enemies, self.projs, self.fx, self.weapons, self.bubbles = [], [], [], [], []
        self.vfx, self.chips, self.shake = [], [], 0.0
        self.boss = None
        self.guest = None
        self.token = None
        self.crate = None
        self.chord = None
        self.pending = None
        self.b_hold = 0.0
        self.last_tap = {"left": -9.0, "right": -9.0}
        self.fade = 0.0
        self.go_t = 0.0
        self.scramble = 0.0
        self.debris = []
        self.resume_phase = "walk"
        self.choice = self.unlocked
        self.cam = 0.0
        self.prog = 0.0
        self.talk, self.talk_i = [], 0
        self.start_level(0)
        if self.unlocked > 1:
            self.phase, self.pt = "select", 0.0

    def start_level(self, i):
        self.level_i = i
        self.L = LEVELS[i]
        self.seen = bool(c.load_scores(self.scores_path).get(SEEN_KEY % self.L["n"], 0))
        self.p.hp = MAX_HP
        self.p.masked = False
        self.boss = None
        self.guest = None
        self.load_scene(0)
        self.talk, self.talk_i = self.L["intro"], 0
        self.set_phase("intro")

    def load_scene(self, i):
        self.scene_i = i
        self.sc = self.L["scenes"][i]
        self.enemies, self.projs, self.weapons, self.bubbles = [], [], [], []
        self.cam, self.prog, self.doors = 0.0, 0.0, 0.0
        self.stop_i, self.stop_spawned, self.belt = 0, False, 1
        self.debris = []
        self.vfx, self.chips = [], []
        self.zone = None
        self.token = None
        self.crate = None
        self.zones = []
        self.length = W
        if self.sc["kind"] == "walk":
            self.length = self.sc["length"]
            self.zones = [dict(z, done=False, wave=0) for z in self.sc["zones"]]
            self.weapons = [{"x": float(x), "y": float(y), "kind": k} for x, y, k in self.sc.get("weapons", [])]
            tk = self.sc.get("token")
            if tk and self.L["guest"]:
                self.token = {"x": float(tk[0]), "y": float(tk[1]), "t": 0.0, "guest": self.L["guest"]}
            cr = self.sc.get("crate")
            if cr and self.met_guests():
                self.crate = {"x": float(cr[0]), "y": float(cr[1]), "hp": 3}
        self.p.x, self.p.y, self.p.z = 40.0, 196.0, 0.0
        self.p.state, self.p.held = "idle", None

    def met_guests(self):
        return GUEST_ORDER[:min(self.level_i, len(GUEST_ORDER))]

    @property
    def scene(self):
        return self.sc["stage"]

    @property
    def fixed(self):
        return self.sc["kind"] != "walk"

    # ------------------------------------------------------------ frame
    def step(self, dt, inp):
        if self.state == "play" and getattr(self, "phase", "") in CUT_PHASES and "start" in inp.pressed and self.seen:
            inp.pressed.discard("start")
            self.skip_cutscene()
        super().step(dt, inp)

    def update(self, dt, inp):
        self.pt += dt
        self.fade = max(0.0, self.fade - dt)
        self.go_t = max(0.0, self.go_t - dt)
        self.scramble = max(0.0, self.scramble - dt)
        for f in self.fx:
            f[3] -= dt
        self.fx = [f for f in self.fx if f[3] > 0]
        self.shake = max(0.0, self.shake - dt)
        for v in self.vfx:
            v["t"] += dt
        self.vfx = [v for v in self.vfx if v["t"] < v["life"]]
        for d in self.chips:
            d[0] += d[3] * dt
            d[2] += d[4] * dt
            d[4] -= GRAV * dt
            d[5] += dt * 12
        self.chips = [d for d in self.chips if d[2] > -2]
        for b in self.bubbles:
            b[2] -= dt
        self.bubbles = [b for b in self.bubbles if b[2] > 0]
        getattr(self, "phase_" + self.phase)(dt, inp)

    def set_phase(self, ph):
        self.phase, self.pt = ph, 0.0
        if ph in ("boss", "reform", "ending", "intro"):
            self.sound.music(self.music)

    # ------------------------------------------------------------ select and story
    def phase_select(self, dt, inp):
        if "up" in inp.pressed and self.choice > 1:
            self.choice -= 1
            self.sfx("move")
        if "down" in inp.pressed and self.choice < self.unlocked:
            self.choice += 1
            self.sfx("move")
        if self.pt > 0.3 and ("a" in inp.pressed or "b" in inp.pressed):
            self.sfx("select")
            self.start_level(self.choice - 1)

    def phase_intro(self, dt, inp):
        self.talk_step(inp, lambda: self.set_phase("walk"))

    def talk_step(self, inp, done):
        if self.pt > 0.3 and ("a" in inp.pressed or "b" in inp.pressed):
            line = self.talk[self.talk_i][2]
            if self.pt * 45 < len(line):
                self.pt = 99.0
            else:
                self.talk_i += 1
                self.pt = 0.0
                self.sfx("move")
                if self.talk_i >= len(self.talk):
                    done()

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

    # ------------------------------------------------------------ walking scenes
    def phase_walk(self, dt, inp):
        self.update_world(dt, inp, control=True)
        if self.phase != "walk":
            return
        p = self.p
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

    def spawn(self, kind, x, y):
        e = Enemy(kind, x, y)
        self.enemies.append(e)
        return e

    def spawn_wave(self):
        z = self.zone
        for i, k in enumerate(z["waves"][z["wave"]]):
            side = 1 if i % 2 == 0 else -1
            x = self.cam + (W + 20 + i * 18 if side > 0 else -20 - i * 18)
            self.spawn(k, x, TOP + 10 + (i * 23) % (BOTTOM - TOP - 10))

    def next_scene(self):
        if self.guest is not None:
            self.guest.leave(self, silent=True)
            self.guest = None
        self.load_scene(self.scene_i + 1)
        self.fade = 0.6
        kind = self.sc["kind"]
        if kind == "walk":
            self.set_phase("walk")
        elif kind == "ride":
            self.p.x, self.p.y = W / 2, 200.0
            self.put_mask_on("ride")
        else:
            self.p.x, self.p.y = 90.0, 200.0
            self.boss = bosses.make(self.L["boss"])
            self.talk, self.talk_i = self.L["boss_talk"], 0
            self.p.masked = True
            self.set_phase("boss_intro")

    # ------------------------------------------------------------ set pieces
    def phase_ride(self, dt, inp):
        self.update_world(dt, inp, control=True)
        if self.phase != "ride":
            return
        self.ride_hazards(dt)
        b = self.boss
        if b is not None:
            if b.hp > 0:
                b.update(self, dt)
            else:
                self.fx.append(["ko", b.x, b.y, 0.9, False])
                self.score += 2000
                self.sfx("boom")
                self.boss = None
        stops = self.sc["stops"]
        end = self.sc["end"]
        target = stops[self.stop_i][0] if self.stop_i < len(stops) else end
        busy = any(e.alive for e in self.enemies) or self.boss is not None
        if self.prog < target:
            self.doors = max(0.0, self.doors - dt * 3)
            if self.doors <= 0 and not busy:
                self.prog = min(float(target), self.prog + dt * 6)
                if self.prog >= target:
                    self.sfx("ding")
                    if target == end:
                        self.next_scene()
                        return
        elif self.stop_i < len(stops):
            self.doors = min(1.0, self.doors + dt * 3)
            if self.doors >= 1.0 and not busy and not self.stop_spawned:
                for i, k in enumerate(stops[self.stop_i][1]):
                    if k.startswith("boss:"):
                        self.boss = bosses.make(k.split(":")[1], mini=True)
                        self.boss.x = W - 80
                        self.bubble("Rematch!", self.boss.x, 80, 1.2)
                    else:
                        x = 15 if i % 2 == 0 else W - 15
                        if self.scene == "ramp":
                            x = W + 30 + i * 40
                        e = self.spawn(k, x, TOP + 12 + i * 20)
                        e.riding = self.scene == "ramp"
                self.stop_spawned = True
            elif self.doors >= 1.0 and not busy and self.stop_spawned:
                self.stop_i += 1
                self.stop_spawned = False
                self.belt = -self.belt

    def ride_hazards(self, dt):
        p = self.p
        if self.scene == "conveyor":
            push = self.belt * 30 * dt
            if p.z <= 0 and p.state != "dodge":
                p.x += push
            for e in self.enemies:
                if e.alive and e.z <= 0:
                    e.x = max(self.lo() + 4, min(self.hi() - 4, e.x + push))
        elif self.scene == "scaffold":
            if self.rng.random() < dt * 0.7:
                self.debris.append([p.x + self.rng.uniform(-40, 40), p.y + self.rng.uniform(-10, 10), 0.0])
            for d in self.debris:
                d[2] += dt
                if 0.9 <= d[2] and d[2] - dt < 0.9:
                    self.sfx("thud")
                    if abs(d[0] - p.x) < 16 and abs(d[1] - p.y) < 9 and p.z < 20:
                        self.hurt_player(10, d[0])
                    for e in self.enemies:
                        if e.alive and abs(d[0] - e.x) < 16 and abs(d[1] - e.y) < 9:
                            self.damage_enemy(e, 12, True, 1, gain=False)
            self.debris = [d for d in self.debris if d[2] < 1.3]

    # ------------------------------------------------------------ boss
    def phase_boss_intro(self, dt, inp):
        self.talk_step(inp, lambda: self.set_phase("boss"))

    def phase_boss(self, dt, inp):
        self.update_world(dt, inp, control=True)
        if self.phase != "boss":
            return
        self.boss.update(self, dt)
        if self.boss.hp <= 0:
            self.begin_katana()

    def boss_hit(self, dmg, from_air, sx, sy):
        b = self.boss
        if b is None or b.hp <= 0:
            return False
        if not b.take(dmg, from_air):
            return False
        self.score += dmg * 10
        if self.p.state not in SPECIALS:
            self.p.meter = min(3.0, self.p.meter + 0.05)
        self.fx.append(["spark", sx, sy, 0.15, True])
        return True

    # ------------------------------------------------------------ katana and reform
    def begin_katana(self):
        self.enemies, self.projs = [], []
        self.guest = None
        p, b = self.p, self.boss
        p.state, p.move, p.z, p.weapon = "cut", None, 0.0, None
        p.x, p.y, p.face = 150.0, 204.0, 1
        b.x, b.y, b.state, b.st = 300.0, 196.0, "beaten", 0.0
        if hasattr(b, "ball"):
            b.ball = None
        if hasattr(b, "wave"):
            b.wave = None
        self.set_phase("katana")
        self.sound.stop_music()
        self.sfx("rift")

    def phase_katana(self, dt, inp):
        t, b, p = self.pt, self.boss, self.p
        k = self.L["katana"]
        if 2.6 <= t < 3.0:
            p.x = min(300.0, p.x + dt * 420)
        if 3.0 <= t and t - dt < 3.0:
            self.sfx("slash")
        if 3.4 <= t and t - dt < 3.4:
            self.sfx("boom")
        if t > 3.4:
            b.z = max(0.0, b.z - dt * 30)
        if t > 4.6 and not b.gag:
            b.gag = True
            self.bubble(k["boss_line"], b.x, 70, 1.8)
        if 6.0 <= t and t - dt < 6.0:
            self.sfx("rift")
        if 6.8 <= t and t - dt < 6.8:
            self.sfx("mask")
            self.bubble(k["quick_line"], p.x, 120, 2.2)
        p.masked = t < 6.9
        if t > 9.2:
            self.finish_katana()

    def finish_katana(self):
        if not self.seen:
            self.seen = True
            c.save_score(SEEN_KEY % self.L["n"], 1, self.scores_path)
        self.score += 10000
        self.set_phase("reform")

    def skip_cutscene(self):
        if self.phase == "katana":
            self.boss.gag = True
            self.p.masked = False
            self.finish_katana()
        elif self.phase == "reform":
            self.complete()
        elif self.phase == "ending":
            self.finish_game()

    def phase_reform(self, dt, inp):
        if self.pt > 3.5 and self.pt - dt <= 3.5:
            self.sfx("start")
        if self.pt > 11.0 or (self.pt > 4.0 and self.seen and "a" in inp.pressed):
            self.complete()

    def complete(self):
        nxt = self.level_i + 2
        if nxt <= len(LEVELS) and nxt > self.unlocked:
            self.unlocked = nxt
            c.save_score(UNLOCK_KEY, nxt, self.scores_path)
        if self.level_i == len(LEVELS) - 1:
            self.set_phase("ending")
            return
        self.set_phase("complete")
        self.sfx("win")

    def phase_complete(self, dt, inp):
        if self.pt > 3.0 or (self.pt > 1.0 and "a" in inp.pressed):
            self.start_level(self.level_i + 1)

    def phase_ending(self, dt, inp):
        if self.pt > 22.0 or (self.pt > 3.0 and self.seen and "a" in inp.pressed):
            self.finish_game()

    def finish_game(self):
        self.win = True
        self.game_over()

    # ------------------------------------------------------------ continue
    def phase_continue(self, dt, inp):
        if self.pt > 0.6 and ("a" in inp.pressed or "start" in inp.pressed):
            p = self.p
            p.lives, p.hp, p.inv, p.state, p.st = 3, MAX_HP, 2.5, "idle", 0.0
            self.score = 0
            for e in self.enemies:
                if e.alive:
                    e.hp = e.max_hp
            self.set_phase(self.resume_phase)
            self.sfx("start")
        elif self.pt > 9.9:
            self.game_over()

    # ------------------------------------------------------------ the world
    def update_world(self, dt, inp, control):
        p = self.p
        p.inv = max(0.0, p.inv - dt)
        p.combo_t += dt
        p.flash = max(0.0, p.flash - dt)
        if control and p.state != "cut":
            self.read_input(dt, inp)
        self.update_hero(dt, inp)
        for e in self.enemies:
            self.update_enemy(e, dt)
        self.enemies = [e for e in self.enemies if e.alive or e.st < 0.9]
        self.update_projs(dt)
        if self.guest is not None and not self.guest.update(self, dt):
            self.guest = None
        self.check_pickups()

    def lo(self):
        return 12.0 if self.fixed else self.cam + 10

    def hi(self):
        return W - 12.0 if self.fixed else self.cam + W - 10

    def read_input(self, dt, inp):
        p = self.p
        held, pressed = inp.held, inp.pressed
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
                if self.chord >= CHARGE_START and p.meter >= 1.0 and self.can_act():
                    self.start_charge()
                    self.chord = None
            else:
                if self.chord < CHARGE_START or p.meter < 1.0:
                    self.start_jump(inp)
                self.chord = None
            return
        if self.pending is not None:
            self.pending[1] += dt
            if self.pending[1] >= 0.04:
                btn = self.pending[0]
                self.pending = None
                self.press(btn, inp)
        g = self.guest
        if "b" in held and "a" not in held and g is not None and g.state == "fight":
            self.b_hold += dt
            if self.b_hold >= 1.0:
                self.b_hold = 0.0
                g.team(self)
        else:
            self.b_hold = 0.0
        for d in ("left", "right"):
            if d in pressed:
                if self.time - self.last_tap[d] < 0.25 and self.can_act():
                    sgn = 1 if d == "right" else -1
                    self.start_dodge(-sgn if self.scramble > 0 else sgn)
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
        if p.state == "dodge" and btn == "b" and p.weapon is None:
            self.start_move("pounce")
            self.combo_name("POUNCE")
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
        if self.time - p.seq_t > MIX_GAP:
            p.seq = []
        p.seq = (p.seq + [btn])[-3:]
        p.seq_t = self.time
        mix = MIXES.get(tuple(p.seq))
        if mix:
            p.seq = []
            p.combo = {"a": 0, "b": 0}
            self.start_move(mix[0])
            self.combo_name(mix[1])
            return
        combo = B_COMBO if btn == "b" else A_COMBO
        if p.combo_t > 0.6:
            p.combo[btn] = 0
        self.start_move(combo[p.combo[btn] % 3])
        p.combo[btn] = (p.combo[btn] + 1) % 3

    def combo_name(self, name):
        p = self.p
        self.vfx.append({"kind": "name", "text": name, "x": p.x, "y": p.y - 66, "t": 0.0, "life": 0.7})
        self.score += 50

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
        if self.scramble > 0:
            move = -move
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

    def start_charge(self):
        p = self.p
        p.state, p.st, p.charge = "charge", 0.0, 1
        self.vfx.append({"kind": "burst", "x": p.x, "y": p.y, "t": 0.0, "life": 0.25, "lvl": 1})
        self.sfx("charge1")

    def charge_level(self):
        p = self.p
        return max(1, min(3, int(p.meter + 1e-6), 1 + int(p.st / CHARGE_STEP)))

    def nearest_foe(self):
        """Where Sky Pound should land: the closest standing enemy or the boss, if any."""
        p = self.p
        best = None
        for e in self.enemies:
            if e.alive and e.state not in ("fly", "down", "held") and self.lo() - 10 < e.x < self.hi() + 10:
                d = abs(e.x - p.x) + abs(e.y - p.y)
                if best is None or d < best[0]:
                    best = (d, e.x, e.y)
        b = self.boss
        if b is not None and b.hp > 0 and self.phase in ("boss", "ride"):
            d = abs(b.x - p.x) + abs(b.y - p.y)
            if best is None or d < best[0]:
                best = (d, b.x - p.face * 6, b.y)
        if best is None:
            return (p.x + p.face * 40, p.y)
        return (best[1], best[2])

    def fire_special(self, lvl):
        p = self.p
        p.meter = max(0.0, p.meter - lvl)
        p.hit_ids, p.tick, p.charge = set(), 0.0, 0
        state = {1: "skypound", 2: "roar", 3: "cyclone"}[lvl]
        p.state, p.st = state, 0.0
        p.inv = {1: SKY["end"], 2: ROAR["end"], 3: CYC["end"]}[lvl] + 0.3
        self.score += 100 * lvl
        if lvl == 1:
            p.target = self.nearest_foe()
            self.sfx("liftoff")
        elif lvl == 2:
            self.sfx("gather")
        else:
            self.sfx("rift")
            self.bubble("Ninth Dominion, lend me your edge!", p.x, p.y - 70, 1.2)

    def special_damage(self, dmg, knock, test, boss_dmg, sx=None, sy=None):
        """Hit every enemy that test(e) picks, once each (tracked in hit_ids), and the boss if he is in range."""
        p = self.p
        hit = False
        for e in self.enemies:
            if not e.alive or e.id in p.hit_ids or e.state in ("fly", "held"):
                continue
            if test(e.x, e.y, e.z):
                p.hit_ids.add(e.id)
                self.damage_enemy(e, dmg, knock, 1 if e.x > p.x else -1, gain=False)
                self.fx.append(["spark", e.x, e.y - 30 - e.z, 0.14, True])
                hit = True
        cr = self.crate
        if cr is not None and -3 not in p.hit_ids and test(cr["x"], cr["y"], 0):
            p.hit_ids.add(-3)
            cr["hp"] = 0
            self.crate = None
            met = self.met_guests()
            self.token = {"x": cr["x"], "y": cr["y"], "t": 0.0, "guest": met[self.rng.randrange(len(met))]}
            self.fx.append(["spark", cr["x"], cr["y"] - 14, 0.3, True])
        b = self.boss
        if b is not None and b.hp > 0 and -2 not in p.hit_ids and self.phase in ("boss", "ride") and test(b.x, b.y, 0):
            bx, by = b.body()
            if self.boss_hit(boss_dmg, True, bx if sx is None else sx, by if sy is None else sy):
                p.hit_ids.add(-2)
                hit = True
        return hit

    def enemy_behind(self):
        p = self.p
        return any(e.alive and abs(e.y - p.y) <= 10 and 0 < (e.x - p.x) * -p.face <= 30 for e in self.enemies)

    def try_pickup(self):
        p = self.p
        for w in self.weapons:
            if abs(w["x"] - p.x) < 14 and abs(w["y"] - p.y) < 9:
                if any(e.alive and e.state not in ("down", "fly") and abs(e.y - p.y) <= 9
                       and 0 < (e.x - p.x) * p.face <= 26 for e in self.enemies):
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
        held = set(inp.held) if self.phase in PLAY_PHASES else set()
        if self.scramble > 0:
            held = {{"left": "right", "right": "left"}.get(k, k) for k in held}
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
            if p.move == "pounce" and p.st < 0.16:
                p.x += p.face * 170 * dt
            if p.move == "claw" and p.st >= 0.15 and p.st - dt < 0.15:
                p.hit_ids = set()                   # the second swipe can hit again
            if a0 <= p.st <= a1 and -1 not in p.hit_ids:
                if p.move == "tail":
                    self.resolve_attack(reach, dmg, knock, snd, p.face, both=True)
                elif p.move == "hammer":
                    self.resolve_attack(reach, dmg, knock, snd, p.face, downed=True)
                else:
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
        elif s == "special":           # Pops' Bug Out spin
            if p.st > 0.12:
                self.resolve_attack(42, 18, True, "kick", p.face, radius=True)
            if p.st > 0.6:
                p.state = "idle"
        elif s == "charge":
            if self.phase not in PLAY_PHASES:
                p.state, p.charge = "idle", 0
            else:
                lvl = self.charge_level()
                if lvl > p.charge:
                    p.charge = lvl
                    self.vfx.append({"kind": "burst", "x": p.x, "y": p.y, "t": 0.0, "life": 0.3, "lvl": lvl})
                    self.sfx("charge%d" % lvl)
                    self.shake = max(self.shake, 0.08 * lvl)
                if not ("a" in held and "b" in held):
                    self.fire_special(p.charge)
        elif s == "skypound":
            self.update_skypound(dt)
        elif s == "roar":
            self.update_roar(dt)
        elif s == "cyclone":
            self.update_cyclone(dt)
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

    # ------------------------------------------------------------ charged specials
    def update_skypound(self, dt):
        p, t = self.p, self.p.st
        tx, ty = p.target
        if t < SKY["crouch"]:
            p.z = 0.0
        elif t < SKY["up"]:
            k = (t - SKY["crouch"]) / (SKY["up"] - SKY["crouch"])
            p.z = SKY["top"] * (1 - (1 - k) ** 2)
        elif t < SKY["hang"]:
            p.z = SKY["top"]
            p.x += max(-320 * dt, min(320 * dt, tx - p.x))
            p.y += max(-140 * dt, min(140 * dt, ty - p.y))
            if t - dt < SKY["up"]:
                self.sfx("dive")
        elif t < SKY["hit"]:
            k = (t - SKY["hang"]) / (SKY["hit"] - SKY["hang"])
            p.z = SKY["top"] * (1 - k * k)
        else:
            p.z = 0.0
            if t - dt < SKY["hit"]:
                self.sky_impact()
            if t >= SKY["end"]:
                p.state, p.st = "idle", 0.0

    def sky_impact(self):
        p = self.p
        self.sfx("quake")
        self.shake = 0.5
        self.vfx.append({"kind": "quake", "x": p.x, "y": p.y, "t": 0.0, "life": 0.75, "seed": int(p.x)})
        self.vfx.append({"kind": "flash", "col": (255, 236, 170), "t": 0.0, "life": 0.18})
        for k in range(14):
            a = self.rng.uniform(0.15, math.pi - 0.15)
            self.chips.append([p.x + self.rng.uniform(-10, 10), p.y + self.rng.uniform(-4, 4), 2.0,
                                math.cos(a) * self.rng.uniform(40, 130), math.sin(a) * self.rng.uniform(140, 260),
                                self.rng.uniform(0, 6)])
        self.special_damage(24, True, lambda x, y, z: abs(x - p.x) <= 78 and abs(y - p.y) <= 28 + (12 if z > 20 else 0),
                            26, p.x, p.y - 30)
        self.bubble("SKY POUND!", p.x, p.y - 74, 0.9)

    def update_roar(self, dt):
        p, t = self.p, self.p.st
        if t >= ROAR["blast"]:
            if t - dt < ROAR["blast"]:
                self.sfx("roar")
                self.sfx("discharge")
                self.shake = 0.4
                self.vfx.append({"kind": "flash", "col": (110, 190, 255), "t": 0.0, "life": 0.25})
                self.bubble("RAAAWR!", p.x, p.y - 74, 1.0)
            r = min(ROAR["reach"], (t - ROAR["blast"]) * ROAR["speed"])
            p.ring = r
            self.special_damage(20, True, lambda x, y, z: math.hypot(x - p.x, (y - p.y) * 2.2) <= r, 24)
            for pr in self.projs:                     # the blast swats enemy fire out of the air
                if pr["owner"] == "enemy" and math.hypot(pr["x"] - p.x, (pr["y"] - p.y) * 2.2) <= r:
                    pr["dead"] = True
                    self.fx.append(["spark", pr["x"], pr["y"] - pr["z"], 0.1, False])
        if t >= ROAR["end"]:
            p.state, p.st = "idle", 0.0

    def update_cyclone(self, dt):
        p, t = self.p, self.p.st
        if CYC["spin"] <= t < CYC["stop"]:
            p.x += p.face * 74 * dt
            foes = [e for e in self.enemies if e.alive and e.state not in ("fly", "down", "held")]
            if foes:
                e = min(foes, key=lambda e: abs(e.x - p.x))
                p.y += max(-40 * dt, min(40 * dt, e.y - p.y))
            p.tick -= dt
            if p.tick <= 0:
                p.tick = CYC["tick"]
                p.hit_ids = set()
                last = t > CYC["stop"] - CYC["tick"] * 1.5
                reach = CYC["reach"]
                if self.special_damage(6 if not last else 10, last,
                                       lambda x, y, z: abs(x - p.x) <= reach and abs(y - p.y) <= 18 + (14 if z > 20 else 0), 7):
                    self.sfx("slash")
                else:
                    self.sfx("kspin")
        if t >= CYC["stop"] and t - dt < CYC["stop"]:
            self.sfx("slash")
            self.shake = 0.25
        if t >= CYC["end"]:
            p.state, p.st = "idle", 0.0

    def try_grab(self):
        p = self.p
        for e in self.enemies:
            if e.state == "dazed" and e.style == "brawler" and abs(e.y - p.y) < 8 and 0 < (e.x - p.x) * p.face < 26:
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
            if e.state != "down" and e.z > 26:
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
        cr = self.crate
        if cr is not None and -3 not in p.hit_ids and abs(cr["y"] - p.y) <= 10 and -10 < (cr["x"] - p.x) * d <= reach + 6:
            p.hit_ids.add(-3)
            cr["hp"] -= 1
            self.sfx("bonk")
            hit_any = True
            if cr["hp"] <= 0:
                self.crate = None
                met = self.met_guests()
                self.token = {"x": cr["x"], "y": cr["y"], "t": 0.0, "guest": met[self.rng.randrange(len(met))]}
                self.fx.append(["spark", cr["x"], cr["y"] - 14, 0.3, True])
        b = self.boss
        if b is not None and b.hp > 0 and -2 not in p.hit_ids and self.phase in ("boss", "ride"):
            dy = abs(b.y - p.y)
            dx = (b.x - p.x) * d
            if dy <= 12 and (-10 < dx <= reach + 22 or radius and abs(b.x - p.x) < reach + 20):
                bx, by = b.body()
                if self.boss_hit(dmg, air or p.z > 10, bx - d * 14, by):
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
        if gain and self.p.state not in SPECIALS:
            self.p.meter = min(3.0, self.p.meter + 0.07)
        e.recent = [t for t in e.recent if self.time - t < 1.2] + [self.time]
        e.attacking = False
        if e is self.p.held and not knock and e.hp > 0:
            return
        if e.style in ("flyer", "puff"):          # small fry: a solid hit knocks them out of the air
            if e.hp <= 0 or knock or e.style == "puff":
                e.state, e.st = "fly", 0.0
                e.vx, e.vz = d * 70.0, 80.0
            else:
                e.state, e.st = "hurt", 0.0
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
            if e.thrown:
                for o in self.enemies:
                    if o is not e and o.alive and o.state not in ("fly", "down") and abs(o.y - e.y) < 11 and abs(o.x - e.x) < 14:
                        self.damage_enemy(o, 14, True, 1 if e.vx > 0 else -1)
                        self.sfx("thud")
            if e.z <= 0:
                e.z = 0.0
                e.thrown = False
                if e.hp <= 0 or e.style in ("flyer", "puff"):
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
        if s == "hurt":
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
        if e.riding:                         # arriving on a runaway gurney
            e.x -= 170 * dt
            if e.x < W - 70:
                e.riding = False
                self.sfx("land")
            return
        if p.state in ("down", "fly", "cut") or self.phase not in PLAY_PHASES:
            e.state = "idle"
            return
        if e.style == "flyer":
            self.update_flyer(e, dt)
            return
        if e.style == "puff":
            e.x += max(-e.speed * dt, min(e.speed * dt, p.x - e.x))
            e.y += max(-e.speed * 0.7 * dt, min(e.speed * 0.7 * dt, p.y - e.y))
            e.z = 6 + math.sin(e.st * 3) * 3
            e.anim += dt
            if abs(e.x - p.x) < 14 and abs(e.y - p.y) < 8 and e.cool <= 0:
                e.cool = 1.0
                self.hurt_player(e.dmg, e.x)
            return
        if s == "attack":
            if e.st >= 0.28 and not e.swung:
                e.swung = True
                if e.style == "thrower" and abs(e.x - p.x) > 40:
                    kind = {"butler": "tray", "gigbot": "box", "smogbot": "soot", "bailiff": "notice"}.get(e.kind, "tray")
                    self.projs.append({"kind": kind, "x": e.x + e.face * 10, "y": e.y, "z": 24.0, "vx": e.face * 160.0,
                                       "vz": 0.0, "g": 0.0, "dmg": e.dmg + 2, "owner": "enemy"})
                    self.sfx("throw")
                elif abs(e.y - p.y) <= 8 and 0 < (p.x - e.x) * e.face <= e.reach + 4 and p.z < 20:
                    heavy = e.kind in ("security", "foreman", "demo", "collector") and self.rng.random() < 0.25
                    self.hurt_player(e.dmg, e.x, knock=heavy)
            if e.st >= 0.5:
                e.state, e.st = "idle", 0.0
                e.swung = False
                e.attacking = False
                e.cool = e.cool_max * self.rng.uniform(0.8, 1.3)
            return
        attackers = sum(1 for o in self.enemies if o.attacking and o is not e)
        side = 1 if e.x > p.x else -1
        e.face = -side
        ranged = e.style == "thrower" and abs(e.x - p.x) > 50
        if e.attacking or attackers < 2:
            e.attacking = True
            tx = p.x + side * (e.reach - 2)
            if e.style == "thrower" and e.id % 2 == 0:
                tx = p.x + side * 90
        else:
            tx = p.x + side * 70
        if not (self.lo() < tx < self.hi()):
            tx = p.x - side * (e.reach - 2 if e.attacking else 70)
        tx = max(self.lo() + 8, min(self.hi() - 8, tx))
        dx, dy = tx - e.x, p.y - e.y
        if abs(dx) > 3 or abs(dy) > 2:
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

    def update_flyer(self, e, dt):
        """Drones hover at chest height and drop paper (or static) on Quick."""
        p = self.p
        e.anim += dt
        tx = p.x + (40 if e.id % 2 else -40) * math.cos(e.st * 0.8)
        tx = max(self.lo() + 8, min(self.hi() - 8, tx))
        e.x += max(-e.speed * dt, min(e.speed * dt, tx - e.x))
        e.y += max(-40 * dt, min(40 * dt, p.y - e.y))
        e.z = 22 + math.sin(e.st * 4) * 3
        e.face = 1 if p.x > e.x else -1
        if e.cool <= 0 and abs(e.x - p.x) < 50 and abs(e.y - p.y) < 10:
            e.cool = e.cool_max * self.rng.uniform(0.8, 1.2)
            d = 1 if p.x > e.x else -1
            self.projs.append({"kind": "slip" if e.kind == "authdrone" else "static", "x": e.x, "y": p.y, "z": e.z + 10,
                               "vx": d * 90.0, "vz": 0.0, "g": 60.0, "dmg": e.dmg, "owner": "enemy",
                               "scramble": e.kind == "fakenews"})
            self.sfx("throw")

    def update_projs(self, dt):
        p = self.p
        for pr in self.projs:
            pr["x"] += pr["vx"] * dt
            pr["vz"] -= pr["g"] * dt
            pr["z"] += pr["vz"] * dt
            if "spin" in pr:
                pr["spin"] += dt * 900
            if pr["owner"] == "enemy":
                if abs(pr["x"] - p.x) < 9 and abs(pr["y"] - p.y) < 8 and abs(pr["z"] - (p.z + 22)) < 22:
                    if p.inv <= 0 and p.state not in ("down", "fly", "dodge"):
                        self.hurt_player(pr["dmg"], pr["x"] - pr["vx"])
                        if pr.get("scramble"):
                            self.scramble = 2.0
                            self.bubble("Fake news! Controls scrambled!", p.x, p.y - 64, 1.6)
                        pr["dead"] = True
            else:
                for e in self.enemies:
                    if e.alive and e.state not in ("down", "fly") and abs(pr["x"] - e.x) < 11 and abs(pr["y"] - e.y) < 9:
                        if pr["kind"] == "stun":
                            e.hp -= pr["dmg"]
                            if e.style in ("flyer", "puff") or e.hp <= 0:
                                self.damage_enemy(e, 0, True, 1 if pr["vx"] > 0 else -1, gain=False)
                            elif e.state != "held":
                                e.state, e.st = "dazed", 0.3
                        else:
                            self.damage_enemy(e, pr["dmg"], True, 1 if pr["vx"] > 0 else -1)
                        self.sfx("bonk")
                        pr["dead"] = True
                        break
                b = self.boss
                if not pr.get("dead") and b is not None and b.hp > 0 and self.phase in ("boss", "ride"):
                    if abs(pr["x"] - b.x) < 26 and abs(pr["y"] - b.y) < 12:
                        bx, by = b.body()
                        if self.boss_hit(pr["dmg"], True, pr["x"], by):
                            pr["dead"] = True
            if pr["z"] <= 0:
                pr["dead"] = True
                if pr["owner"] == "player":
                    self.weapons.append({"x": pr["x"], "y": pr["y"], "kind": pr["kind"]})
        lo, hi = self.lo() - 60, self.hi() + 60
        self.projs = [pr for pr in self.projs if not pr.get("dead") and lo < pr["x"] < hi]

    def check_pickups(self):
        p, tk = self.p, self.token
        if tk is None:
            return
        tk["t"] += 1 / 60.0
        if abs(tk["x"] - p.x) < 14 and abs(tk["y"] - p.y) < 10 and p.z < 20 and self.guest is None:
            self.token = None
            self.summon(tk["guest"])

    def summon(self, kind):
        self.guest = guests.summon(kind, self)
        self.sfx("powerup")
        self.bubble(GUESTS[kind]["greet"], self.p.x, self.p.y - 64, 1.6)

    def bubble(self, msg, x, y, t):
        self.bubbles.append([msg, (x, y), t])

    # ------------------------------------------------------------ drawing
    def draw_title_art(self, surf):
        art.street(surf, 980 + math.sin(self.time * 0.3) * 20, self.time)
        big = pygame.transform.scale(art.portrait(True), (120, 120))
        surf.blit(big, (W - 126, H - 126))
        pygame.draw.rect(surf, art.BLUE[2], (W - 126, H - 126, 120, 120), 2)

    def draw(self, surf):
        if self.phase == "select":
            self.draw_select(surf)
            return
        if self.phase == "reform":
            self.draw_reform(surf)
            return
        if self.phase == "ending":
            self.draw_ending(surf)
            return
        kind = self.sc["kind"]
        if kind == "walk":
            stages.stage(surf, self.scene, self.cam, self.time)
        elif kind == "ride":
            stages.ride(surf, self.scene, self.prog, self.time, self.doors, self.belt)
        else:
            stages.arena(surf, self.scene, self.time, clear=(self.phase == "katana" and self.pt > 3.0))
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
            art.say(surf, "LEVEL %d COMPLETE" % self.L["n"], (W // 2, 90), 34, (255, 220, 80))
            art.say(surf, " ".join(self.L["headline"]), (W // 2, 128), 18, (255, 255, 255))
        if self.phase == "intro" and self.pt < 2.0 and self.talk_i == 0:
            art.say(surf, "LEVEL %d" % self.L["n"], (W // 2, 50), 30, (255, 220, 80))
            art.say(surf, self.L["name"].upper(), (W // 2, 80), 24, (255, 255, 255))
        if self.fade > 0:
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, int(255 * min(1.0, self.fade / 0.6))))
            surf.blit(shade, (0, 0))
        if self.shake > 0 and self.phase in PLAY_PHASES:
            amp = int(1 + 6 * min(1.0, self.shake / 0.5))
            k = int(self.time * 60)
            surf.scroll((k * 7) % (2 * amp + 1) - amp, ((k * 13) % (2 * amp + 1) - amp) // 2)

    def draw_select(self, surf):
        art.street(surf, 400 + self.pt * 10, self.time)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((6, 6, 20, 170))
        surf.blit(shade, (0, 0))
        art.say(surf, "CHOOSE A LEVEL", (W // 2, 10), 28, (255, 220, 80))
        for i, L in enumerate(LEVELS):
            y = 44 + i * 26
            open_ = i < self.unlocked
            sel = i + 1 == self.choice
            r = pygame.Rect(70, y, W - 140, 22)
            pygame.draw.rect(surf, (60, 140, 200) if sel else ((30, 50, 80) if open_ else (30, 30, 40)), r, border_radius=4)
            if sel:
                pygame.draw.rect(surf, (255, 220, 80), r, 2, border_radius=4)
            label = "%d  %s" % (L["n"], L["name"]) if open_ else "%d  ???" % L["n"]
            art.say(surf, label, (84, y + 3), 18, (255, 255, 255) if open_ else (120, 120, 130), center=False)
        art.say(surf, "Up/down: choose   Big button: fight", (W // 2, 210), 16, (220, 220, 235))

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
            if p.move == "claw" and p.st >= 0.15:
                pose = "jab"
            elif p.move == "tail" and 0.1 < p.st < 0.26:
                return art.hero("round", p.masked, -p.face if int(p.st * 20) % 2 else p.face)
        elif s == "jump":
            pose = {"kick": "jumpk", "elbow": "elbow"}.get(p.air, "tuck")
        elif s == "hit":
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
        elif s == "charge":
            pose = "charge"
        elif s == "skypound":
            t = p.st
            if t < SKY["crouch"]:
                pose = "charge"
            elif t < SKY["hang"]:
                pose = "sky"
            elif t < SKY["hit"]:
                key = ("dive", p.masked, p.face)
                img = art._cache.get(key)
                if img is None:
                    img = art._cache[key] = pygame.transform.flip(art.hero("sky", p.masked, p.face), False, True)
                return img
            else:
                pose = "pound"
        elif s == "roar":
            pose = "charge" if p.st < ROAR["blast"] else "roar"
        elif s == "cyclone":
            t = p.st
            if t < CYC["spin"]:
                pose = "draw"
            elif t < CYC["stop"]:
                return art.hero("spin", p.masked, 1 if int(t * 16) % 2 == 0 else -1)
            else:
                pose = "strike"
        return art.hero(pose, p.masked, p.face)

    def blit_fighter(self, surf, img, x, y, z, face):
        if img.get_height() > 0 and self.p is not None and img is self._dive_img():
            surf.blit(img, (int(x - img.get_width() / 2), int(y - z - 12)))
            return
        if img.get_width() > 70:
            surf.blit(img, (int(x - img.get_width() / 2), int(y - z - img.get_height() + 4)))
            return
        ax = art.HX + 1 if face > 0 else img.get_width() - 2 - art.HX
        surf.blit(img, (int(x - ax), int(y - z - (art.FEET_Y + 1))))

    def _dive_img(self):
        p = self.p
        return art._cache.get(("dive", p.masked, p.face))

    def enemy_sprite(self, e):
        s, st = e.state, e.style
        if st == "flyer":
            return cast.flyer(e.kind, e.anim)
        if st == "puff":
            return cast.puff(e.anim, e.flash > 0)
        if st == "thrower":
            img = cast.robot(e.kind, int(e.anim * 8), e.face, s == "attack")
            return art.lying(img) if s in ("fly", "down", "out") else img
        if s in ("fly", "down", "out"):
            return art.lying(cast.goon(e.kind, "hit", e.face))
        pose = {"walk": "walk%d" % (int(e.anim * 8) % 4), "attack": "jab" if e.st > 0.15 else "idle1",
                "hurt": "hit", "dazed": "idle1", "held": "hit", "bitten": "hit", "getup": "getup"}.get(s, "idle0")
        return cast.goon(e.kind, pose, e.face)

    def draw_world(self, surf):
        cam = 0 if self.fixed else int(self.cam)
        p = self.p
        for d in self.debris:
            if d[2] < 0.9:
                r = int(4 + d[2] * 10)
                pygame.draw.ellipse(surf, (40, 20, 20), (int(d[0] - r), int(d[1] - r / 3), r * 2, int(r / 1.5)))
                fy = int(d[1] - 160 * (1 - d[2] / 0.9))
                pygame.draw.rect(surf, (200, 160, 40), (int(d[0] - 10), fy - 6, 20, 6))
            else:
                pygame.draw.rect(surf, (200, 160, 40), (int(d[0] - 10), int(d[1] - 6), 20, 6))
        items = [(w["y"], 0, "weapon", w) for w in self.weapons]
        if self.token is not None:
            items.append((self.token["y"], 1, "token", self.token))
        if self.crate is not None:
            items.append((self.crate["y"], 1, "crate", self.crate))
        for e in self.enemies:
            items.append((e.y, 2, "enemy", e))
        if self.guest is not None:
            items.append((self.guest.y, 3, "guest", self.guest))
        items.append((p.y, 4, "hero", p))
        if self.boss is not None and self.phase in ("boss", "boss_intro", "ride", "continue"):
            items.append((self.boss.y, 1, "boss", self.boss))
        if self.scene == "ramp":
            art.shadow(surf, p.x, p.y, 54)
            stages.gurney(surf, p.x, p.y)
        items.sort(key=lambda it: (it[0], it[1]))
        for _, _, kind, o in items:
            if kind == "weapon":
                surf.blit(art.weapon_img(o["kind"]), (int(o["x"] - cam - 12), int(o["y"] - 4)))
            elif kind == "token":
                art.shadow(surf, o["x"] - cam, o["y"], 18)
                surf.blit(self.token_img(o), (int(o["x"] - cam - 12), int(o["y"] - 30 + math.sin(o["t"] * 3) * 3)))
            elif kind == "crate":
                x, y = int(o["x"] - cam), int(o["y"])
                art.shadow(surf, x, y, 26)
                pygame.draw.rect(surf, art.OUT, (x - 12, y - 22, 24, 22))
                pygame.draw.rect(surf, (170, 120, 70), (x - 11, y - 21, 22, 20))
                pygame.draw.line(surf, (120, 80, 40), (x - 11, y - 21), (x + 10, y - 2), 2)
                pygame.draw.line(surf, (120, 80, 40), (x + 10, y - 21), (x - 11, y - 2), 2)
            elif kind == "enemy":
                if not o.alive and int(o.st * 12) % 2:
                    continue
                art.shadow(surf, o.x - cam, o.y)
                img = self.enemy_sprite(o)
                if o.flash > 0 and o.style != "puff":
                    img = art.white(img)
                if o.style in ("flyer", "puff"):
                    surf.blit(img, (int(o.x - cam - img.get_width() / 2), int(o.y - o.z - 30)))
                else:
                    self.blit_fighter(surf, img, o.x - cam, o.y, o.z, o.face)
                if o.riding:
                    stages.gurney(surf, o.x - cam, o.y)
                if o.state == "dazed":
                    art.stars(surf, o.x - cam, o.y - 52, self.time)
            elif kind == "guest":
                o.draw(surf, self, cam)
            elif kind == "boss":
                o.draw(surf, self)
            else:
                if p.inv > 0 and int(self.time * 16) % 2 and p.state not in SPECIALS + ("dodge", "cut"):
                    continue
                if p.state == "cut" and self.guest is not None and self.guest.kind == "uncle_t":
                    continue
                art.shadow(surf, p.x - cam, p.y, max(8, int(26 - p.z / 12)))
                if p.state == "charge":
                    fx.aura(surf, p.x - cam, p.y - p.z, p.charge, self.time, False)
                if p.state == "skypound" and p.st >= SKY["up"] and p.st < SKY["hit"]:
                    fx.target_mark(surf, p.x - cam, p.y, self.time)
                if p.state == "skypound" and SKY["crouch"] <= p.st < SKY["up"]:
                    fx.skybeam(surf, p.x - cam, p.y - p.z - 20, (p.st - SKY["crouch"]) / (SKY["up"] - SKY["crouch"]))
                if p.state == "skypound" and SKY["hang"] <= p.st < SKY["hit"]:
                    fx.skybeam(surf, p.x - cam, p.y - p.z, 0.3)
                if p.state == "roar" and p.st < ROAR["blast"]:
                    fx.gather(surf, p.x - cam, p.y, p.st / ROAR["blast"], self.time)
                img = self.sprite_for(p)
                if p.flash > 0:
                    img = art.white(img)
                jit = 0
                if p.state == "charge" or (p.state == "roar" and p.st >= ROAR["blast"] and p.st < ROAR["blast"] + 0.5):
                    jit = (1 if int(self.time * 40) % 2 else -1) * (1 if p.state == "roar" else min(2, p.charge))
                self.blit_fighter(surf, img, p.x - cam + jit, p.y, p.z, p.face)
                if p.state == "charge":
                    fx.aura(surf, p.x - cam, p.y - p.z, p.charge, self.time, True)
                    art.say(surf, fx.NAMES[p.charge], (int(p.x - cam), int(p.y - 72)), 14, fx.LEVEL_COLS[p.charge][3])
                if p.state == "cyclone":
                    self.draw_cyclone(surf, p, cam)
                if p.weapon is not None and p.state not in ("fly", "down"):
                    ang = 300 if p.state == "atk" and p.move == "swing" and p.st > 0.08 else 45
                    wimg = art.weapon_img(p.weapon["kind"], ang if p.face > 0 else 180 - ang)
                    surf.blit(wimg, (int(p.x - cam + p.face * 10 - wimg.get_width() / 2), int(p.y - p.z - 32)))
                if p.state == "special":
                    pygame.draw.circle(surf, art.BLUE[2], (int(p.x - cam), int(p.y - 22)), 24 + int(p.st * 30) % 8, 2)
                if p.state == "roar" and p.st >= ROAR["blast"]:
                    r = min(ROAR["reach"], (p.st - ROAR["blast"]) * ROAR["speed"])
                    k = (p.st - ROAR["blast"]) / (ROAR["end"] - ROAR["blast"])
                    fx.roar_ring(surf, p.x - cam, p.y, r, k, self.time)
                    if k < 0.6:
                        fx.roar_ring(surf, p.x - cam, p.y, r * 0.55, min(1.0, k + 0.3), self.time + 1)
                if self.scramble > 0:
                    art.say(surf, "?!", (int(p.x - cam), int(p.y - 70)), 16, (255, 120, 255))
        for pr in self.projs:
            x, y = int(pr["x"] - cam), int(pr["y"] - pr["z"])
            art.shadow(surf, pr["x"] - cam, pr["y"], 10)
            k = pr["kind"]
            if k == "coin":
                surf.blit(art.coin(), (x - 4, y - 4))
            elif k == "tray":
                surf.blit(art.tray(), (x - 6, y - 3))
            elif k in ("notice", "slip"):
                pygame.draw.rect(surf, art.OUT, (x - 5, y - 4, 10, 8))
                pygame.draw.rect(surf, (250, 250, 240), (x - 4, y - 3, 8, 6))
                pygame.draw.line(surf, (220, 40, 40), (x - 3, y - 1), (x + 3, y - 1))
            elif k == "box":
                pygame.draw.rect(surf, art.OUT, (x - 6, y - 5, 12, 10))
                pygame.draw.rect(surf, (200, 150, 90), (x - 5, y - 4, 10, 8))
            elif k == "soot":
                pygame.draw.circle(surf, (40, 36, 34), (x, y), 5)
                pygame.draw.circle(surf, (250, 120, 40), (x - 1, y - 1), 1)
            elif k == "static":
                for j in range(6):
                    v = ((j * 37 + int(self.time * 60)) % 5) * 50
                    surf.fill((v, v, 255), (x - 6 + (j % 3) * 4, y - 4 + (j // 3) * 4, 4, 4))
            elif k == "stun":
                pygame.draw.circle(surf, (255, 240, 120), (x, y), 3)
                pygame.draw.circle(surf, (255, 255, 255), (x, y), 1)
            else:
                img = art.weapon_img(k, pr.get("spin", 0))
                surf.blit(img, (x - img.get_width() // 2, y - img.get_height() // 2))
        for kind, x, y, t, big in self.fx:
            if kind == "spark":
                art.spark(surf, x - cam, y, big)
            elif kind == "ko":
                art.stars(surf, x - cam, y - 14, self.time)
            elif kind == "fence":
                for k in range(8):
                    surf.fill((150, 154, 166), (int(x - cam + k * 5 + (0.5 - t) * 80), int(y - 30 - k * 3), 3, 2))
        for v in self.vfx:
            k = v["t"] / v["life"]
            if v["kind"] == "burst":
                fx.burst(surf, v["x"] - cam, v["y"], v["lvl"], k)
            elif v["kind"] == "quake":
                fx.quake(surf, v["x"] - cam, v["y"], k, v["seed"])
            elif v["kind"] == "name":
                art.say(surf, v["text"], (int(v["x"] - cam), int(v["y"] - 14 * k)), 16, (255, 220, 80))
        for d in self.chips:
            fx.debris(surf, d[0] - cam, d[1], d[2], d[5])
        for v in self.vfx:
            if v["kind"] == "flash":
                fx.tint(surf, v["col"], 70 * (1 - v["t"] / v["life"]))
        for msg, (x, y), t in self.bubbles:
            art.bubble(surf, msg, x - cam, y)

    def token_img(self, tk):
        s = art.token(tk["t"])
        if tk["guest"] == "mazee":
            return s
        s = s.copy()
        pygame.draw.circle(s, art.BLUE[2], (12, 12), 8)
        face = {"uncle_t": "uncle_t", "stephen": "stephen", "squad": "miles", "pops": "pops"}[tk["guest"]]
        head = cast.guest_fig(face, "idle0", 1).subsurface((art.HX - 7, 4, 16, 16))
        s.blit(pygame.transform.scale(head, (12, 12)), (6, 5))
        return s

    def draw_talk(self, surf):
        if self.talk_i >= len(self.talk):
            return
        who, masked, line = self.talk[self.talk_i]
        box = pygame.Rect(4, 150, 392, 86)
        pygame.draw.rect(surf, art.OUT, box)
        pygame.draw.rect(surf, (24, 22, 40), box.inflate(-4, -4))
        pygame.draw.rect(surf, art.BLUE[1], box.inflate(-4, -4), 1)
        img = self.boss_portrait() if masked is None else art.portrait(masked)
        surf.blit(pygame.transform.scale(img, (78, 78)), (8, 154))
        pygame.draw.rect(surf, art.GOLD[2] if masked is None else art.BLUE[2], (8, 154, 78, 78), 1)
        art.say(surf, who, (94, 156), 18, art.GOLD[2] if masked is None else (255, 220, 80), center=False)
        shown = line[:int(self.pt * 45)]
        lines, cur = [], ""
        for w_ in shown.split(" "):
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

    def boss_portrait(self):
        key = ("bossp", self.L["boss"])
        img = art._cache.get(key)
        if img is not None:
            return img
        if self.L["boss"] == "heir":
            img = art.heir_portrait()
        else:
            img = pygame.Surface((96, 96))
            for y in range(96):
                img.fill((int(40 + 40 * y / 96), 20, int(40 + 30 * y / 96)), (0, y, 96, 1))
            fig = {"pig": lambda: cast.capitalist_pig(0, "walk"), "poverty": lambda: cast.mister_poverty(0),
                   "eviction": lambda: cast.madame_eviction(0, "ground"), "smog": lambda: cast.baron_smog(0),
                   "biglie": lambda: cast.big_lie(0)}[self.L["boss"]]()
            fig = pygame.transform.scale(fig, (int(fig.get_width() * 1.4), int(fig.get_height() * 1.4)))
            img.blit(fig, (48 - fig.get_width() // 2, 6))
        art._cache[key] = img
        return img

    def draw_cyclone(self, surf, p, cam):
        t = p.st
        hx, hy = p.x - cam, p.y - p.z - 26
        if t < CYC["spin"]:                     # the rift opens and the blade slides out
            k = t / CYC["spin"]
            art.rift(surf, hx + p.face * 22, hy - 6, min(1.0, k * 1.6), self.time)
            fx.crimson_katana(surf, (hx + p.face * 8, hy - 4), -math.pi / 2 - p.face * 0.6, 14 + 26 * k, self.time)
            return
        if t >= CYC["stop"]:                    # the finishing pose; the blade goes home
            k = (t - CYC["stop"]) / (CYC["end"] - CYC["stop"])
            fx.crimson_katana(surf, (hx + p.face * 10, hy + 2), p.face * 0.2 if p.face > 0 else math.pi - 0.2,
                              40 * (1 - k), self.time)
            art.rift(surf, hx + p.face * 50, hy, max(0.0, 1 - k * 1.5), self.time)
            return
        spin = (t - CYC["spin"]) * 26
        for g in (3, 2, 1):                     # afterimages and the swoosh
            fx.crimson_katana(surf, (hx + math.cos(spin - g * 0.35) * 8, hy + math.sin(spin - g * 0.35) * 4),
                              spin - g * 0.35, 40, self.time, ghost=g)
        fx.slash_arc(surf, hx, hy, spin - 1.4, spin, 46, 0.2)
        fx.slash_arc(surf, hx, hy + 6, spin - 1.0 + math.pi, spin + math.pi, 38, 0.4)
        fx.crimson_katana(surf, (hx + math.cos(spin) * 8, hy + math.sin(spin) * 4), spin, 40, self.time)

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
        label = self.sc["label"]
        if self.sc["kind"] == "ride":
            label += "  %s %d" % (self.sc["unit"], int(self.prog))
        art.say(surf, label, (W // 2, 18), 14, art.GOLD[2])
        g = self.guest
        if g is not None and g.state != "leave":
            gb = pygame.Rect(W - 28, 4, 24, 24)
            pygame.draw.rect(surf, art.OUT, gb.inflate(2, 2))
            surf.blit(pygame.transform.scale(self.token_img({"t": 0.0, "guest": g.kind}), (24, 24)), gb)
            ring = max(0.0, g.t / guests.DURATION)
            pygame.draw.arc(surf, art.BLUE[2], gb.inflate(8, 8), math.pi / 2, math.pi / 2 + math.tau * ring, 2)
            name = g.lines["name"]
            art.say(surf, name, (W - 36 - art.font(14).size(name)[0], 4), 14, (240, 240, 250), center=False)
        b = self.boss
        if b is not None and b.hp > 0 and self.phase in ("boss", "ride"):
            name = b.name if not b.mini else b.name + " (REMATCH)"
            art.say(surf, name, (W // 2, 214), 14, art.GOLD[2])
            pygame.draw.rect(surf, art.OUT, (99, 227, 202, 8))
            pygame.draw.rect(surf, (70, 20, 30), (100, 228, 200, 6))
            pygame.draw.rect(surf, art.GOLD[2], (100, 228, int(200 * b.hp / b.max), 6))

    # ------------------------------------------------------------ cutscenes
    def draw_katana(self, surf):
        t, p, b = self.pt, self.p, self.boss
        target = self.L["katana"]["target"]
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((6, 8, 30, int(min(150, t * 160)) if t < 6.5 else int(max(0, 150 - (t - 6.5) * 150))))
        surf.blit(dim, (0, 0))
        self.draw_target(surf, target, t)
        b.draw(surf, self)
        if target == "broadcast":                 # the whole crew stands with Quick at the end
            for i, kind in enumerate(("mazee", "uncle_t", "stephen", "miles", "felix", "pops")):
                x = 20 + i * 18
                if kind == "mazee":
                    surf.blit(art.mazee(0, 1, True), (x - 20, 196))
                else:
                    img = cast.guest_fig(kind, "victory" if t > 3.4 else "idle0", 1)
                    surf.blit(img, (x - art.HX - 1, 214 - art.FEET_Y - 1))
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
        if 1.0 <= t < 2.6 or 6.0 <= t < 6.8:
            pose = "draw"
        elif 2.6 <= t < 6.0:
            pose = "strike"
        elif t >= 7.6:
            pose = "victory"
        art.shadow(surf, p.x, p.y)
        self.blit_fighter(surf, art.hero(pose, p.masked, p.face), p.x, p.y, 0, p.face)
        if 1.2 <= t < 2.6:
            grow = min(1.0, (t - 1.2) / 0.8)
            art.katana(surf, (p.x - 10, p.y - 36), math.radians(200 - 40 * grow), 14 + 30 * grow)
            k = min(1.0, (t - 1.2) / 0.25)
            px_ = int(-150 + 160 * k)
            panel = pygame.Rect(px_, 30, 150, 110)
            pygame.draw.rect(surf, art.OUT, panel.inflate(4, 4))
            surf.blit(pygame.transform.scale(art.portrait(True), (150, 150)), panel.topleft, area=pygame.Rect(0, 20, 150, 110))
            pygame.draw.rect(surf, art.BLUE[2], panel, 2)
            art.say(surf, "DAYBREAK", (px_ + 236, 70), 34, art.BLUE[3])
        elif 2.6 <= t < 6.0:
            art.katana(surf, (p.x + 14, p.y - 30), math.radians(-10), 44)
        if 2.9 <= t < 3.4:
            a = int(255 * (1 - (t - 2.9) / 0.5))
            flash = pygame.Surface((W, H), pygame.SRCALPHA)
            flash.fill((255, 255, 255, a))
            surf.blit(flash, (0, 0))
            pygame.draw.line(surf, art.BLUE[3], (40, 140), (380, 50), 3)
        if t > 4.0:
            art.say(surf, self.L["katana"]["shout"], (W // 2, 18), 18, art.GOLD[3])
        for msg, (x, y), tt in self.bubbles:
            art.bubble(surf, msg, x, y)
        if t > 8.4:
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, int(min(255, (t - 8.4) * 320))))
            surf.blit(shade, (0, 0))

    def draw_target(self, surf, target, t):
        """What Daybreak cuts, and what follows: different for every boss."""
        cut = t >= 3.0
        after = max(0.0, t - 3.4)
        if target == "vault" and after > 0:
            for k in range(40):
                ct = after * 1.3 + k * 0.08
                cx = 316 + math.sin(k * 1.7) * 30 + ct * 18
                cy = 86 + (ct % 2.0) * 90
                if cy < 236:
                    surf.blit(art.coin(), (int(cx), int(cy)))
        elif target == "stamp":
            if not cut:
                pygame.draw.rect(surf, (120, 70, 40), (340, 40, 10, 60))
                pygame.draw.rect(surf, (160, 30, 40), (318, 96, 54, 26))
                art.say(surf, "DENIED", (345, 100), 16, (255, 220, 220))
            else:
                pygame.draw.rect(surf, (40, 140, 70), (300, 170, 30, 22))
                pygame.draw.rect(surf, (40, 140, 70), (334, 176, 30, 22))
                art.say(surf, "APPROVED", (332, 150), 18, (120, 255, 160))
                for k in range(12):
                    u = after * 0.6 + k * 0.09
                    x = 320 + math.cos(k) * 40 + u * 60 * (1 if k % 2 else -1)
                    y = 120 - u * 80 + math.sin(u * 8 + k) * 4
                    if y > -10:
                        pygame.draw.polygon(surf, (250, 250, 250), [(x, y), (x + 6, y - 3), (x + 4, y + 2)])
                        pygame.draw.polygon(surf, (250, 250, 250), [(x, y), (x - 6, y - 3), (x - 4, y + 2)])
        elif target == "chains":
            if not cut:
                gray = pygame.Surface((W, H), pygame.SRCALPHA)
                gray.fill((60, 60, 70, 110))
                surf.blit(gray, (0, 0))
                for wx in (30, 60, 360, 386):
                    cast.bills_chain(surf, 300, 150, wx, 200, self.time)
                    pygame.draw.rect(surf, (120, 120, 130), (wx - 4, 180, 8, 22))
            else:
                for wx in (30, 60, 360, 386):
                    img = art.citizen(wx % 3, "victory", 1 if wx < 200 else -1)
                    surf.blit(img, (wx - art.HX - 1, 214 - art.FEET_Y - 1))
        elif target == "cable":
            cast.crane(surf, 70, 30, 300)
            if not cut:
                cast.wrecking_ball(surf, 300, 120, (300, 40))
            else:
                y = min(206, 120 + after * 300)
                pygame.draw.ellipse(surf, (230, 210, 150), (260, 200, 80, 20))
                cast.wrecking_ball(surf, 300, y, (300, 40 + int(min(166, after * 300))))
        elif target == "smog":
            cover = 1.0 if not cut else max(0.0, 1 - after / 1.5)
            if cover > 0:
                cloud = pygame.Surface((W, 120), pygame.SRCALPHA)
                for k in range(14):
                    pygame.draw.circle(cloud, (60, 56, 54, int(220 * cover)), (k * 30 + int(math.sin(self.time + k) * 6), 50), 34)
                surf.blit(cloud, (0, 0))
            if cut:
                for k in range(5):
                    beam = pygame.Surface((30, 200), pygame.SRCALPHA)
                    beam.fill((255, 240, 180, int(70 * (1 - cover))))
                    surf.blit(pygame.transform.rotate(beam, 20), (40 + k * 80, 0))
        elif target == "broadcast":
            if not cut:
                pygame.draw.line(surf, (40, 40, 48), (360, 0), (320, 130), 4)
                pygame.draw.circle(surf, (240, 60, 60), (360, 6), 5)
            else:
                for k in range(16):
                    u = after * 0.5 + k * 0.07
                    x = 200 + math.cos(k * 1.3) * 120 + math.sin(u * 3) * 10
                    y = 200 - u * 120
                    if y > -10:
                        pygame.draw.rect(surf, (250, 250, 240), (int(x) - 4, int(y) - 3, 8, 6))
                        pygame.draw.line(surf, (40, 100, 200), (int(x) - 2, int(y)), (int(x) + 2, int(y)))
                for k in range(30):
                    surf.fill([(220, 60, 60), (250, 220, 60), (60, 140, 230)][k % 3],
                              (int((k * 53 + after * 80) % W), int((k * 31 + after * 60) % 140), 3, 3))

    def draw_reform(self, surf):
        t = self.pt
        first = next(s["stage"] for s in self.L["scenes"] if s["kind"] == "walk")
        if t < 3.5:
            stages.stage(surf, first, 600, self.time)
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 160))
            surf.blit(shade, (0, 0))
            art.newspaper(surf, self.L["headline"], self.L["sub"], t)
            return
        k = t - 3.5
        stages.stage(surf, first, 120 + k * 40, self.time, morning=True)
        n = self.L["n"]
        if n == 1:
            art.bus(surf, int(-90 + k * 70) % 560 - 80, 166)
        elif n == 3:
            stages.food_truck(surf, 250, 160)
        elif n == 4:
            stages.garden(surf, 220, 180)
        elif n == 6:
            stages.bunting(surf, 40, self.time)
        for i in range(5):
            x = (i * 97 + k * (25 + i * 6)) % (W + 60) - 30
            y = 186 + (i * 13) % 40
            art.shadow(surf, x, y)
            img = art.citizen(i, "walk%d" % (int(k * 8 + i) % 4), 1)
            surf.blit(img, (int(x - art.HX - 1), int(y - art.FEET_Y - 1)))
        hero = art.hero("victory" if int(k) % 4 == 0 else "idle0", False, 1)
        art.shadow(surf, 200, 212)
        surf.blit(hero, (200 - art.HX - 1, 212 - art.FEET_Y - 1))
        box = pygame.Rect(30, 18, W - 60, 40)
        pygame.draw.rect(surf, art.OUT, box.inflate(2, 2), border_radius=4)
        pygame.draw.rect(surf, (250, 246, 236), box, border_radius=4)
        for i, line in enumerate(self.L["city"]):
            art.say(surf, line, (W // 2, 22 + i * 16), 18, (40, 40, 60), outline=(250, 246, 236))

    CREDITS = ["BLACK WARRIOR", "", "Quick", "Mazee", "Uncle T", "Stephen", "Miles and Felix", "Pops", "",
               "Fair taxes. Care for all.", "A floor under everyone.", "Homes for all. Clean air.",
               "Every vote counts.", "", "Confluence City, transformed.", "", "Thanks for playing!"]

    def draw_ending(self, surf):
        t = self.pt
        stages.district(surf, "pier", 200 + t * 6, self.time, morning=True)
        stages.bunting(surf, 30, self.time)
        stages.bunting(surf, 60, self.time + 1)
        stages.food_truck(surf, 300, 150)
        for i in range(4):
            x = (i * 90 + t * 20) % (W + 40) - 20
            img = art.citizen(i, "walk%d" % (int(t * 8 + i) % 4), 1)
            surf.blit(img, (int(x - art.HX - 1), int(190 + i * 6 - art.FEET_Y - 1)))
        crew = [("pops", 60), ("uncle_t", 90), ("stephen", 120), ("miles", 250), ("felix", 275)]
        for kind, x in crew:
            img = cast.guest_fig(kind, "victory" if int(t + x) % 3 == 0 else "idle0", 1 if x < 200 else -1)
            surf.blit(img, (x - art.HX - 1, 214 - art.FEET_Y - 1))
        surf.blit(art.mazee(int(t * 4), 1, False), (150, 196))
        hero = art.hero("victory" if int(t * 2) % 2 == 0 else "idle0", False, 1)
        surf.blit(hero, (200 - art.HX - 1, 216 - art.FEET_Y - 1))
        if t > 16:                         # the rift closes, and Mazee barks at it
            size = max(0.0, 1 - (t - 16) / 2.5)
            art.rift(surf, 340, 120, size, self.time)
            if 18.5 < t < 20:
                art.bubble(surf, "Woof!", 170, 186)
        box = pygame.Surface((220, 110), pygame.SRCALPHA)
        box.fill((10, 10, 30, 150))
        surf.blit(box, (90, 14))
        for i, line in enumerate(self.CREDITS):
            y = 124 + i * 16 - t * 14
            if 14 <= y <= 112:
                art.say(surf, line, (W // 2, int(y)), 18 if i == 0 else 16, (255, 220, 80) if i == 0 else (255, 255, 255))

    def render(self, surf):
        super().render(surf)
        if self.state == "over" and self.win:
            art.say(surf, "Confluence City is free!", (W // 2, 30), 22, c.YELLOW)


def make(**kw):
    return BlackWarrior(**kw)


if __name__ == "__main__":
    c.main(make)
