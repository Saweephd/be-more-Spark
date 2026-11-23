"""Vampires, Oh Well...

Lucas is a daywalker: half vampire, fine in sunlight, and hard to impress. He drives to work at
Brightwell Remedies (an invented company) and finds the night shift never left: zombies, bats, skeletons,
werewolves, ghosts and vampires on every floor. Five floors, a boss on each.

D-pad: walk. Big circle: jump (down + jump drops through a ledge). Triangle: attack.
Up + triangle: play the card you hold. A second controller brings in a second hunter at any time.
Cards are found in chests: play stops, the card is shown, the big button turns it over.
"""
import math

import pygame

from .. import common as c
from ..alien_storm import hud
from ..common import H, W, Game, text
from . import art, cards, levels, scenes

FLOOR = levels.FLOOR
GRAV, JUMP = 900.0, -335.0
MODES = ((0.75, 0.9), (1.0, 1.0), (1.4, 1.2))            # monster health and speed, by difficulty
MAX_HP, LIVES = 8, 3
# kind: health, speed, points
BEASTS = {"zombie": (2, 28, 100), "skeleton": (2, 22, 150), "wolf": (3, 84, 200), "bat": (1, 62, 80),
          "ghost": (2, 34, 150), "vampire": (4, 40, 300)}
UNLOCKS = (2, 3, 4, 6, 8)                                # hunters available once this many floors are reached

QUIPS = ("Monday.", "I was told there would be coffee.", "That's going in my report.", "Not my department.", "Sheesh.")
WIN_LINE = "I don't really care about winning, but I still win. Sheesh."
BOSS_LINE = "Do you have an appointment?"
OTHERS = {"poppa": ("I am not angry. THIS is angry.", "Who left these monsters on?", "In my day, zombies had manners."),
          "whitney": ("Label it and move on.", "This is NOT in the moving plan."),
          "rose": ("I have Mahjong at four.", "Mind your manners, young vampire."),
          "heather": ("Count it! One, two, whack.", "See me after class."),
          "stephen": ("Not bad for an old man.", "Have you tried turning it off?"),
          "alex": ("I make this ish look good.", "I have an improv show after this."),
          "kj": ("Nothing but net.", "Just like the team I coach.")}


class Hunter:
    def __init__(self, kind, slot, x):
        self.kind, self.slot = kind, slot
        self.d = art.HUNTERS[kind]
        self.x, self.y, self.vx, self.vy = float(x), float(FLOOR), 0.0, 0.0
        self.face, self.ground = 1, True
        self.hp, self.lives = MAX_HP, LIVES
        self.inv = self.attack_t = self.cool = self.hurt_t = 0.0
        self.walk_t = 0.0
        self.card = None
        self.fx = {}                                      # running card effects: name -> seconds left
        self.staples, self.rosary, self.fire = 0, False, False
        self.safe = (float(x), float(FLOOR))
        self.out = False
        self.struck = set()

    @property
    def box(self):
        return pygame.Rect(int(self.x) - 7, int(self.y) - 38, 14, 38)

    def reach(self):
        return self.d["reach"] + (14 if self.fire else 0)

    def damage(self):
        return self.d["damage"] * (2 if self.fire else 1)


