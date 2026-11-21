"""Alien Storm: Tom Cat Alley. Flight, enemies, bosses, weapons and scoring.

A vertical scrolling shooter for BMO. Cutscenes and the landing game live in scenes.py."""
import math

import pygame

from ..common import Game, W, H, WHITE, YELLOW, RED, INK, text
from . import art, world, lines

STAGES = [
    dict(name="Open Ocean", boss="lance", boss_name="THE LANCE", hp=260, tune="as_stage1"),
    dict(name="Storm Front", boss="thunderhead", boss_name="THE THUNDERHEAD", hp=330, tune="as_stage2"),
    dict(name="Island Chain", boss="leviathan", boss_name="THE LEVIATHAN", hp=420, tune="as_stage3"),
    dict(name="The Mothership", boss="core", boss_name="THE RED STAR", hp=560, tune="as_stage4"),
]
DIFF = [dict(dmg=0.55, rate=0.75, speed=0.85), dict(dmg=1.0, rate=1.0, speed=1.0), dict(dmg=1.4, rate=1.3, speed=1.15)]
STAGE_LEN = 78.0                # seconds of waves before the boss
SCROLL = 60.0
ENEMY = {  # hp, score, radius
    "fighter": (2, 100, 9), "interceptor": (3, 150, 10), "bomber": (16, 800, 22), "gunship": (11, 500, 16),
    "seeker": (1, 60, 7), "turret": (6, 250, 9),
}
CREWS = [dict(pilot="alex", rio="kj", skin=((140, 92, 60), (90, 56, 36)), squadron=1),
         dict(pilot="stephen", rio="heather", skin=((240, 200, 170), (246, 208, 182)), squadron=2)]
MAX_HEAT, MAX_LOOPS, MAX_LOCKS = 8, 3, 4
LOOP_TIME, LOCK_HOLD, LOCK_STEP, RADAR_RELOAD = 1.1, 0.28, 0.16, 2.6