class Beast:
    def __init__(self, kind, x, y, hp, speed, look=None, scale=1.0, boss=None):
        self.kind, self.look, self.scale, self.boss = kind, look, scale, boss
        self.x, self.y, self.vx, self.vy = float(x), float(y), 0.0, 0.0
        self.hp = self.max_hp = hp
        self.speed = speed
        self.face = -1
        self.t = 0.0
        self.act = 1.5                                    # seconds until the next special move
        self.flash = 0.0
        self.ground = kind not in ("bat", "ghost")
        w, h = art.SIZES[kind]
        self.w, self.h = int(w * scale * 0.6), int(h * scale * 0.86)
        self.home_y = float(y)
        self.dead = False

    @property
    def box(self):
        return pygame.Rect(int(self.x) - self.w // 2, int(self.y) - self.h, self.w, self.h)

    def flies(self):
        return self.kind in ("bat", "ghost") or (self.boss and self.boss["move"] == "float")


class Vampires(Game):
    name = "vampires"
    title = "Vampires, Oh Well..."
    title_color = (230, 60, 80)
    music = "vampires"
    levels = levels.NAMES
    modes = ("Intern", "Staff", "Night Shift")
    players_max = 2
    help_lines = ("Circle: jump   Triangle: attack", "Up + triangle: play your card")

    def __init__(self, **kw):
        super().__init__(**kw)
        saved = c.load_scores(self.scores_path)
        self.found = int(saved.get(self.name + "_cards", 0))         # one bit per card in the album
        self.finished = bool(saved.get(self.name + "_done", 0))
        self.p1_kind, self.p2_kind = "lucas", "poppa"
        self.album = None                                            # [index, turn, target] while the album is open
        self.scene = None
        self.cardview = None
        self.players, self.beasts, self.shots, self.drops, self.pops = [], [], [], [], []
        self.level = levels.build(0)
        self.cam = 0.0
        self.stage = 0
        self.say_line, self.say_t, self.say_who = "", 0.0, "lucas"
        self.banner, self.banner_t = "", 0.0
        self.boss_on = False
        self.clear_t = 0.0

    # ------------------------------------------------------------ title screen extras
    def roster(self):
        return art.ROSTER[:UNLOCKS[min(len(UNLOCKS), self.unlocked) - 1]]

    def title_options(self):
        rows = super().title_options() + ["p2"]
        if self.finished:
            rows.append("p1")
        return rows

    def title_input(self, inp):
        rows = self.title_options()
        self.option_row = min(self.option_row, len(rows) - 1)
        row = rows[self.option_row]
        step = (1 if "right" in inp.pressed else 0) - (1 if "left" in inp.pressed else 0)
        if row in ("p1", "p2") and step:
            names = self.roster()
            cur = self.p1_kind if row == "p1" else self.p2_kind
            new = names[(names.index(cur) + step) % len(names)] if cur in names else names[0]
            if row == "p1":
                self.p1_kind = new
            else:
                self.p2_kind = new
            self.sfx("select")
            return
        super().title_input(inp)

    def step(self, dt, inp):
        if self.state == "title":
            if self.album is not None:
                self.time += dt
                a = self.album
                a[1] += max(-dt * 4, min(dt * 4, a[2] - a[1]))
                if "b" in inp.pressed or "start" in inp.pressed:
                    self.album = None
                elif "a" in inp.pressed:
                    if self.found >> a[0] & 1:
                        a[2] = 0.0 if a[2] else 1.0
                        self.sfx("select")
                else:
                    move = (1 if "right" in inp.pressed else 0) - (1 if "left" in inp.pressed else 0)
                    if move:
                        self.album = [(a[0] + move) % len(cards.KEYS), 0.0, 0.0]
                        self.sfx("move")
                return
            if "b" in inp.pressed:
                self.album = [0, 0.0, 0.0]
                self.sfx("select")
                return
        super().step(dt, inp)

    # ------------------------------------------------------------ set-up
    def reset(self):
        self.score = 0
        self.win = False
        self.players = [Hunter(self.p1_kind, 0, 60)]
        self.start_stage(self.level_choice)
        if self.level_choice == 0 and getattr(self, "scenes_on", True):
            self.scene = scenes.Opening()

    def start_stage(self, index):
        self.stage = index
        self.reach_level(index)
        self.level = levels.build(index)
        self.spawn_i = 0
        self.beasts, self.shots, self.drops, self.pops = [], [], [], []
        self.lamps = [list(p) for p in self.level["lamps"]]
        self.chests = [list(p) for p in self.level["chests"]]
        self.chest_cards = self.pick_cards(index)
        self.boss_on, self.clear_t = False, 0.0
        self.cam = 0.0
        self.cardview = None
        for i, p in enumerate(self.players):
            p.x, p.y, p.vx, p.vy = 60.0 + i * 24, float(FLOOR), 0.0, 0.0
            p.safe = (p.x, p.y)
            p.fire = False
            p.fx = {}
            if p.out:
                p.out, p.lives, p.hp = False, 1, MAX_HP
        self.banner, self.banner_t = "Floor %d: %s" % (index + 1, self.level["name"]), 3.0
        self.talk(self.players[0], self.rng.choice(QUIPS[:4]) if self.players[0].kind == "lucas" else None)
        self.sound.music("vampires")

    def pick_cards(self, index):
        """Two cards for this floor's chests: ones not yet in the album come first."""
        order = list(cards.KEYS[index * 2 % len(cards.KEYS):]) + list(cards.KEYS[:index * 2 % len(cards.KEYS)])
        fresh = [k for k in order if not self.found >> cards.KEYS.index(k) & 1]
        return (fresh + [k for k in order if k not in fresh])[:2]

    def talk(self, hunter, line=None, seconds=3.0):
        if line is None:
            line = self.rng.choice(OTHERS.get(hunter.kind, QUIPS))
        self.say_line, self.say_t, self.say_who = line, seconds, hunter.kind

    # ------------------------------------------------------------ the world
    def ground_at(self, x):
        return any(a <= x <= b for a, b in self.level["ground"])

    def land_y(self, x, y0, y1, drop=False):
        """The surface a falling body meets between heights y0 and y1 at x, or None."""
        best = None
        if not drop:
            for lx, ly, lw in self.level["ledges"]:
                if lx <= x <= lx + lw and y0 <= ly <= y1:
                    best = ly if best is None else min(best, ly)
        if self.ground_at(x) and y0 <= FLOOR <= y1:
            best = FLOOR if best is None else min(best, FLOOR)
        return best

    def nearest(self, x):
        live = [p for p in self.players if not p.out]
        return min(live, key=lambda p: abs(p.x - x)) if live else None

    def spawn_beast(self, kind, x):
        hp, speed, _ = BEASTS[kind]
        mh, ms = MODES[self.mode]
        y = FLOOR if kind not in ("bat", "ghost") else self.rng.choice((120, 140, 160))
        look = "mummy" if kind == "skeleton" and self.rng.random() < 0.3 else None
        self.beasts.append(Beast(kind, x, y, max(1, int(round(hp * mh))), speed * ms, look))

    def start_boss(self):
        self.boss_on = True
        b = self.level["boss"]
        left = self.level["length"] - levels.ARENA
        mh, ms = MODES[self.mode]
        speed = BEASTS[b["kind"]][1] * ms
        for i in range(2 if b.get("pair") else 1):
            y = FLOOR if b["move"] != "float" else 130
            look = b["look"] if i == 0 else None
            self.beasts.append(Beast(b["kind"], left + 300 - i * 90, y, int(b["hp"] * mh), speed, look, b["scale"], dict(b)))
        self.banner, self.banner_t = b["name"], 3.0
        self.talk(self.players[0], BOSS_LINE if self.players[0].kind == "lucas" else None)
        self.sound.music("vampires_boss")

    # ------------------------------------------------------------ hunters
    def join(self, inp):
        p2 = getattr(inp, "p2", None)
        if p2 is not None and len(self.players) == 1 and ("a" in p2.pressed or "start" in p2.pressed):
            kind = self.p2_kind if self.p2_kind != self.players[0].kind else next(k for k in art.ROSTER if k != self.players[0].kind)
            h = Hunter(kind, 1, self.players[0].x - 20)
            h.y = self.players[0].safe[1]
            h.x = self.players[0].safe[0]
            self.players.append(h)
            self.talk(h)
            self.sfx("start")

    def update_hunter(self, p, inp, dt):
        if p.out:
            return
        fast = 1.45 if "coffee" in p.fx else 1.0
        for k in list(p.fx):
            p.fx[k] -= dt
            if p.fx[k] <= 0:
                del p.fx[k]
        p.inv = max(0.0, p.inv - dt)
        p.cool = max(0.0, p.cool - dt)
        p.attack_t = max(0.0, p.attack_t - dt)
        p.hurt_t = max(0.0, p.hurt_t - dt)
        bat = "bat" in p.fx
        move = (1 if "right" in inp.held else 0) - (1 if "left" in inp.held else 0)
        if p.hurt_t <= 0:
            p.vx = move * p.d["speed"] * fast * (1.3 if bat else 1.0)
            if move:
                p.face = move
                p.walk_t += dt
        if bat:
            p.vy = ((1 if "down" in inp.held else 0) - (1 if "up" in inp.held or "a" in inp.held else 0)) * 120.0
            p.ground = False
        else:
            if "a" in inp.pressed and p.ground:
                if "down" in inp.held and p.y < FLOOR:
                    p.y += 3                              # step off the ledge
                    p.ground = False
                    p.drop = 0.18
                else:
                    p.vy = JUMP
                    p.ground = False
                    self.sfx("jump")
            p.vy += GRAV * dt
        p.drop = max(0.0, getattr(p, "drop", 0.0) - dt)
        left_wall = (self.level["length"] - levels.ARENA + 6) if self.boss_on else self.cam + 6
        p.x = max(left_wall, min(min(self.level["length"], self.cam + W) - 6, p.x + p.vx * dt))
        y0 = p.y
        p.y += p.vy * dt
        if bat:
            p.y = max(40.0, min(float(FLOOR), p.y))
        elif p.vy >= 0:
            surface = self.land_y(p.x, y0 - 0.01, p.y + 0.01, drop=p.drop > 0)
            if surface is not None:
                p.y, p.vy, p.ground = float(surface), 0.0, True
                p.safe = (p.x, p.y)
            else:
                p.ground = False
        if p.y > H + 30:                                  # fell down a hole
            p.x, p.y = p.safe
            p.vy = 0.0
            self.hurt(p, 2, 0, force=True)
        # attack, or play the card
        if "b" in inp.pressed and p.cool <= 0 and not bat:
            if "up" in inp.held and p.card:
                self.play_card(p)
            else:
                p.attack_t, p.cool = 0.18, p.d["cool"] / fast
                p.struck = set()
                self.sfx("whiff")
                if p.staples > 0:
                    p.staples -= 1
                    self.shots.append(dict(x=p.x + p.face * 12, y=p.y - 22, vx=p.face * 260.0, vy=0.0, kind="staple", foe=False,
                                           dmg=2, ttl=1.2, owner=p))
        if p.attack_t > 0:
            r = p.reach()
            hit = pygame.Rect(int(p.x) + (4 if p.face > 0 else -4 - r), int(p.y) - 34, r, 26)
            self.strike(p, hit, p.damage())
        if "garlic" in p.fx or "hallpass" in p.fx:
            for b in self.beasts:
                near = abs(b.x - p.x) < (30 if "garlic" in p.fx else 46) and abs((b.y - b.h / 2) - (p.y - 20)) < 44
                if near and b.flash <= 0:
                    self.wound(b, 1, p, push=140 if "garlic" in p.fx else 60)

    def strike(self, p, rect, dmg):
        for b in self.beasts:
            if id(b) not in p.struck and rect.colliderect(b.box):
                p.struck.add(id(b))
                self.wound(b, dmg, p)
        for lamp in list(self.lamps):
            if rect.collidepoint(lamp[0], lamp[1] - 10):
                self.lamps.remove(lamp)
                self.sfx("gem")
                self.score += 20
                if self.rng.random() < 0.45:
                    self.drops.append(dict(x=float(lamp[0]), y=float(lamp[1]) - 12, kind="heart", vy=-90.0, floor=lamp[1]))
        for i, chest in enumerate(self.chests):
            if chest and rect.collidepoint(chest[0], chest[1] - 8):
                self.drops.append(dict(x=float(chest[0]), y=float(chest[1]) - 14, kind="card", vy=-150.0, floor=chest[1],
                                       card=self.chest_cards[i % len(self.chest_cards)]))
                self.chests[i] = None
                self.sfx("combo")

    def wound(self, b, dmg, p=None, push=90):
        if b.dead:
            return
        b.hp -= dmg
        b.flash = 0.14
        if not b.boss and p is not None:
            b.vx = push * (1 if b.x >= p.x else -1)
            b.stun = 0.25
        self.sfx("punch" if b.hp > 0 else "boom")
        if b.hp <= 0:
            b.dead = True
            self.score += 2500 if b.boss else BEASTS[b.kind][2]
            self.pops.append([b.x, b.y - b.h, "+%d" % (2500 if b.boss else BEASTS[b.kind][2]), 0.7])
            if not b.boss and self.rng.random() < 0.12:
                self.drops.append(dict(x=b.x, y=b.y - 12, kind="heart", vy=-90.0, floor=FLOOR if self.ground_at(b.x) else b.y))
            if p is not None and not b.boss and self.rng.random() < 0.1:
                self.talk(p, self.rng.choice(QUIPS) if p.kind == "lucas" else None, 2.2)

    def hurt(self, p, dmg, from_x, force=False):
        if p.out or ((p.inv > 0 or "bat" in p.fx) and not force):
            return
        p.hp -= dmg
        p.inv, p.hurt_t = 1.3, 0.3
        if not force:
            p.vx = 130.0 * (1 if p.x >= from_x else -1)
            p.vy = -170.0
            p.ground = False
        self.sfx("hurt")
        if p.hp <= 0:
            if p.rosary:
                p.rosary, p.hp = False, MAX_HP
                self.pops.append([p.x, p.y - 44, "Rosary!", 1.2])
                self.sfx("heart")
                return
            p.lives -= 1
            if p.lives <= 0:
                p.out = True
                if all(q.out for q in self.players):
                    self.game_over()
                return
            p.hp = MAX_HP
            p.x, p.y = p.safe
            p.inv = 2.5

    def play_card(self, p):
        key, p.card = p.card, None
        secs = cards.info(key)[4]
        self.sfx("combo")
        self.pops.append([p.x, p.y - 46, cards.info(key)[1], 1.2])
        if key == "dawn":
            self.dawn = 0.6
            for b in self.beasts:
                if self.cam - 20 <= b.x <= self.cam + W + 20:
                    self.wound(b, 6, None)
        elif key == "stapler":
            p.staples = 30
        else:
            p.fx[key] = float(secs)

    def take_card(self, p, key):
        self.cardview = dict(key=key, p=p, turn=0.0, target=0.0, t=0.0)
        bit = 1 << cards.KEYS.index(key)
        if not self.found & bit:
            self.found |= bit
            c.save_score(self.name + "_cards", self.found, self.scores_path, best=False)
        self.sfx("win")

    def close_card(self):
        v, self.cardview = self.cardview, None
        p, key = v["p"], v["key"]
        if key == "rosary":
            p.rosary = True
        elif key == "fire":
            p.fire = True
        else:
            p.card = key                                  # a card already held is swapped out

    # ------------------------------------------------------------ monsters
    def update_beast(self, b, dt):
        b.t += dt
        b.flash = max(0.0, b.flash - dt)
        b.act -= dt
        target = self.nearest(b.x)
        if target is None:
            return
        dx = target.x - b.x
        b.face = 1 if dx > 0 else -1
        stun = getattr(b, "stun", 0.0)
        if stun > 0:
            b.stun = stun - dt
            b.x += b.vx * dt
        elif b.boss:
            self.boss_moves(b, target, dx, dt)
        elif b.kind == "zombie":
            b.x += b.face * b.speed * dt
        elif b.kind == "skeleton":
            if abs(dx) > 130:
                b.x += b.face * b.speed * dt
            elif abs(dx) < 80:
                b.x -= b.face * b.speed * dt
            if b.act <= 0 and abs(dx) < 220:
                b.act = 2.4
                self.shots.append(dict(x=b.x, y=b.y - 34, vx=dx / 1.1, vy=-230.0, kind="bone", foe=True, dmg=1, ttl=3.0, grav=True))
        elif b.kind == "wolf":
            if b.ground:
                b.x += b.face * b.speed * dt
                if abs(dx) < 80 and b.act <= 0:
                    b.act, b.vy, b.ground, b.vx = 1.6, -250.0, False, b.face * 150.0
            else:
                b.x += b.vx * dt
        elif b.kind == "bat":
            b.x += b.face * b.speed * dt
            b.y = b.home_y + math.sin(b.t * 4) * 16 + min(40.0, b.t * 10)
        elif b.kind == "ghost":
            b.x += b.face * b.speed * dt
            b.y += max(-30 * dt, min(30 * dt, (target.y - 6) - b.y)) + math.sin(b.t * 3) * 0.4
        elif b.kind == "vampire":
            b.x += b.face * b.speed * dt
            if b.act <= 0 and abs(dx) < 200:
                b.act = 3.2
                b.x = max(self.cam + 16, min(self.cam + W - 16, target.x - b.face * 50))
                self.sfx("select")
        if not b.flies() and b.kind != "bat":
            b.vy += GRAV * dt
            y0 = b.y
            b.y += b.vy * dt
            if b.vy >= 0:
                surface = self.land_y(b.x, y0 - 0.01, b.y + 0.01, drop=True)
                if surface is not None:
                    b.y, b.vy, b.ground = float(surface), 0.0, True
                elif not self.ground_at(b.x) and b.ground and not b.boss:      # do not walk into holes
                    b.x -= b.face * b.speed * dt * 2
                    b.y, b.vy = y0, 0.0
            if b.y > H + 60:
                b.dead = True
        if self.boss_on:
            left = self.level["length"] - levels.ARENA
            b.x = max(left + 14, min(self.level["length"] - 14, b.x))
        for p in self.players:
            if not p.out and b.box.colliderect(p.box):
                self.hurt(p, 2 if b.boss else 1, b.x)

    def boss_moves(self, b, target, dx, dt):
        spec = b.boss
        move, attack = spec["move"], spec["attack"]
        if spec.get("forms"):                             # the Chairman changes his ways as he weakens
            part = b.hp / float(b.max_hp)
            move, attack = (("blink", "orb") if part > 0.66 else (("float", "scream") if part > 0.33 else ("leap", "wave")))
            if move != getattr(b, "form", move):
                self.banner, self.banner_t = "The Chairman changes shape!", 2.0
                b.y, b.vy = (120.0 if move == "float" else float(FLOOR)), 0.0
            b.form = move
            spec = dict(spec, move=move)
            b.boss["move"] = move
        left = self.level["length"] - levels.ARENA
        if move == "walk":
            b.x += b.face * b.speed * 1.2 * dt
        elif move == "float":
            b.x = left + 200 + math.sin(b.t * 0.9) * 150
            b.y = 120 + math.sin(b.t * 2.1) * 26
        elif move == "leap":
            if b.ground and b.act <= 0:
                b.act, b.vy, b.ground = 1.7, -330.0, False
                b.vx = max(-260.0, min(260.0, dx / 0.72))
                if attack == "wave":
                    b.slam = True
            elif not b.ground:
                b.x += b.vx * dt
            elif getattr(b, "slam", False):
                b.slam = False
                self.wave(b)
        elif move == "blink" and b.act <= 0:
            b.x = left + self.rng.randrange(40, levels.ARENA - 40)
            b.y, b.vy = float(FLOOR), 0.0
            self.sfx("select")
        if b.act <= 0:
            b.act = 2.4 if move != "blink" else 2.0
            if attack == "wave" and move == "walk":
                self.wave(b)
            elif attack == "scream":
                self.aim(b, target, "scream", 140.0)
            elif attack == "orb":
                for spread in ((-0.3, 0.0, 0.3) if b.look == "chairman" else (0.0,)):
                    self.aim(b, target, "orb", 120.0, spread)

    def wave(self, b):
        self.sfx("boom")
        self.shake = 0.3
        for sg in (-1, 1):
            self.shots.append(dict(x=b.x, y=float(FLOOR), vx=sg * 150.0, vy=0.0, kind="wave", foe=True, dmg=2, ttl=2.2))

    def aim(self, b, target, kind, speed, spread=0.0):
        a = math.atan2((target.y - 20) - (b.y - b.h / 2), target.x - b.x) + spread
        self.shots.append(dict(x=b.x, y=b.y - b.h / 2, vx=math.cos(a) * speed, vy=math.sin(a) * speed, kind=kind, foe=True, dmg=2, ttl=4.0))
        self.sfx("select")

    # ------------------------------------------------------------ update
    def update(self, dt, inp):
        if self.scene is not None:
            if self.scene.update(dt, inp):
                self.scene = None
            return
        if self.cardview is not None:
            v = self.cardview
            v["t"] += dt
            v["turn"] += max(-dt * 4, min(dt * 4, v["target"] - v["turn"]))
            src = inp if v["p"].slot == 0 or inp.p2 is None else inp.p2
            if "a" in src.pressed and v["t"] > 0.4:
                if v["target"] == 0.0:
                    v["target"] = 1.0
                    self.sfx("select")
                elif v["turn"] >= 0.99:
                    self.close_card()
            return
        self.say_t = max(0.0, self.say_t - dt)
        self.banner_t = max(0.0, self.banner_t - dt)
        self.shake = max(0.0, getattr(self, "shake", 0.0) - dt)
        self.dawn = max(0.0, getattr(self, "dawn", 0.0) - dt)
        self.join(inp)
        for p in self.players:
            src = inp if p.slot == 0 else (inp.p2 or c.Input())
            self.update_hunter(p, src, dt)
        if self.state != "play":
            return
        live = [p for p in self.players if not p.out]
        length = self.level["length"]
        if live and not self.boss_on:
            want = sum(p.x for p in live) / len(live) - 150
            self.cam = max(self.cam, min(max(0.0, want), length - W))          # the screen only scrolls forward
            if self.cam >= length - W - 2:
                self.start_boss()
        elif self.boss_on:
            self.cam = float(length - W)
        while self.spawn_i < len(self.level["spawns"]) and self.level["spawns"][self.spawn_i][0] < self.cam + W + 30:
            x, kind = self.level["spawns"][self.spawn_i]
            self.spawn_i += 1
            if len(self.beasts) < 7:
                self.spawn_beast(kind, max(x, self.cam + W + 16))
        for b in self.beasts:
            self.update_beast(b, dt)
        was_boss = any(b.boss for b in self.beasts)
        self.beasts = [b for b in self.beasts if not b.dead and b.x > self.cam - 120]
        if self.boss_on and was_boss and not any(b.boss for b in self.beasts) and self.clear_t <= 0:
            self.clear_t = 3.2
            self.beasts, self.shots = [], []
            self.score += 1000 * (self.stage + 1)
            self.banner, self.banner_t = "Floor cleared!", 3.0
            if live:
                self.talk(live[0], WIN_LINE if live[0].kind == "lucas" else None, 3.2)
            self.sound.stop_music()
            self.sfx("win")
        if self.clear_t > 0:
            self.clear_t -= dt
            if self.clear_t <= 0:
                if self.stage + 1 < len(levels.STAGES):
                    self.start_stage(self.stage + 1)
                else:
                    self.win = True
                    self.finished = True
                    c.save_score(self.name + "_done", 1, self.scores_path, best=False)
                    self.game_over()
                return
        for s in self.shots:
            if s.get("grav"):
                s["vy"] += 500 * dt
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            s["ttl"] -= dt
            box = pygame.Rect(int(s["x"]) - 5, int(s["y"]) - (12 if s["kind"] == "wave" else 5), 10, 12 if s["kind"] == "wave" else 10)
            if s["foe"]:
                for p in self.players:
                    if not p.out and box.colliderect(p.box):
                        self.hurt(p, s["dmg"], s["x"] - s["vx"])
                        s["ttl"] = 0 if s["kind"] != "wave" else s["ttl"]
            else:
                for b in self.beasts:
                    if box.colliderect(b.box):
                        self.wound(b, s["dmg"], s.get("owner"))
                        s["ttl"] = 0
                        break
        self.shots = [s for s in self.shots if s["ttl"] > 0 and self.cam - 40 < s["x"] < self.cam + W + 40 and s["y"] < H + 20]
        for d in self.drops:
            d["vy"] += 500 * dt
            d["y"] = min(float(d["floor"]) - 2, d["y"] + d["vy"] * dt)
            for p in self.players:
                if not p.out and not d.get("gone") and abs(p.x - d["x"]) < 14 and abs((p.y - 16) - d["y"]) < 24 and d["vy"] > 0:
                    d["gone"] = True
                    if d["kind"] == "heart":
                        p.hp = min(MAX_HP, p.hp + 2)
                        self.sfx("heart")
                    else:
                        self.take_card(p, d["card"])
        self.drops = [d for d in self.drops if not d.get("gone")]
        for q in self.pops:
            q[1] -= 26 * dt
            q[3] -= dt
        self.pops = [q for q in self.pops if q[3] > 0]

    # ------------------------------------------------------------ drawing
    def draw(self, surf):
        cam = int(self.cam) + (self.rng.choice((-2, 2)) if getattr(self, "shake", 0) > 0 and self.state == "play" else 0)
        bg = art.backdrop(self.stage)
        off = int(cam * 0.5) % bg.get_width()
        surf.blit(bg, (-off, 0))
        surf.blit(bg, (bg.get_width() - off, 0))
        floor_col = ((70, 72, 80), (96, 84, 76), (80, 96, 90), (52, 62, 80), (90, 50, 60))[self.stage]
        for a, b in self.level["ground"]:
            if b > cam and a < cam + W:
                pygame.draw.rect(surf, floor_col, (a - cam, FLOOR, b - a, H - FLOOR))
                pygame.draw.rect(surf, tuple(min(255, v + 40) for v in floor_col), (a - cam, FLOOR, b - a, 3))
        for a, b in zip(self.level["ground"], self.level["ground"][1:]):
            pygame.draw.rect(surf, (10, 8, 16), (a[1] - cam, FLOOR, b[0] - a[1], H - FLOOR))
        for lx, ly, lw in self.level["ledges"]:
            if lx + lw > cam and lx < cam + W:
                pygame.draw.rect(surf, (120, 124, 136), (lx - cam, ly, lw, 5))
                pygame.draw.rect(surf, (70, 72, 84), (lx - cam, ly + 5, lw, 3))
                for k in range(lx + 6, lx + lw, 22):
                    pygame.draw.line(surf, (70, 72, 84), (k - cam, ly + 8), (k - cam, ly + 16))
        for lamp in self.lamps:
            surf.blit(art.small("lamp"), (lamp[0] - 8 - cam, lamp[1] - 20))
        for chest in self.chests:
            if chest:
                surf.blit(art.small("chest"), (chest[0] - 8 - cam, chest[1] - 20))
        for d in self.drops:
            surf.blit(art.small(d["kind"]), (int(d["x"]) - 8 - cam, int(d["y"]) - 14))
        for b in self.beasts:
            img = art.monster(b.kind, int(b.t * 5) % 2, b.scale, b.look, b.flash > 0)
            if b.face > 0:
                img = c.flip(img)
            surf.blit(img, (int(b.x) - img.get_width() // 2 - cam, int(b.y) - img.get_height() + 2))
        for p in self.players:
            if p.out or (p.inv > 0 and int(self.time * 20) % 2):
                continue
            if "bat" in p.fx:
                img = art.hunter(p.kind, "bat", int(self.time * 10) % 2)
            elif p.hurt_t > 0:
                img = art.hunter(p.kind, "hurt")
            elif p.attack_t > 0:
                img = art.hunter(p.kind, "attack", 0, p.fire)
            elif not p.ground:
                img = art.hunter(p.kind, "jump")
            elif abs(p.vx) > 1:
                img = art.hunter(p.kind, "walk", int(p.walk_t * 9) % 4)
            else:
                img = art.hunter(p.kind, "stand")
            x = int(p.x) - 20 - cam
            if p.face < 0:
                img = c.flip(img)
                x = int(p.x) - (art.HW - 20) - cam
            surf.blit(img, (x, int(p.y) - art.HH + 1))
            if "garlic" in p.fx:
                for i in range(8):
                    a = self.time * 3 + i * math.pi / 4
                    pygame.draw.circle(surf, (250, 240, 200), (int(p.x + math.cos(a) * 22) - cam, int(p.y - 20 + math.sin(a) * 22)), 2)
            if "hallpass" in p.fx:
                g = art.monster("ghost", int(self.time * 4) % 2, 0.7)
                surf.blit(g, (int(p.x + math.cos(self.time * 2) * 30) - 10 - cam, int(p.y - 50 + math.sin(self.time * 3) * 6)))
        for s in self.shots:
            img = art.small(s["kind"])
            surf.blit(img if s["vx"] < 0 else c.flip(img), (int(s["x"]) - 8 - cam, int(s["y"]) - (20 if s["kind"] == "wave" else 10)))
        for q in self.pops:
            text(surf, q[2], (int(q[0]) - cam, int(q[1])), 16, c.YELLOW, center=True)
        if getattr(self, "dawn", 0) > 0:
            glow = pygame.Surface((W, H), pygame.SRCALPHA)
            glow.fill((255, 240, 170, int(220 * self.dawn / 0.6)))
            surf.blit(glow, (0, 0))
        self.draw_hud(surf)

    def draw_hud(self, surf):
        for p in self.players:
            x0 = 6 if p.slot == 0 else W - 6 - 84
            text(surf, p.d["title"] + ("  x%d" % p.lives if not p.out else "  out"), (x0, 3), 14)
            for i in range(MAX_HP // 2):
                full = p.hp - i * 2
                col = (232, 70, 90) if full >= 2 else ((240, 160, 170) if full == 1 else (70, 60, 70))
                pygame.draw.rect(surf, c.INK, (x0 + i * 11 - 1, 14, 10, 8))
                pygame.draw.rect(surf, col, (x0 + i * 11, 15, 8, 6))
            note = cards.info(p.card)[1] if p.card else ""
            if p.staples:
                note = (note + "  " if note else "") + "staples %d" % p.staples
            for k, left in p.fx.items():
                note = (note + "  " if note else "") + "%s %d" % (cards.info(k)[1], int(left) + 1)
            if note:
                text(surf, note, (x0, 25), 13, (255, 232, 120))
        text(surf, "%d" % self.score, (W // 2, 3), 18, c.WHITE, center=True)
        if len(self.players) == 1 and self.boss_on is False and int(self.time) % 6 < 2 and self.stage == 0 and self.cam < 200:
            text(surf, "Second controller: press a button to join", (W // 2, 228), 13, c.WHITE, center=True)
        bosses = [b for b in self.beasts if b.boss]
        if bosses:
            total = sum(b.max_hp for b in bosses)
            left = sum(max(0, b.hp) for b in bosses)
            pygame.draw.rect(surf, c.INK, (W // 2 - 81, H - 13, 162, 8))
            pygame.draw.rect(surf, (200, 40, 60), (W // 2 - 80, H - 12, int(160 * left / float(total)), 6))
        if self.banner_t > 0:
            text(surf, self.banner, (W // 2, 60), 30, c.YELLOW, center=True)

    def draw_title_art(self, surf):
        bg = art.backdrop(4)
        surf.blit(bg, (-int(self.time * 12) % bg.get_width() - bg.get_width(), 0))
        surf.blit(bg, (-int(self.time * 12) % bg.get_width(), 0))
        pygame.draw.rect(surf, (90, 50, 60), (0, FLOOR, W, H - FLOOR))
        surf.blit(art.hunter("lucas", "stand"), (60, FLOOR - art.HH + 1))
        surf.blit(art.monster("vampire", int(self.time * 3) % 2, 1.0, "chairman"), (300, FLOOR - 46))
        surf.blit(art.monster("zombie", int(self.time * 3) % 2), (250, FLOOR - 42))

    def render(self, surf):
        if self.state != "title":
            return super().render(surf)
        self.draw_title_art(surf)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 130))
        surf.blit(shade, (0, 0))
        text(surf, "Vampires,", (W // 2, 12), 40, self.title_color, center=True)
        text(surf, "Oh Well...", (W // 2, 42), 40, self.title_color, center=True)
        for i, line in enumerate(self.help_lines):
            text(surf, line, (W // 2, 80 + i * 14), 16, c.WHITE, center=True)
        rows = self.title_options()
        for i, row in enumerate(rows):
            if row == "level":
                label = "Start at: %d. %s" % (self.level_choice + 1, self.levels[self.level_choice])
            elif row == "mode":
                label = "Level: %s" % self.modes[self.mode]
            else:
                label = "Player %s: %s" % ("two" if row == "p2" else "one", art.HUNTERS[self.p2_kind if row == "p2" else self.p1_kind]["title"])
            text(surf, "<  %s  >" % label, (W // 2, 114 + 16 * i), 16, c.YELLOW if i == self.option_row else c.WHITE, center=True)
        if int(self.time * 2) % 2 == 0:
            text(surf, "Big button: start", (W // 2, 186), 20, c.YELLOW, center=True)
        have = bin(self.found).count("1")
        text(surf, "Triangle: card album (%d of %d)" % (have, len(cards.KEYS)), (W // 2, 206), 16, c.WHITE, center=True)
        text(surf, "Best %d" % self.best, (W // 2, 224), 16, c.WHITE, center=True)

    def render_hd(self, screen):
        if self.state == "title":
            if self.album is not None:
                i, turn, _ = self.album
                screen.fill((16, 10, 24))
                hud.label(screen, "Card album", (400, 10), 34, (236, 196, 70), center=True, bold=True)
                if self.found >> i & 1:
                    cards.show(screen, cards.KEYS[i], turn, (400, 236))
                else:
                    back = cards.card_back()
                    screen.blit(back, (400 - cards.CW // 2, 236 - cards.CH // 2))
                    hud.label(screen, "Not found yet", (400, 222), 28, (255, 255, 255), center=True)
                hud.label(screen, "%d of %d" % (i + 1, len(cards.KEYS)), (400, 420), 26, (255, 255, 255), center=True)
                hud.label(screen, "Left and right: browse    Big button: turn over    Triangle: back", (400, 448), 24, (200, 190, 220), center=True)
            return
        if self.scene is not None:
            self.scene.draw(screen)
            return
        if self.state == "over":
            return
        if self.cardview is not None:
            v = self.cardview
            shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            shade.fill((10, 6, 20, 200))
            screen.blit(shade, (0, 0))
            hud.label(screen, "%s found a card!" % v["p"].d["title"], (400, 12), 34, (236, 196, 70), center=True, bold=True)
            rise = min(1.0, v["t"] / 0.35)
            cards.show(screen, v["key"], v["turn"], (400, int(244 + (1 - rise) * 260)))
            if v["turn"] >= 0.99:
                hud.label(screen, "Big button: back to work", (400, 440), 28, (255, 255, 255), center=True)
            return
        if self.say_t > 0 and self.say_line:
            hero = next((p for p in self.players if p.kind == self.say_who and not p.out), None)
            if hero is not None:
                f = hud.font(24)
                rows = hud.wrap(self.say_line, f, 280)
                wide = max(f.size(r)[0] for r in rows) + 22
                x = max(6, min(800 - wide - 6, int((hero.x - self.cam) * 2 - wide // 2)))
                y = max(70, int(hero.y * 2) - 130 - 22 * len(rows))
                box = pygame.Rect(x, y, wide, 14 + 22 * len(rows))
                pygame.draw.rect(screen, (255, 255, 255), box, border_radius=9)
                pygame.draw.rect(screen, (30, 26, 30), box, 2, border_radius=9)
                for i, row in enumerate(rows):
                    screen.blit(f.render(row, True, (30, 26, 30)), (x + 11, y + 7 + i * 22))