def make_waves(stage, rng):
    """The script for one stage: a list of (time, kind, formation, count, x)."""
    out, t = [], 3.0
    kinds = [["fighter", "fighter", "interceptor", "bomber"],
             ["fighter", "interceptor", "gunship", "seeker", "bomber"],
             ["fighter", "interceptor", "gunship", "bomber", "seeker", "interceptor"],
             ["fighter", "turret", "gunship", "seeker", "interceptor", "turret", "bomber"]][stage]
    while t < STAGE_LEN:
        u = t / STAGE_LEN
        kind = rng.choice(kinds)
        if kind == "fighter":
            out.append((t, kind, rng.choice(("v", "line", "column")), rng.randrange(3, 6 + stage), rng.uniform(70, W - 70)))
        elif kind == "interceptor":
            out.append((t, kind, "side", rng.randrange(2, 4 + stage // 2), rng.choice((-1, 1))))
        elif kind == "bomber":
            out.append((t, kind, "one", 1, rng.uniform(80, W - 80)))
        elif kind == "gunship":
            out.append((t, kind, "one", 1 + (stage > 1 and u > 0.5), rng.uniform(100, W - 100)))
        elif kind == "seeker":
            out.append((t, kind, "line", rng.randrange(3, 6), rng.uniform(80, W - 80)))
        else:
            out.append((t, kind, "pair", 2, rng.uniform(70, W - 150)))
        t += rng.uniform(2.6, 4.4) - 1.2 * u - 0.25 * stage
    return out


class Jet:
    def __init__(self, slot):
        self.slot = slot
        self.crew = CREWS[slot]
        self.x, self.y = W / 2 + (-40 if slot == 0 else 40), H - 44
        self.hp, self.alive, self.safe = 100.0, True, 2.0
        self.sweep, self.burner = 1.0, 0.5
        self.gun, self.gun_t = 1, 0.0
        self.heat, self.loops, self.loop_t, self.loop_charge = 4, 2, 0.0, 0.0
        self.hold, self.locks, self.lock_t, self.reload = 0.0, [], 0.0, 0.0
        self.down_t, self.flash, self.smoke_t = 0.0, 0.0, 0.0

    @property
    def looping(self):
        return self.loop_t > 0

    def sprite(self):
        dmg = 0.0 if self.hp > 66 else (0.5 if self.hp > 33 else 0.9)
        return art.tomcat(round(self.sweep * 2) / 2, self.crew["squadron"], min(4, self.heat),
                          round(self.burner * 2.5) / 2.5, dmg, self.crew["skin"])


class AlienStorm(Game):
    name = "alien_storm"
    title = "Alien Storm"
    help_lines = ("Tom Cat Alley", "Guns fire on their own", "Tap big button: heat seeker   Hold: radar lock",
                  "Triangle: loop the loop")
    title_color = (255, 90, 80)
    music = None
    levels = tuple(s["name"] for s in STAGES)
    modes = ("Cadet", "Aviator", "Ace")
    players_max = 2
    scenes = True               # tests turn this off to stay in the air

    # ------------------------------------------------------------------ set up
    def __init__(self, seed=None, scores_path=None):
        super().__init__(seed=seed, scores_path=scores_path)
        self.scene, self.landing, self.talk = None, None, {}     # the title screen is drawn before any game starts

    def reset(self):
        self.score = 0
        self.win = False
        self.jets = [Jet(0)]
        self.spares = 2
        self.combo, self.combo_t, self.kills = 0, 0.0, 0
        self.talk = {}                              # side -> [who, mood, line, time left]
        self.quip_t = 0.0
        self.hits_taken = 0
        self.scene = None
        self.landing = None
        self.grades = []
        self.begin_stage(self.level_choice)
        if self.scenes:
            from . import scenes
            self.scene = scenes.takeoff(self, first=True)

    def begin_stage(self, stage):
        self.stage = stage
        self.reach_level(stage)
        self.diff = DIFF[self.mode]
        self.phase, self.phase_t = "flight", 0.0     # flight, warning, boss, clear
        self.t = 0.0
        self.scroll = 0.0
        self.waves = make_waves(stage, self.rng)
        self.enemies, self.shots, self.bolts, self.rockets = [], [], [], []
        self.fx, self.pickups, self.clouds, self.ground, self.hazards = [], [], [], [], []
        self.boss = None
        self.shake = 0.0
        self.flash = 0.0
        self.kill_count = 0
        for j in self.jets:
            j.x, j.y, j.safe = W / 2 + (-40 if j.slot == 0 else 40), H - 44, 2.0
            j.locks, j.hold = [], 0.0
            if j.alive:
                j.hp = min(100.0, j.hp + 40)
        for i in range(4):
            self.clouds.append([self.rng.uniform(-40, W - 80), self.rng.uniform(-60, H), self.rng.randrange(3), self.rng.uniform(1.3, 1.9)])
        if stage == 0:
            self.ground.append(["fleet", W / 2, H + 40])
        self.sound.music(STAGES[stage]["tune"])
        for who, mood, line in lines.STAGE_START[stage]:
            self.say(who, mood, line, 3.0)

    # ------------------------------------------------------------------ talk
    def say(self, who, mood, line, dur=2.2, force=False):
        side = 1 if who in ("stephen", "heather") else 0
        cur = self.talk.get(side)
        if cur and not force and cur[3] > 0.4 and cur[2] == lines.HIT_KJ:
            return
        self.talk[side] = [who, mood, line, dur]

    # ------------------------------------------------------------------ helpers
    def live_jets(self):
        return [j for j in self.jets if j.alive]

    def nearest_jet(self, x, y):
        js = [j for j in self.jets if j.alive and not j.looping] or self.live_jets()
        return min(js, key=lambda j: (j.x - x) ** 2 + (j.y - y) ** 2) if js else None

    def boom(self, x, y, size=14, n=1):
        for i in range(n):
            ox = self.rng.uniform(-size, size) * (i > 0)
            oy = self.rng.uniform(-size, size) * (i > 0)
            self.fx.append(["boom", x + ox, y + oy, -0.06 * i, size])

    def spawn(self, kind, x, y, **kw):
        hp, pts, r = ENEMY[kind]
        e = dict(kind=kind, x=x, y=y, hp=hp, pts=pts, r=r, t=0.0, x0=x, flash=0.0, fire=self.rng.uniform(0.6, 1.6), dir=1)
        e.update(kw)
        self.enemies.append(e)
        return e

    def spawn_wave(self, kind, form, n, x):
        if form == "v":
            for i in range(n):
                k = (i + 1) // 2 * (1 if i % 2 else -1)
                self.spawn(kind, x + k * 22, -14 - abs(k) * 14, ph=0.0)
        elif form == "line":
            for i in range(n):
                self.spawn(kind, min(W - 20, max(20, x + (i - (n - 1) / 2) * 26)), -14, ph=i * 0.5)
        elif form == "column":
            for i in range(n):
                self.spawn(kind, x, -14 - i * 22, ph=i * 0.7)
        elif form == "side":
            for i in range(n):
                self.spawn(kind, -16 - i * 30 if x > 0 else W + 16 + i * 30, 30 + i * 12, dir=x)
        elif form == "pair":
            self.spawn(kind, x, -14)
            self.spawn(kind, x + 80, -14)
        else:
            for i in range(n):
                self.spawn(kind, min(W - 30, max(30, x + i * 90)), -24)

    def bolt(self, x, y, ang, speed=95.0, kind=0):
        speed *= self.diff["speed"]
        self.bolts.append([x, y, math.cos(ang) * speed, math.sin(ang) * speed, kind])

    def aim(self, x, y):
        j = self.nearest_jet(x, y)
        return math.atan2(j.y - y, j.x - x) if j else math.pi / 2

    # ------------------------------------------------------------------ the frame
    def step(self, dt, inp):
        if self.state == "play" and (self.scene is not None or self.landing is not None):
            self.time += dt
            self.run_scene(dt, inp)
            return
        super().step(dt, inp)

    def run_scene(self, dt, inp):
        if self.scene is not None:
            if self.scene.update(dt, inp):
                done, self.scene = self.scene, None
                if done.after:
                    done.after()
        elif self.landing is not None:
            if self.landing.update(dt, inp):
                land, self.landing = self.landing, None
                land.after()

    @property
    def hd_only(self):
        return self.state == "play" and self.scene is not None

    def update(self, dt, inp):
        self.t += dt
        self.phase_t += dt
        self.scroll += SCROLL * dt
        self.shake = max(0.0, self.shake - dt)
        self.flash = max(0.0, self.flash - dt)
        self.quip_t = max(0.0, self.quip_t - dt)
        for side in list(self.talk):
            self.talk[side][3] -= dt
            if self.talk[side][3] <= 0:
                del self.talk[side]
        if self.combo_t > 0:
            self.combo_t -= dt
            if self.combo_t <= 0:
                self.combo = 0
        p2 = getattr(inp, "p2", None)
        if p2 is not None and len(self.jets) == 1 and (p2.pressed or p2.held):
            self.jets.append(Jet(1))
            self.say("heather", "grin", "Second crew is airborne!", 2.4)
            self.sfx("start")
        for j in self.jets:
            self.update_jet(j, inp if j.slot == 0 else p2, dt)
        self.update_script(dt)
        self.update_enemies(dt)
        if self.boss:
            self.update_boss(dt)
        self.update_shots(dt)
        self.update_world(dt)
        if not self.live_jets() and all(j.down_t <= 0 for j in self.jets):
            if self.spares > 0:
                for j in self.jets:
                    if self.spares > 0:
                        self.spares -= 1
                        j.alive, j.hp, j.safe, j.heat, j.loops = True, 100.0, 3.0, 4, 2
                        j.x, j.y = W / 2 + (-40 if j.slot == 0 else 40), H - 44
            else:
                self.game_over()

    # ------------------------------------------------------------------ the jets
    def update_jet(self, j, inp, dt):
        j.flash = max(0.0, j.flash - dt)
        if not j.alive:
            if j.down_t > 0:
                j.down_t -= dt
                j.y += 50 * dt
                j.smoke_t -= dt
                if j.smoke_t <= 0:
                    j.smoke_t = 0.05
                    self.fx.append(["smoke", j.x, j.y, 0.0, 6])
                if j.down_t <= 0:
                    self.boom(j.x, j.y, 22, 4)
                    self.sfx("as_boom_big")
                    self.shake = 0.5
            return
        if inp is None:
            return
        held = inp.held
        dx = ("right" in held) - ("left" in held)
        dy = ("down" in held) - ("up" in held)
        if inp.touch and j.slot == 0:
            tx, ty = inp.touch
            dx = max(-1, min(1, (tx - j.x) / 12))
            dy = max(-1, min(1, (ty - 30 - j.y) / 12))
        sp = 165.0 if not j.looping else 110.0
        j.x = max(18, min(W - 18, j.x + dx * sp * dt))
        j.y = max(40, min(H - 30, j.y + dy * sp * dt))
        j.sweep += ((0.5 if dy > 0 else 1.0) - j.sweep) * min(1, dt * 5)
        j.burner += ((1.0 if dy < 0 else (0.2 if dy > 0 else 0.6)) - j.burner) * min(1, dt * 6)
        j.safe = max(0.0, j.safe - dt)
        j.reload = max(0.0, j.reload - dt)
        if j.loops < MAX_LOOPS:
            j.loop_charge += dt
            if j.loop_charge >= 11:
                j.loop_charge, j.loops = 0.0, j.loops + 1
        if j.looping:
            j.loop_t = max(0.0, j.loop_t - dt)
        elif "b" in inp.pressed and j.loops > 0:
            j.loops -= 1
            j.loop_t = LOOP_TIME
            j.locks, j.hold = [], 0.0
            self.sfx("as_loop")
        # the Vulcan fires by itself whenever there is something to shoot
        j.gun_t -= dt
        if j.gun_t <= 0 and not j.looping and (self.enemies or self.boss):
            j.gun_t = 0.085
            gx = j.x - 4
            self.shots.append([gx, j.y - 22, 0.0, -420.0])
            if j.gun >= 2:
                self.shots.append([gx + 8, j.y - 22, 0.0, -420.0])
            if j.gun >= 3:
                self.shots.append([gx - 3, j.y - 18, -70.0, -410.0])
                self.shots.append([gx + 11, j.y - 18, 70.0, -410.0])
            self.fx.append(["muzzle", gx, j.y - 24, 0.0, 0])
            if int(self.t * 12) % 2 == 0:
                self.sfx("as_vulcan")
        if j.looping:
            return
        # big button: tap for a heat seeker, hold for the radar
        if "a" in held:
            j.hold += dt
            if j.hold > LOCK_HOLD and j.reload <= 0:
                j.lock_t -= dt
                if j.lock_t <= 0 and len(j.locks) < MAX_LOCKS:
                    j.lock_t = LOCK_STEP
                    taken = [id(t) for jj in self.jets for t in jj.locks]
                    cands = [e for e in self.enemies if 0 < e["y"] < H and id(e) not in taken]
                    if self.boss and self.boss_open() and len(j.locks) < MAX_LOCKS:
                        cands.append(self.boss)
                    if cands:
                        tgt = min(cands, key=lambda e: (e["x"] - j.x) ** 2 + (e["y"] - j.y) ** 2)
                        if tgt is self.boss and any(t is self.boss for t in j.locks) and len(cands) > 1:
                            tgt = min(cands[:-1], key=lambda e: (e["x"] - j.x) ** 2 + (e["y"] - j.y) ** 2)
                        j.locks.append(tgt)
                        self.sfx("as_lock")
        elif j.hold > 0:
            if j.locks:
                for i, tgt in enumerate(j.locks):
                    self.rockets.append(dict(kind="radar", x=j.x + (i - 1.5) * 6, y=j.y - 6, vx=(i - 1.5) * 40.0, vy=-60.0,
                                             tgt=tgt, t=0.0, dmg=13, slot=j.slot))
                self.sfx("as_radar")
                who = j.crew["rio"]
                if len(j.locks) >= MAX_LOCKS:
                    self.say(who, "grin", lines.LOCK[who], 1.8)
                j.reload = RADAR_RELOAD
            elif j.hold <= LOCK_HOLD and j.heat > 0:
                j.heat -= 1
                self.rockets.append(dict(kind="heat", x=j.x, y=j.y - 14, vx=0.0, vy=-200.0, tgt=None, t=0.0, dmg=7, slot=j.slot))
                self.sfx("as_heat")
            j.hold, j.locks = 0.0, []
        j.locks = [t for t in j.locks if t.get("hp", 0) > 0]
        if j.hp < 34:
            j.smoke_t -= dt
            if j.smoke_t <= 0:
                j.smoke_t = 0.09
                self.fx.append(["smoke", j.x + self.rng.uniform(-6, 6), j.y + 20, 0.0, 4])

    def hurt(self, j, amount):
        if not j.alive or j.looping or j.safe > 0:
            return
        j.hp -= amount * self.diff["dmg"]
        j.safe, j.flash = 0.7, 0.3
        self.shake = max(self.shake, 0.25)
        self.hits_taken += 1
        self.combo = 0
        self.sfx("as_hit")
        if j.slot == 0:
            self.say("kj", "alarm", lines.HIT_KJ, 2.0, force=True)      # every hit, exactly as written
        else:
            self.say("heather", "alarm", lines.HIT_HEATHER, 2.0, force=True)
        if j.hp <= 0:
            j.alive, j.down_t, j.locks, j.hold = False, 1.4, [], 0.0
            who = j.crew["rio"]
            self.talk[j.slot] = [who, "alarm", lines.DOWN[who], 2.4]

    # ------------------------------------------------------------------ the stage script
    def update_script(self, dt):
        if self.phase == "flight":
            while self.waves and self.waves[0][0] <= self.t:
                _, kind, form, n, x = self.waves.pop(0)
                self.spawn_wave(kind, form, n, x)
            if not self.waves and self.t > STAGE_LEN and not self.enemies:
                self.phase, self.phase_t = "warning", 0.0
                self.sound.music("as_boss")
                self.sfx("as_warning")
                for i, (who, mood, line) in enumerate(lines.BOSS[STAGES[self.stage]["boss"]][:1]):
                    self.say(who, mood, line, 3.0)
        elif self.phase == "warning":
            if int(self.phase_t * 2) != int((self.phase_t - dt) * 2) and self.phase_t < 2.6:
                self.sfx("as_warning")
            if self.phase_t > 3.0:
                st = STAGES[self.stage]
                self.boss = dict(kind=st["boss"], x=W / 2, y=-70.0, hp=float(st["hp"]), max=float(st["hp"]), t=0.0, r=30,
                                 flash=0.0, fire=1.5, fire2=3.0, mode="enter", mode_t=0.0, vis=1.0, dir=1, pts=5000, ang=0.0)
                self.phase, self.phase_t = "boss", 0.0
                who, mood, line = lines.BOSS[st["boss"]][1]
                self.say(who, mood, line, 2.6)
        elif self.phase == "clear":
            if int(self.phase_t * 9) != int((self.phase_t - dt) * 9) and self.phase_t < 2.6:
                self.boom(self.bx + self.rng.uniform(-50, 50), self.by + self.rng.uniform(-30, 30), self.rng.choice((14, 20, 26)))
                self.sfx("as_boom")
            if self.phase_t > 3.6:
                self.stage_done()

    def stage_done(self):
        self.score += 2000 * (self.stage + 1)
        if not self.scenes:
            self.next_stage()
            return
        from . import scenes
        self.sound.stop_music()
        self.scene = scenes.set_piece(self, self.stage)

    def next_stage(self):
        if self.stage + 1 >= len(STAGES):
            self.win = True
            self.game_over()
        else:
            self.begin_stage(self.stage + 1)

    # ------------------------------------------------------------------ enemies
    def update_enemies(self, dt):
        rate = self.diff["rate"]
        for e in self.enemies:
            e["t"] += dt
            e["flash"] = max(0.0, e["flash"] - dt)
            k, t = e["kind"], e["t"]
            if k == "fighter":
                e["y"] += 74 * dt
                e["x"] = e["x0"] + math.sin(t * 2.2 + e.get("ph", 0)) * 34
                e["fire"] -= dt * rate
                if e["fire"] <= 0 and 10 < e["y"] < 150:
                    e["fire"] = 2.2
                    self.bolt(e["x"], e["y"] + 10, self.aim(e["x"], e["y"]))
            elif k == "interceptor":
                e["x"] += e["dir"] * 150 * dt
                e["y"] = e["y"] + math.cos(t * 2.0) * 60 * dt + 18 * dt
                e["fire"] -= dt * rate
                if e["fire"] <= 0 and 20 < e["x"] < W - 20:
                    e["fire"] = 1.5
                    self.bolt(e["x"], e["y"] + 8, self.aim(e["x"], e["y"]), 120)
            elif k == "bomber":
                e["y"] += 26 * dt
                e["fire"] -= dt * rate
                if e["fire"] <= 0 and e["y"] > 0:
                    e["fire"] = 2.3
                    for a in (-0.45, 0, 0.45):
                        self.bolt(e["x"], e["y"] + 14, math.pi / 2 + a, 80, 1)
            elif k == "gunship":
                if e["y"] < 50 and t < 9:
                    e["y"] += 60 * dt
                elif t >= 9:
                    e["y"] -= 70 * dt
                else:
                    e["x"] += e["dir"] * 50 * dt
                    if e["x"] < 40 or e["x"] > W - 40:
                        e["dir"] *= -1
                e["fire"] -= dt * rate
                if e["fire"] <= 0 and e["y"] > 20:
                    e["burst"] = e.get("burst", 0) + 1
                    e["fire"] = 0.16 if e["burst"] % 4 else 1.7
                    self.bolt(e["x"] - 11, e["y"] + 18, self.aim(e["x"], e["y"]), 130)
                    self.bolt(e["x"] + 11, e["y"] + 18, self.aim(e["x"], e["y"]), 130)
            elif k == "seeker":
                j = self.nearest_jet(e["x"], e["y"])
                if j:
                    a = math.atan2(j.y - e["y"], j.x - e["x"])
                    e["x"] += math.cos(a) * 62 * dt
                    e["y"] += max(18.0, math.sin(a) * 62) * dt
                else:
                    e["y"] += 50 * dt
            else:                                       # turret, bolted to the hull
                e["y"] += SCROLL * dt
                e["fire"] -= dt * rate
                if e["fire"] <= 0 and 0 < e["y"] < H - 60:
                    e["fire"] = 1.6
                    self.bolt(e["x"], e["y"], self.aim(e["x"], e["y"]), 105)
            for j in self.live_jets():
                if not j.looping and (e["x"] - j.x) ** 2 + (e["y"] - j.y) ** 2 < (e["r"] + 9) ** 2 and k != "turret":
                    self.hurt(j, 18)
                    if k in ("seeker", "fighter", "interceptor"):
                        e["hp"] = 0
                        self.boom(e["x"], e["y"], 12)
        self.enemies = [e for e in self.enemies if e["hp"] > 0 and -80 < e["y"] < H + 40 and -140 < e["x"] < W + 140]

    def damage(self, e, dmg, slot=0):
        e["hp"] -= dmg
        e["flash"] = 0.07
        if e["hp"] > 0:
            return
        if e is self.boss:
            self.kill_boss()
            return
        self.kill_count += 1
        self.combo += 1
        self.combo_t = 2.6
        mult = min(8, 1 + self.combo // 5)
        self.score += e["pts"] * mult
        big = e["kind"] in ("bomber", "gunship")
        self.boom(e["x"], e["y"], 24 if big else 12, 4 if big else 1)
        self.sfx("as_boom_big" if big else "as_boom")
        self.fx.append(["pts", e["x"], e["y"], 0.0, e["pts"] * mult])
        if big:
            self.shake = max(self.shake, 0.3)
        if big or self.kill_count % 14 == 0:
            self.pickups.append([e["x"], e["y"], self.rng.choice("MMHLP" if big else "MMHP")])
        if self.quip_t <= 0 and (big or self.combo in (10, 25, 40)):
            self.quip_t = 7.0
            if slot == 0:
                self.say("kj", "grin", self.rng.choice(lines.KILL_KJ), 2.0)
            else:
                self.say("stephen", "grin", lines.OLD_MAN_STEPHEN, 2.0)

    # ------------------------------------------------------------------ bosses
    def boss_open(self):
        b = self.boss
        return b is not None and b["mode"] != "enter" and b["vis"] > 0.6 and b["hp"] > 0

    def kill_boss(self):
        b = self.boss
        self.bx, self.by = b["x"], b["y"]
        self.score += b["pts"] * (self.stage + 1)
        self.boss = None
        self.bolts, self.hazards = [], []
        for e in self.enemies:
            self.boom(e["x"], e["y"], 12)
        self.enemies = []
        self.phase, self.phase_t = "clear", 0.0
        self.shake, self.flash = 1.2, 0.5
        self.sfx("as_boom_big")
        self.sound.stop_music()
        self.say("alex", "grin", "Splash one big ugly!", 2.6, force=True)

    def update_boss(self, dt):
        b = self.boss
        b["t"] += dt
        b["mode_t"] += dt
        b["flash"] = max(0.0, b["flash"] - dt)
        rate = self.diff["rate"]
        frac = b["hp"] / b["max"]
        if b["mode"] == "enter":
            b["y"] += 60 * dt
            if b["y"] >= 54:
                b["mode"], b["mode_t"] = "sweep", 0.0
            return
        k = b["kind"]
        if k == "lance":
            if b["mode"] == "sweep":
                b["x"] += b["dir"] * (60 + 40 * (1 - frac)) * dt
                if b["x"] < 50 or b["x"] > W - 50:
                    b["dir"] *= -1
                b["fire"] -= dt * rate
                if b["fire"] <= 0:
                    b["fire"] = 1.3
                    for i in range(-3, 4):
                        self.bolt(b["x"], b["y"] + 40, math.pi / 2 + i * 0.2, 90)
                    self.sfx("as_shot")
                if b["mode_t"] > 6.5:
                    j = self.nearest_jet(b["x"], b["y"])
                    b["mode"], b["mode_t"], b["tx"] = "aim", 0.0, (j.x if j else W / 2)
            elif b["mode"] == "aim":                    # line up, glow, then stab down the screen
                b["x"] += (b["tx"] - b["x"]) * min(1, dt * 4)
                if b["mode_t"] > 1.0:
                    b["mode"], b["mode_t"] = "stab", 0.0
                    self.sfx("as_dive")
            elif b["mode"] == "stab":
                b["y"] += 330 * dt
                if b["y"] > H - 30:
                    b["mode"], b["mode_t"] = "back", 0.0
                    self.shake = 0.3
            elif b["mode"] == "back":
                b["y"] -= 120 * dt
                if b["y"] <= 54:
                    b["y"], b["mode"], b["mode_t"] = 54, "sweep", 0.0
                    if frac < 0.6:
                        self.spawn_wave("fighter", "line", 4, b["x"])
        elif k == "thunderhead":
            if b["mode"] == "sweep":
                b["x"] += b["dir"] * 44 * dt
                if b["x"] < 80 or b["x"] > W - 80:
                    b["dir"] *= -1
                b["fire"] -= dt * rate
                if b["fire"] <= 0:
                    b["fire"] = 1.9
                    for i in range(12):
                        self.bolt(b["x"], b["y"] + 10, i * math.tau / 12 + b["t"], 80, 1)
                    self.sfx("as_shot")
                b["fire2"] -= dt * rate
                if b["fire2"] <= 0:                     # lightning: a warning line, then the strike
                    b["fire2"] = 2.4 if frac > 0.5 else 1.5
                    for j in self.live_jets():
                        self.hazards.append(dict(kind="bolt", x=j.x + self.rng.uniform(-14, 14), t=0.0))
                    self.hazards.append(dict(kind="bolt", x=self.rng.uniform(30, W - 30), t=0.0))
                if b["mode_t"] > 7:
                    b["mode"], b["mode_t"] = "hide", 0.0
            elif b["mode"] == "hide":                   # fades into the cloud and comes back somewhere else
                b["vis"] = max(0.0, b["vis"] - dt * 1.6)
                if b["mode_t"] > 1.6:
                    b["x"] = self.rng.uniform(90, W - 90)
                    b["mode"], b["mode_t"] = "show", 0.0
                    self.spawn_wave("seeker", "line", 4, b["x"])
            else:
                b["vis"] = min(1.0, b["vis"] + dt * 1.6)
                if b["vis"] >= 1:
                    b["mode"], b["mode_t"] = "sweep", 0.0
        elif k == "leviathan":
            b["x"] = W / 2 + math.sin(b["t"] * 0.5) * 60
            b["fire"] -= dt * rate
            if b["fire"] <= 0:                          # wing tip turrets spiral
                b["fire"] = 0.22
                b["ang"] += 0.33
                for sx in (-88, 88):
                    self.bolt(b["x"] + sx, b["y"] - 16, math.pi / 2 + math.sin(b["ang"]) * 0.9, 100)
            b["fire2"] -= dt * rate
            if b["fire2"] <= 0:                         # the bays launch fighters
                b["fire2"] = 4.2 if frac > 0.5 else 3.0
                for sx in (-74, -52, 52, 74):
                    self.spawn("fighter", b["x"] + sx, b["y"] - 6, ph=sx * 0.1)
                self.sfx("as_launch")
            if frac < 0.4 and int(b["t"] / 3.5) != int((b["t"] - dt) / 3.5):
                for i in range(-4, 5):
                    self.bolt(b["x"], b["y"] + 44, math.pi / 2 + i * 0.17, 85, 1)
        else:                                           # the Red Star core, in three phases
            ph = 0 if frac > 0.66 else (1 if frac > 0.33 else 2)
            if ph != b.get("ph", 0):
                b["ph"] = ph
                self.flash, self.shake = 0.3, 0.6
                self.sfx("as_boom_big")
                self.boom(b["x"], b["y"], 26, 5)
                self.say("kj", "alarm", ("", "It's opening up! Watch those beams!", "It's coming apart! Pour it on!")[ph], 2.6)
            b["x"] = W / 2 + math.sin(b["t"] * 0.7) * (40 + 30 * ph)
            b["y"] = 58 + math.sin(b["t"] * 1.1) * 8
            b["ang"] += dt * (0.9 + 0.5 * ph)
            b["fire"] -= dt * rate
            if b["fire"] <= 0:
                b["fire"] = (0.5, 0.42, 0.2)[ph]
                n = (4, 3, 2)[ph]
                for i in range(n):
                    self.bolt(b["x"], b["y"], b["ang"] * (1 if ph < 2 else 1.7) + i * math.tau / n, 85 + 15 * ph, ph % 2)
            b["fire2"] -= dt * rate
            if b["fire2"] <= 0:
                b["fire2"] = (5.0, 3.4, 3.0)[ph]
                if ph >= 1:                             # sweeping beams, with a warning first
                    for j in self.live_jets():
                        self.hazards.append(dict(kind="bolt", x=j.x, t=0.0))
                    self.hazards.append(dict(kind="bolt", x=self.rng.uniform(30, W - 30), t=0.0))
                if ph != 1:
                    self.spawn_wave("seeker", "line", 3 + ph, b["x"])
        for j in self.live_jets():
            if self.boss_open() and not j.looping and abs(j.x - b["x"]) < b["r"] and abs(j.y - b["y"]) < b["r"] + 16:
                self.hurt(j, 25)

    # ------------------------------------------------------------------ bullets, missiles, pickups
    def targets(self):
        out = [e for e in self.enemies if e["y"] > -10]
        if self.boss_open():
            out.append(self.boss)
        return out

    def update_shots(self, dt):
        tg = self.targets()
        keep = []
        for s in self.shots:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            hit = False
            for e in tg:
                rr = e["r"] if e is not self.boss else e["r"] + 8
                if abs(s[0] - e["x"]) < rr and abs(s[1] - e["y"]) < rr and e["hp"] > 0:
                    self.damage(e, 1)
                    self.fx.append(["spark", s[0], s[1], 0.0, 0])
                    hit = True
                    break
            if not hit and s[1] > -8:
                keep.append(s)
        self.shots = keep
        keep = []
        for m in self.rockets:
            m["t"] += dt
            tgt = m["tgt"]
            if tgt is not None and tgt.get("hp", 0) <= 0:
                tgt = m["tgt"] = None
            if tgt is None and tg:
                live = [e for e in tg if e["hp"] > 0]
                if live:
                    tgt = min(live, key=lambda e: (e["x"] - m["x"]) ** 2 + (e["y"] - m["y"]) ** 2)
                    if m["kind"] == "radar":
                        m["tgt"] = tgt
            sp = 300.0 if m["kind"] == "heat" else 250.0
            if tgt is not None and m["t"] > 0.12:
                a = math.atan2(tgt["y"] - m["y"], tgt["x"] - m["x"])
                turn = 9.0 if m["kind"] == "heat" else 14.0
                m["vx"] += (math.cos(a) * sp - m["vx"]) * min(1, dt * turn)
                m["vy"] += (math.sin(a) * sp - m["vy"]) * min(1, dt * turn)
            else:
                m["vy"] += (-sp - m["vy"]) * min(1, dt * 4)
            m["x"] += m["vx"] * dt
            m["y"] += m["vy"] * dt
            if int(m["t"] * 40) != int((m["t"] - dt) * 40):
                self.fx.append(["trail", m["x"], m["y"], 0.0, 0 if m["kind"] == "heat" else 1])
            done = False
            for e in tg:
                rr = e["r"] + 4
                if e["hp"] > 0 and abs(m["x"] - e["x"]) < rr and abs(m["y"] - e["y"]) < rr:
                    self.boom(m["x"], m["y"], 10)
                    self.damage(e, m["dmg"], m["slot"])
                    done = True
                    break
            if not done and m["t"] < 3.0 and -20 < m["y"] < H + 20 and -20 < m["x"] < W + 20:
                keep.append(m)
        self.rockets = keep
        keep = []
        jets = [j for j in self.live_jets() if not j.looping]
        for b in self.bolts:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            hit = False
            for j in jets:
                if abs(b[0] - j.x) < 7 and abs(b[1] - j.y) < 12:
                    self.hurt(j, 10)
                    hit = True
                    break
            if not hit and -10 < b[1] < H + 10 and -10 < b[0] < W + 10:
                keep.append(b)
        self.bolts = keep
        for hz in self.hazards:
            hz["t"] += dt
            if 0.8 <= hz["t"] < 0.8 + dt * 1.5:
                self.sfx("as_thunder")
                self.flash = max(self.flash, 0.12)
            if 0.8 <= hz["t"] < 1.05:
                for j in jets:
                    if abs(j.x - hz["x"]) < 13:
                        self.hurt(j, 24)
        self.hazards = [hz for hz in self.hazards if hz["t"] < 1.15]
        keep = []
        for p in self.pickups:
            p[1] += 34 * dt
            got = None
            for j in self.live_jets():
                if abs(p[0] - j.x) < 16 and abs(p[1] - j.y) < 20:
                    got = j
                    break
            if got:
                if p[2] == "M":
                    got.heat = min(MAX_HEAT, got.heat + 3)
                elif p[2] == "H":
                    got.hp = min(100.0, got.hp + 30)
                elif p[2] == "L":
                    got.loops = min(MAX_LOOPS, got.loops + 1)
                else:
                    got.gun = min(3, got.gun + 1)
                self.score += 50
                self.sfx("as_pickup")
            elif p[1] < H + 10:
                keep.append(p)
        self.pickups = keep

    def update_world(self, dt):
        for c in self.clouds:
            c[1] += SCROLL * c[3] * dt
            if c[1] > H + 10:
                c[0], c[1], c[2] = self.rng.uniform(-40, W - 80), -90.0, self.rng.randrange(3)
        for g in self.ground:
            g[2] += SCROLL * 0.6 * dt
        self.ground = [g for g in self.ground if g[2] < H + 260]
        if self.stage == 2 and self.phase == "flight" and int(self.t / 3.2) != int((self.t - dt) / 3.2):
            self.ground.append(["island%d" % self.rng.randrange(4), self.rng.uniform(40, W - 40), -70.0])
        keep = []
        for f in self.fx:
            f[3] += dt
            life = {"boom": 0.5, "smoke": 0.6, "muzzle": 0.04, "spark": 0.1, "trail": 0.35, "pts": 0.8}[f[0]]
            if f[0] in ("smoke", "boom", "trail"):
                f[2] += SCROLL * 0.5 * dt
            if f[3] < life:
                keep.append(f)
        self.fx = keep[-220:]

    # ------------------------------------------------------------------ drawing
    def draw_title_art(self, surf):
        surf.blit(world.sea(0), (0, int(self.time * 40) % 480 - 480))
        surf.blit(world.sea(0), (0, int(self.time * 40) % 480))
        car = world.carrier_small()
        surf.blit(car, (40, 20))
        for i, x in enumerate((250, 320)):
            im = art.tomcat(1.0, i + 1, 4, 0.6 + 0.4 * math.sin(self.time * 9 + i))
            surf.blit(im, (x - 28, 120 + int(math.sin(self.time * 1.6 + i) * 6)))
        surf.blit(art.alien("bomber"), (230, 14))
        surf.blit(art.alien("fighter"), (200, 60))
        surf.blit(art.alien("fighter"), (330, 56))

    def draw(self, surf):
        if self.landing is not None:
            self.landing.draw(surf)
            return
        ox = int(self.rng.uniform(-3, 3)) if self.shake > 0 else 0
        oy = int(self.rng.uniform(-3, 3)) if self.shake > 0 else 0
        sea = world.sea(self.stage)
        off = int(self.scroll * (0.6 if self.stage != 3 else 1.0)) % 480
        surf.blit(sea, (ox, off - 480 + oy))
        surf.blit(sea, (ox, off + oy))
        for g in self.ground:
            if g[0] == "fleet":
                car = world.carrier_small()
                surf.blit(car, (int(g[1]) - car.get_width() // 2 + ox, int(g[2]) - 200 + oy))
                for dx, dy, kind in ((-120, -60, "destroyer"), (120, -90, "destroyer"), (-90, 110, "battleship"), (130, 80, "destroyer")):
                    im = world.ship(kind)
                    surf.blit(im, (int(g[1]) + dx - im.get_width() // 2 + ox, int(g[2]) - 200 + dy + oy))
            else:
                im = world.island(int(g[0][6:]))
                surf.blit(im, (int(g[1]) - im.get_width() // 2 + ox, int(g[2]) + oy))
        for e in self.enemies:
            if e["kind"] == "turret":
                self.draw_enemy(surf, e, ox, oy)
        if self.stage != 3:
            for c in self.clouds[:2]:
                surf.blit(world.cloud(self.stage, c[2]), (int(c[0]) + ox, int(c[1]) + oy))
        for f in self.fx:
            if f[0] == "smoke":
                r = int(f[4] + f[3] * 10)
                g = 70 + int(f[3] * 100)
                pygame.draw.circle(surf, (g, g, g), (int(f[1]) + ox, int(f[2]) + oy), r)
            elif f[0] == "trail":
                g = 230 - int(f[3] * 300)
                col = (g, g, g) if f[4] == 0 else (g - 40, g - 10, g)
                pygame.draw.circle(surf, col, (int(f[1]) + ox, int(f[2]) + oy), 2 if f[3] < 0.15 else 1)
        for p in self.pickups:
            surf.blit(world.pickup(p[2]), (int(p[0]) - 7 + ox, int(p[1]) - 7 + oy + int(math.sin(self.t * 6) * 1.5)))
        for e in self.enemies:
            if e["kind"] != "turret":
                self.draw_enemy(surf, e, ox, oy)
        if self.boss:
            self.draw_boss(surf, ox, oy)
        for hz in self.hazards:
            x = int(hz["x"]) + ox
            if hz["t"] < 0.8:
                if int(hz["t"] * 14) % 2 == 0:
                    pygame.draw.line(surf, (255, 240, 150), (x, 0), (x, H), 1)
                pygame.draw.polygon(surf, (255, 240, 150), [(x - 5, 2), (x + 5, 2), (x, 10)])
            else:
                pts, y = [(x, 0)], 0
                while y < H:
                    y += 16
                    pts.append((x + self.rng.randrange(-7, 8), y))
                pygame.draw.lines(surf, (150, 190, 255), False, pts, 7)
                pygame.draw.lines(surf, (255, 255, 255), False, pts, 3)
        for s in self.shots:
            pygame.draw.line(surf, (255, 240, 160), (int(s[0]) + ox, int(s[1]) + oy), (int(s[0] - s[2] * 0.016) + ox, int(s[1]) + 7 + oy), 2)
        for m in self.rockets:
            im = world.missile(m["kind"])
            ang = -math.degrees(math.atan2(m["vy"], m["vx"])) - 90
            im = pygame.transform.rotate(im, ang) if abs(ang) > 6 else im
            surf.blit(im, (int(m["x"]) - im.get_width() // 2 + ox, int(m["y"]) - im.get_height() // 2 + oy))
        for j in self.jets:
            self.draw_jet(surf, j, ox, oy)
        for b in self.bolts:
            x, y = int(b[0]) + ox, int(b[1]) + oy
            if b[4] == 0:
                pygame.draw.circle(surf, (255, 70, 70), (x, y), 3)
                pygame.draw.circle(surf, (255, 220, 200), (x, y), 1)
            else:
                pygame.draw.circle(surf, (90, 170, 255), (x, y), 4)
                pygame.draw.circle(surf, (230, 245, 255), (x, y), 2)
        for f in self.fx:
            if f[0] == "boom" and f[3] >= 0:
                frames = world.boom(f[4])
                im = frames[min(9, int(f[3] / 0.5 * 10))]
                surf.blit(im, (int(f[1]) - f[4] + ox, int(f[2]) - f[4] + oy))
            elif f[0] == "muzzle":
                pygame.draw.circle(surf, (255, 250, 200), (int(f[1]) + ox, int(f[2]) + oy), 3)
            elif f[0] == "spark":
                pygame.draw.circle(surf, (255, 255, 255), (int(f[1]) + ox, int(f[2]) + oy), 2)
            elif f[0] == "pts":
                text(surf, str(f[4]), (int(f[1]), int(f[2] - f[3] * 26)), 14, YELLOW, center=True)
        if self.stage != 3:
            for c in self.clouds[2:]:
                surf.blit(world.cloud(self.stage, c[2]), (int(c[0]) + ox, int(c[1]) + oy))
        if self.stage == 1:                             # rain
            for i in range(26):
                x = (i * 53 + int(self.t * 240)) % (W + 40) - 20
                y = (i * 97 + int(self.t * 520)) % H
                pygame.draw.line(surf, (150, 170, 190), (x, y), (x - 3, y + 9))
        if self.flash > 0:
            surf.fill((70, 70, 70), special_flags=pygame.BLEND_RGB_ADD)
        self.draw_hud(surf)

    def draw_enemy(self, surf, e, ox, oy):
        k = e["kind"]
        im = world.extra_alien(k) if k in ("seeker", "turret") else art.alien(k)
        x, y = int(e["x"]) - im.get_width() // 2 + ox, int(e["y"]) - im.get_height() // 2 + oy
        surf.blit(im, (x, y))
        if e["flash"] > 0:
            surf.blit(im, (x, y), special_flags=pygame.BLEND_RGB_ADD)
            surf.blit(im, (x, y), special_flags=pygame.BLEND_RGB_ADD)

    def draw_boss(self, surf, ox, oy):
        b = self.boss
        im = world.boss(b["kind"], b["flash"] > 0)
        if b["vis"] < 1:
            im = im.copy()
            im.set_alpha(int(255 * max(0.08, b["vis"])))
        if b["kind"] == "core":
            im = pygame.transform.rotate(im, math.degrees(b["ang"]) % 360)
        if b["kind"] == "lance" and b["mode"] == "aim" and int(b["mode_t"] * 12) % 2 == 0:
            pygame.draw.line(surf, (255, 90, 90), (int(b["x"]) + ox, int(b["y"]) + 50), (int(b["x"]) + ox, H), 1)
        surf.blit(im, (int(b["x"]) - im.get_width() // 2 + ox, int(b["y"]) - im.get_height() // 2 + oy))

    def draw_jet(self, surf, j, ox, oy):
        if not j.alive and j.down_t <= 0:
            return
        im = j.sprite()
        if j.looping:                                   # up, over the top and back down
            u = 1 - j.loop_t / LOOP_TIME
            k = 1 + 0.55 * math.sin(u * math.pi)
            sy = math.cos(u * math.tau)
            im = pygame.transform.scale(im, (int(56 * k), max(4, int(72 * k * abs(sy)))))
            if sy < 0:
                im = pygame.transform.flip(im, False, True)
        elif not j.alive:
            im = pygame.transform.rotate(im, (1.4 - j.down_t) * 260)
        elif j.safe > 0 and int(self.t * 16) % 2 == 0 and j.flash <= 0:
            return
        x, y = int(j.x) - im.get_width() // 2 + ox, int(j.y) - im.get_height() // 2 + oy
        surf.blit(im, (x, y))
        if j.flash > 0:
            surf.blit(im, (x, y), special_flags=pygame.BLEND_RGB_ADD)
        if j.alive and j.hold > LOCK_HOLD and j.reload <= 0:   # KJ's radar sweep and the lock diamonds
            a = self.t * 7
            pygame.draw.arc(surf, (120, 255, 140), (int(j.x) - 60 + ox, int(j.y) - 60 + oy, 120, 120), a, a + 1.0, 1)
        col = (120, 255, 140) if j.slot == 0 else (255, 200, 90)
        for tgt in j.locks:
            cx, cy, r = int(tgt["x"]) + ox, int(tgt["y"]) + oy, 11 + int(math.sin(self.t * 14) * 2)
            pygame.draw.polygon(surf, col, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], 1)

    def draw_hud(self, surf):
        for j in self.jets:
            x = 6 if j.slot == 0 else W - 96
            pygame.draw.rect(surf, INK, (x - 1, 5, 92, 9))
            col = (90, 220, 110) if j.hp > 50 else ((240, 200, 60) if j.hp > 25 else RED)
            pygame.draw.rect(surf, col, (x, 6, int(90 * max(0, j.hp) / 100), 7))
            text(surf, CREWS[j.slot]["pilot"].upper(), (x + 2, 5), 12, WHITE, shadow=False)
            for i in range(j.heat):
                pygame.draw.rect(surf, (236, 236, 240), (x + i * 5, 17, 3, 7))
                pygame.draw.rect(surf, (220, 60, 60), (x + i * 5, 17, 3, 2))
            for i in range(j.loops):
                pygame.draw.circle(surf, (120, 190, 255), (x + 50 + i * 9, 20), 3, 1)
            if j.reload > 0:
                pygame.draw.rect(surf, (120, 255, 140), (x + 78, 17, int(12 * (1 - j.reload / RADAR_RELOAD)), 3))
        text(surf, "%07d" % int(self.score), (W // 2, 4), 18, WHITE, center=True)
        if self.combo >= 5:
            text(surf, "x%d" % min(8, 1 + self.combo // 5), (W // 2, 18), 16, YELLOW, center=True)
        if self.spares:
            text(surf, "JETS %d" % self.spares, (W // 2 + 44, 6), 12, WHITE)
        if self.phase == "warning" and int(self.phase_t * 4) % 2 == 0:
            pygame.draw.rect(surf, (200, 30, 30), (0, 96, W, 30))
            text(surf, "WARNING", (W // 2, 98), 34, YELLOW, center=True)
        if self.boss:
            b = self.boss
            pygame.draw.rect(surf, INK, (119, 30, 162, 6))
            pygame.draw.rect(surf, (230, 60, 70), (120, 31, int(160 * max(0, b["hp"]) / b["max"]), 4))
            text(surf, STAGES[self.stage]["boss_name"], (W // 2, 37), 12, WHITE, center=True)
        if self.phase == "flight" and self.t < 3:
            text(surf, "STAGE %d" % (self.stage + 1), (W // 2, 84), 30, YELLOW, center=True)
            text(surf, STAGES[self.stage]["name"].upper(), (W // 2, 110), 22, WHITE, center=True)

    # ------------------------------------------------------------------ full resolution overlay
    def render_hd(self, screen):
        from . import hud
        if self.state == "play" and self.scene is not None:
            self.scene.draw(screen)
        elif self.state in ("play", "paused") and self.landing is None:
            hud.talk(screen, self.talk)
        elif self.landing is not None and self.state == "play":
            self.landing.draw_hd(screen)
