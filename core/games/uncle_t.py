"""Uncle T's Big Adventure: a top-down road chase to the mall.

Opening: Uncle T is relaxing in the hot tub when the phone rings about the new
iPhone. He curses (unintelligibly), ending in "ALICE!", and heads for the car.

On the road (scrolls upward):
    D-pad left/right  steer          up  speed up        down  brake
    big circle        turbo burst    triangle  horn (the car ahead moves over)
Dodge semi trucks, buses and cars. Cops chase from behind: make them crash into
traffic or each other, or brake-check one that rams you from behind. Every crash
earns a "That's what you get!" The further he gets, the madder he gets and the
more cops join in. Four hits and he's done. Reach the mall to win.

All art, sounds and music are original to this project.
"""
import math
import os
import subprocess
import threading

import pygame

from . import common as c
from .common import H, W, Game, text

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VOICE_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "bmo-games")

ROAD_L, ROAD_R = 100, 300
LANES = [125, 175, 225, 275]          # lane centres
PLAYER_Y = 178
CAR_W, CAR_H = 16, 28
STRETCH = 7000                       # distance per stretch of road
STRETCHES = ["The neighborhood", "The highway", "Downtown", "Mall Road"]
TOTAL = STRETCH * len(STRETCHES)

SKIN = (222, 182, 140)
SKIN_D = (190, 148, 108)
HAIR = (92, 70, 54)
SHADES = (20, 20, 26)
SHIRT = (60, 170, 200)

INTRO_LEN = 10.0


# ---------- art made from shapes ----------
TURBO_LEN, TURBO_COOL, TURBO_BOOST = 2.6, 5.5, 190
MAX_HITS = 4
LUNGE_AFTER = 1.1        # seconds a cop must sit lined up behind you before he rams


def cop_speed(stage):
    """A touch faster than Uncle T's top speed: they reel you in slowly flat out, fast at cruise, never in turbo."""
    return 255 + 40 * stage


def car_surface(body, dark, kind="car"):
    s = pygame.Surface((CAR_W, CAR_H), pygame.SRCALPHA)
    for x, y in ((0, 4), (14, 4), (0, 19), (14, 19)):
        pygame.draw.rect(s, (16, 16, 18), (x, y, 2, 6))
    pygame.draw.rect(s, body, (1, 1, 14, 26), border_radius=4)
    pygame.draw.rect(s, dark, (1, 1, 14, 26), 1, border_radius=4)
    if kind == "cop":
        pygame.draw.rect(s, (245, 245, 245), (1, 9, 14, 10))
    pygame.draw.rect(s, (40, 56, 76), (3, 7, 10, 5))           # windscreen
    pygame.draw.rect(s, dark, (3, 12, 10, 7))                  # roof
    pygame.draw.rect(s, (40, 56, 76), (3, 19, 10, 3))          # rear window
    pygame.draw.rect(s, (255, 236, 150), (2, 1, 3, 2))         # headlights
    pygame.draw.rect(s, (255, 236, 150), (11, 1, 3, 2))
    pygame.draw.rect(s, (220, 40, 40), (2, 25, 3, 2))          # tail lights
    pygame.draw.rect(s, (220, 40, 40), (11, 25, 3, 2))
    return s


def bus_surface():
    s = pygame.Surface((22, 62), pygame.SRCALPHA)
    pygame.draw.rect(s, (238, 238, 232), (0, 0, 22, 62), border_radius=3)
    pygame.draw.rect(s, (40, 110, 190), (0, 0, 22, 62), 2, border_radius=3)
    pygame.draw.rect(s, (40, 56, 76), (2, 2, 18, 6))
    for y in range(12, 58, 9):
        pygame.draw.rect(s, (180, 180, 176), (5, y, 12, 5))     # roof vents
    pygame.draw.rect(s, (40, 110, 190), (0, 28, 22, 4))
    return s


def semi_surface(cab):
    s = pygame.Surface((24, 82), pygame.SRCALPHA)
    pygame.draw.rect(s, cab, (2, 0, 20, 18), border_radius=3)
    pygame.draw.rect(s, (40, 56, 76), (4, 3, 16, 5))
    pygame.draw.rect(s, (60, 60, 64), (10, 18, 4, 3))
    pygame.draw.rect(s, (214, 214, 220), (0, 21, 24, 61), border_radius=2)
    for y in range(25, 80, 6):
        pygame.draw.line(s, (180, 180, 188), (1, y), (22, y))
    pygame.draw.rect(s, (120, 120, 128), (0, 21, 24, 61), 1, border_radius=2)
    return s


def face_surface(rage):
    """Uncle T's head for the dashboard: skinny face, balding, sunglasses; redder when angry."""
    s = pygame.Surface((26, 30), pygame.SRCALPHA)
    red = min(1.0, max(0.0, rage))
    skin = tuple(int(a + (b - a) * red * 0.7) for a, b in zip(SKIN, (232, 92, 72)))
    pygame.draw.ellipse(s, skin, (4, 3, 18, 25))                  # long, thin face
    pygame.draw.ellipse(s, (255, 255, 255, 120), (9, 5, 6, 3))    # shine on the bald top
    pygame.draw.rect(s, HAIR, (3, 11, 3, 8))                      # hair at the sides only
    pygame.draw.rect(s, HAIR, (20, 11, 3, 8))
    pygame.draw.rect(s, SHADES, (5, 13, 16, 4), border_radius=1)  # sunglasses
    if rage > 0.3:                                                # angry brows
        pygame.draw.line(s, HAIR, (6, 10), (11, 12), 2)
        pygame.draw.line(s, HAIR, (20, 10), (15, 12), 2)
    mouth_y = 23
    if rage > 0.6:
        pygame.draw.rect(s, (60, 20, 20), (10, mouth_y - 1, 6, 3))
    else:
        pygame.draw.line(s, (90, 50, 40), (10, mouth_y), (16, mouth_y))
    return s


_tub = {}


def tub_man(mood):
    """Uncle T from the chest up, lounging in the hot tub: calm, on the phone, or furious. 320 x 150."""
    if mood in _tub:
        return _tub[mood]
    from .alien_storm import art as hd
    poly, oval, line = hd.poly, hd.oval, hd.line
    s = pygame.Surface((320 * hd.SS, 150 * hd.SS), pygame.SRCALPHA)
    cx = 160.0
    skin = SKIN if mood != "angry" else (232, 150, 120)
    dark = SKIN_D if mood != "angry" else (196, 110, 86)
    # arms stretched out along the edge of the tub, or one bent up holding the phone
    poly(s, skin, [(cx - 34, 92), (cx - 110, 100), (cx - 128, 108), (cx - 126, 118), (cx - 104, 116), (cx - 34, 112)])
    oval(s, skin, (cx - 142, 102, 22, 16))
    for k in range(3):
        line(s, dark, (cx - 138 + k * 5, 106), (cx - 138 + k * 5, 114), 0.7)
    if mood == "calm":
        poly(s, skin, [(cx + 34, 92), (cx + 110, 100), (cx + 128, 108), (cx + 126, 118), (cx + 104, 116), (cx + 34, 112)])
        oval(s, skin, (cx + 120, 102, 22, 16))
        poly(s, (240, 240, 250), [(cx + 122, 84), (cx + 140, 84), (cx + 137, 104), (cx + 125, 104)])      # a cold drink
        poly(s, (250, 170, 60), [(cx + 123.5, 90), (cx + 138.5, 90), (cx + 137, 103), (cx + 125, 103)])
        line(s, (230, 60, 60), (cx + 134, 78), (cx + 130, 96), 0.9)
    else:
        poly(s, skin, [(cx + 34, 94), (cx + 62, 104), (cx + 70, 96), (cx + 54, 60), (cx + 40, 62), (cx + 44, 86)])   # bent arm
        oval(s, skin, (cx + 36, 46, 20, 22))
        poly(s, (30, 30, 34), [(cx + 30, 36), (cx + 42, 36), (cx + 42, 66), (cx + 30, 66)])                # the phone
        poly(s, (140, 200, 255), [(cx + 32, 39), (cx + 40, 39), (cx + 40, 62), (cx + 32, 62)])
        for k in range(4):
            line(s, dark, (cx + 40, 50 + k * 4), (cx + 50, 50 + k * 4), 0.7)
    # chest and shoulders
    poly(s, skin, [(cx - 44, 150), (cx - 46, 100), (cx - 34, 88), (cx - 12, 82), (cx + 12, 82), (cx + 34, 88), (cx + 46, 100), (cx + 44, 150)])
    line(s, dark, (cx - 26, 92), (cx - 6, 96), 0.9, mirror=cx)                                           # collar bones
    line(s, dark, (cx, 104), (cx, 132), 0.8)
    poly(s, dark, [(cx - 30, 112), (cx - 6, 116), (cx - 6, 118), (cx - 30, 115)], mirror=cx)
    for k in range(7):                                                                                   # a little chest hair
        oval(s, (120, 100, 90), (cx - 12 + (k * 7) % 24, 100 + (k * 5) % 12, 1.6, 1.6))
    # neck and bald head
    poly(s, dark, [(cx - 12, 62), (cx + 12, 62), (cx + 14, 86), (cx - 14, 86)])
    oval(s, skin, (cx - 25, 8, 50, 62))
    oval(s, skin, (cx - 30, 34, 9, 15), mirror=cx)                                                       # ears
    oval(s, dark, (cx - 28, 38, 4, 8), mirror=cx)
    oval(s, (255, 240, 220), (cx - 14, 12, 16, 9))                                                       # the shine on top
    poly(s, (110, 100, 96), [(cx - 25, 34), (cx - 21, 22), (cx - 19, 34), (cx - 22, 44)], mirror=cx)     # grey at the sides
    # wraparound sunglasses
    poly(s, (16, 16, 22), [(cx - 25, 32), (cx + 25, 32), (cx + 23, 44), (cx + 4, 46), (cx, 40), (cx - 4, 46), (cx - 23, 44)])
    poly(s, (70, 90, 130), [(cx - 21, 34), (cx - 10, 34), (cx - 18, 41)])
    poly(s, (70, 90, 130), [(cx + 6, 34), (cx + 15, 34), (cx + 8, 41)])
    brow = 5 if mood == "angry" else (-2 if mood == "phone" else 0)
    line(s, (90, 80, 76), (cx - 22, 29 - brow * 0.3), (cx - 6, 29 + brow), 1.6)
    line(s, (90, 80, 76), (cx + 22, 29 - brow * 0.3), (cx + 6, 29 + brow), 1.6)
    poly(s, dark, [(cx - 1, 42), (cx - 5, 53), (cx + 5, 53)])                                            # nose
    if mood == "calm":
        line(s, (130, 70, 60), (cx - 9, 59), (cx + 9, 59), 1.2)
        line(s, (130, 70, 60), (cx + 9, 59), (cx + 12, 57), 1.0)
    elif mood == "phone":
        oval(s, (90, 40, 40), (cx - 4, 56, 8, 6))
    else:
        poly(s, (70, 24, 26), [(cx - 12, 55), (cx + 12, 55), (cx + 9, 67), (cx - 9, 67)])
        poly(s, (255, 255, 255), [(cx - 10, 56), (cx + 10, 56), (cx + 9, 59), (cx - 9, 59)])
        poly(s, (220, 100, 110), [(cx - 5, 64), (cx + 5, 64), (cx + 4, 66.5), (cx - 4, 66.5)])
        for sx in (-1, 1):                                                                               # a vein and steam from the ears
            line(s, (190, 60, 60), (cx + sx * 12, 14), (cx + sx * 16, 20), 0.8)
            line(s, (190, 60, 60), (cx + sx * 16, 20), (cx + sx * 13, 24), 0.8)
            oval(s, (245, 245, 245), (cx + sx * 36 - 5, 26, 10, 8))
            oval(s, (245, 245, 245), (cx + sx * 44 - 4, 18, 8, 7))
    _tub[mood] = out = pygame.transform.smoothscale(s, (320, 150))
    return out


def bubble(surf, msg, x, y, size=16):
    font = pygame.font.Font(None, size)
    img = font.render(msg, False, c.INK)
    w, h = img.get_width() + 10, img.get_height() + 6
    x = max(2, min(W - w - 2, x))
    pygame.draw.rect(surf, (255, 255, 255), (x, y, w, h), border_radius=5)
    pygame.draw.rect(surf, c.INK, (x, y, w, h), 1, border_radius=5)
    pygame.draw.polygon(surf, (255, 255, 255), [(x + 10, y + h - 1), (x + 18, y + h - 1), (x + 8, y + h + 6)])
    surf.blit(img, (x + 5, y + 3))


# ---------- voices ----------
def _piper_wave(line, pitch=0.85):
    """Speak a line with BMO's own voice model, pitched down for Uncle T. None if Piper is missing."""
    try:
        import json
        import numpy as np
        from . import sound
        exe = os.path.join(ROOT, "piper", "piper")
        model = os.path.join(ROOT, "piper", "bmo.onnx")
        if not (os.path.exists(exe) and os.path.exists(model)):
            return None
        rate = 22050
        try:
            with open(model + ".json") as fh:
                rate = int(json.load(fh)["audio"]["sample_rate"])
        except Exception:
            pass
        raw = subprocess.run([exe, "--model", model, "--output_raw"], input=line.encode(),
                             capture_output=True, timeout=20).stdout
        if not raw:
            return None
        pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        # Playing it slower lowers the pitch: stretch to (RATE / rate) / pitch.
        n_out = int(len(pcm) * sound.RATE / rate / pitch)
        return np.interp(np.linspace(0, len(pcm) - 1, n_out), np.arange(len(pcm)), pcm).astype(np.float32) * 0.9
    except Exception:
        return None


def _garble(seed, syllables=9):
    """Comic, unintelligible grumbling made of chip tones."""
    import random
    from . import sound
    rng = random.Random(seed)
    parts = []
    for _ in range(syllables):
        f0 = rng.uniform(150, 260)
        d = rng.uniform(0.06, 0.13)
        parts.append(sound.mix(sound.tone(f0, d, "square", 0.3, 0.32, slide=f0 * rng.uniform(0.7, 1.4), vibrato=9),
                               sound.tone(f0 * 2.6, d, "square", 0.5, 0.08)))
        parts.append(sound.rest(rng.uniform(0.01, 0.05)))
    return sound.chain(*parts)


def _fallback_word(kind):
    from . import sound
    if kind == "alice":   # "A-lice": a rising "ah" then a hiss
        return sound.chain(sound.tone(170, 0.2, "square", 0.4, 0.4, slide=260, vibrato=6),
                           sound.tone(320, 0.12, "square", 0.3, 0.35, slide=300), sound.tone(5000, 0.16, "noise", vol=0.25))
    return _garble(7, 6)


def build_voices():
    """{"curse": wave, "taunt": wave}. Piper words are cached in ~/.cache/bmo-games."""
    import numpy as np
    from . import sound
    out = {}
    os.makedirs(VOICE_CACHE, exist_ok=True)

    def word(key, line, pitch, fallback):
        path = os.path.join(VOICE_CACHE, "uncle_t_%s.npy" % key)
        try:
            return np.load(path)
        except Exception:
            pass
        w = _piper_wave(line, pitch)
        if w is None:
            return fallback()
        try:
            np.save(path, w)
        except Exception:
            pass
        return w

    alice = word("alice", "Alice!", 0.8, lambda: _fallback_word("alice"))
    out["curse"] = sound.chain(_garble(3, 10), sound.rest(0.06), alice * 1.1)
    out["taunt"] = word("taunt", "That's what you get!", 0.85, lambda: _fallback_word("taunt"))
    return out


# ---------- the game ----------
class UncleT(Game):
    levels = tuple(STRETCHES)
    name = "uncle_t"
    title = "Uncle T's Big Adventure"
    help_lines = ("D-pad: steer, up speeds up, down brakes", "Big button: turbo   Triangle: horn",
                  "Dodge the traffic, crash the cops,", "and get to the mall!")
    title_color = (120, 210, 250)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.player_car = car_surface((200, 204, 210), (130, 134, 142))
        self.cop_car = car_surface((24, 24, 30), (10, 10, 14), "cop")
        colors = [((200, 60, 60), (140, 30, 30)), ((60, 120, 200), (30, 70, 140)), ((240, 200, 70), (170, 130, 30)),
                  ((90, 170, 90), (50, 110, 50)), ((150, 100, 190), (100, 60, 140)), ((230, 130, 60), (160, 80, 30))]
        self.traffic_cars = [car_surface(a, b) for a, b in colors]
        self.bus = bus_surface()
        self.semis = [semi_surface(col) for col in ((190, 50, 50), (40, 90, 170), (60, 130, 70))]
        self.faces = [face_surface(r) for r in (0.0, 0.35, 0.65, 1.0)]
        self.big_face = pygame.transform.scale(face_surface(0.0), (78, 90))
        self.voices = None
        self._voice_thread = None
        self.seen_intro = False
        self.reset()

    @property
    def music(self):
        return "hottub" if getattr(self, "phase", "intro") == "intro" else "uncle_t"

    # ----- setup -----
    def reset(self):
        self.score = 0
        self.win = False
        self.phase = "drive" if self.seen_intro else "intro"
        self.phase_t = 0.0
        self.dist = 0.0
        self.speed = 150.0
        self.px = float(LANES[1] - CAR_W // 2)
        self.hits = 0
        self.invuln = 0.0
        self.traffic = []
        self.cops = []
        self.puffs = []
        self.spawn_t = 1.0
        self.cop_t = 4.0
        self.turbo = 0.0
        self.turbo_cool = 0.0
        self.taunt = 0.0
        self.taunt_cool = 0.0
        self.crashed = 0
        self.shaken = 0
        start = min(self.level_choice, len(STRETCHES) - 1)
        self.dist = float(start * STRETCH)
        self.banner = (STRETCHES[start], 2.5)
        self.stretch = start
        self.cue = set()
        self.end_reason = ""

    def start_voices(self):
        if self.voices is None and self._voice_thread is None and self.sound.enabled:
            box = {}

            def work():
                try:
                    box.update(build_voices())
                except Exception:
                    pass
                self.voices = box

            self._voice_thread = threading.Thread(target=work, daemon=True)
            self._voice_thread.start()

    def say(self, key):
        if self.voices and key in self.voices:
            name = "voice_" + key
            if name not in getattr(self, "_added", set()):
                self.sound.add(name, self.voices[key])
                self._added = getattr(self, "_added", set()) | {name}
            self.sound.play(name)

    @property
    def progress(self):
        return min(1.0, self.dist / TOTAL)

    @property
    def rage(self):
        return min(1.0, self.progress + 0.12 * self.hits)

    # ----- frame update -----
    def update(self, dt, inp):
        self.phase_t += dt
        if self.phase == "intro":
            self.update_intro(dt, inp)
        elif self.phase == "drive":
            self.update_drive(dt, inp)
        elif self.phase == "arrive":
            self.update_arrive(dt, inp)

    def once(self, key):
        if key in self.cue:
            return False
        self.cue.add(key)
        return True

    def update_intro(self, dt, inp):
        self.start_voices()
        t = self.phase_t
        if t > 2.0 and self.once("ring"):
            self.sfx("ring")
        if t > 5.6 and self.once("curse"):
            self.say("curse")
        if t > 8.2 and self.once("rev"):
            self.sfx("turbo")
        if t >= INTRO_LEN or (t > 0.4 and ("a" in inp.pressed or "start" in inp.pressed)):
            self.begin_drive()

    def begin_drive(self):
        self.seen_intro = True
        self.phase, self.phase_t = "drive", 0.0
        self.sound.music("uncle_t")

    def update_drive(self, dt, inp):
        self.start_voices()
        p = self.progress
        stage = min(3, int(self.dist // STRETCH))
        if stage != self.stretch:
            self.stretch = stage
            self.reach_level(stage)
            self.banner = (STRETCHES[stage], 2.5)
            self.sfx("start")
        if self.banner[1] > 0:
            self.banner = (self.banner[0], self.banner[1] - dt)

        # speed and steering
        cruise = 150 + 22 * stage
        top = 240 + 40 * stage
        if "up" in inp.held:
            self.speed = min(top, self.speed + 160 * dt)
        elif "down" in inp.held:
            if self.speed > 120 and "down" in inp.pressed:
                self.sfx("skid")
            self.speed = max(70, self.speed - 260 * dt)
        else:
            self.speed += (cruise - self.speed) * min(1, 1.5 * dt)
        if self.turbo > 0:
            self.turbo -= dt
        self.turbo_cool = max(0.0, self.turbo_cool - dt)
        if "a" in inp.pressed and self.turbo_cool <= 0:
            self.turbo, self.turbo_cool = TURBO_LEN, TURBO_COOL
            self.sfx("turbo")
            self.banner = ("TURBO!", 0.8)
        speed = self.speed + (TURBO_BOOST if self.turbo > 0 else 0)
        steer = 150 if not inp.touch else 0
        if "left" in inp.held:
            self.px -= steer * dt
        if "right" in inp.held:
            self.px += steer * dt
        if inp.touch:
            self.px += max(-150 * dt, min(150 * dt, inp.touch[0] - CAR_W / 2 - self.px))
        if self.px < ROAD_L + 3 or self.px > ROAD_R - CAR_W - 3:
            self.px = max(ROAD_L + 3, min(ROAD_R - CAR_W - 3, self.px))
            self.speed = max(80, self.speed - 120 * dt)
            if int(self.time * 8) % 4 == 0:
                self.sfx("scrape")
        if "b" in inp.pressed:
            self.honk()

        self.dist += speed * dt
        self.score += speed * dt / 10
        self.invuln = max(0.0, self.invuln - dt)
        self.taunt = max(0.0, self.taunt - dt)
        self.taunt_cool = max(0.0, self.taunt_cool - dt)

        self.update_traffic(dt, speed, stage)
        self.update_cops(dt, speed, p, stage, inp)
        self.puffs = [[x, y + speed * dt, r + 14 * dt, t - dt] for x, y, r, t in self.puffs if t > dt]

        if self.dist >= TOTAL:
            self.phase, self.phase_t = "arrive", 0.0
            for cop in self.cops:
                self.crash_cop(cop, quiet=True)
            self.sfx("clear")

    def lane_busy(self, x, y0, y1):
        for v in self.traffic:
            if abs(v["x"] + v["w"] / 2 - x) < 20 and v["y"] < y1 and v["y"] + v["h"] > y0:
                return True
        return False

    def update_traffic(self, dt, speed, stage):
        self.spawn_t -= dt
        if self.spawn_t <= 0:
            self.spawn_t = max(0.6, 1.55 - 0.22 * stage - 0.15 * self.progress) * self.rng.uniform(0.7, 1.3)
            weights = {"car": 5, "bus": 2 + (stage == 2) * 2, "semi": 2 + (stage == 1) * 3}
            kind = self.rng.choices(list(weights), list(weights.values()))[0]
            surf = {"car": lambda: self.rng.choice(self.traffic_cars), "bus": lambda: self.bus,
                    "semi": lambda: self.rng.choice(self.semis)}[kind]()
            w, h = surf.get_size()
            free = [ln for ln in LANES if not self.lane_busy(ln, -h - 80, 70)]
            if len(free) >= 2:            # always leave at least one lane open
                lane = self.rng.choice(free)
                v_speed = {"car": self.rng.uniform(85, 125), "bus": self.rng.uniform(65, 85),
                           "semi": self.rng.uniform(55, 75)}[kind]
                self.traffic.append({"kind": kind, "surf": surf, "x": lane - w / 2, "y": -h - 10, "w": w, "h": h,
                                     "v": v_speed, "shift": 0.0})
        self.keep_a_lane_open()
        for v in self.traffic:
            v["y"] += (speed - v["v"]) * dt
            if v["shift"]:
                step = max(-90 * dt, min(90 * dt, v["shift"]))
                v["x"] += step
                v["shift"] -= step
            if self.invuln <= 0 and self.overlap(v, self.player_rect(), 3):
                self.hit("traffic")
        self.traffic = [v for v in self.traffic if -260 < v["y"] < H + 40]

    def lane_of(self, v):
        return min(range(len(LANES)), key=lambda i: abs(LANES[i] - (v["x"] + v["w"] / 2)))

    def keep_a_lane_open(self):
        """If a vehicle is about to close the last open lane, it drops back behind the slowest one beside it."""
        for v in self.traffic:
            near = [o for o in self.traffic if o is not v and o["y"] < v["y"] + v["h"] + 50 and o["y"] + o["h"] > v["y"] - 50]
            lanes = {self.lane_of(o) for o in near} | {self.lane_of(v)}
            if len(lanes) >= len(LANES):
                slowest = min(o["v"] for o in near)
                if v["v"] >= slowest:
                    v["v"] = max(30.0, slowest - 12)

    def honk(self):
        self.sfx("horn")
        cx = self.px + CAR_W / 2
        ahead = [v for v in self.traffic if v["kind"] == "car" and abs(v["x"] + v["w"] / 2 - cx) < 22
                 and PLAYER_Y - 110 < v["y"] < PLAYER_Y and not v["shift"]]
        for v in ahead:
            vx = v["x"] + v["w"] / 2
            for target in sorted(LANES, key=lambda ln: abs(ln - vx)):
                if abs(target - vx) > 30 and not self.lane_busy(target, v["y"] - 20, v["y"] + v["h"] + 20):
                    v["shift"] = target - vx
                    break

    def player_rect(self):
        return {"x": self.px, "y": PLAYER_Y, "w": CAR_W, "h": CAR_H}

    @staticmethod
    def overlap(a, b, inset=2):
        return (a["x"] + inset < b["x"] + b["w"] - inset and b["x"] + inset < a["x"] + a["w"] - inset and
                a["y"] + inset < b["y"] + b["h"] - inset and b["y"] + inset < a["y"] + a["h"] - inset)

    def update_cops(self, dt, speed, p, stage, inp):
        max_cops = min(5, 1 + int(p * 5))
        self.cop_t -= dt
        live = [cp for cp in self.cops if not cp["crash"]]
        if self.cop_t <= 0 and len(live) < max_cops and self.turbo <= 0:
            self.cop_t = max(2.0, 6.5 - 4.5 * p) * self.rng.uniform(0.8, 1.25)
            lane = self.rng.choice(LANES)
            self.cops.append({"x": lane - CAR_W / 2, "y": H + 30, "w": CAR_W, "h": CAR_H, "crash": 0.0,
                              "spin": 0.0, "back": 0.0, "smart": min(0.8, 0.2 + 0.18 * stage),
                              "v": cop_speed(stage) * self.rng.uniform(0.95, 1.05)})
            self.sfx("siren")
        smart_roll = self.rng.random()
        for cop in self.cops:
            if cop["crash"]:
                cop["crash"] -= dt
                cop["spin"] += 540 * dt
                cop["y"] += speed * 0.8 * dt
                continue
            # a cop has a real road speed: drive faster than him (turbo) and he falls behind
            # cops trail a few car lengths back and only lunge after lining up behind you for a moment
            cx0 = cop["x"] + CAR_W / 2
            lined = abs(cx0 - (self.px + CAR_W / 2)) < 12 and self.invuln <= 0
            cop["lock"] = cop.get("lock", 0.0) + dt if lined else max(0.0, cop.get("lock", 0.0) - 2 * dt)
            target_y = PLAYER_Y + (8 if cop["lock"] > LUNGE_AFTER else 46)
            gap = cop["y"] - target_y
            close = cop["v"] - speed - (90 if cop["back"] > 0 else 0)
            if close > 0:
                close = min(close, 110.0, max(0.0, gap) * 2.5)
            elif gap < 0 and cop["v"] >= speed:
                close = gap * 2.0          # drifted too close: ease back to trailing distance
            cop["y"] -= close * dt
            cop["back"] = max(0.0, cop["back"] - dt)
            cx = cop["x"] + CAR_W / 2
            want = self.px + CAR_W / 2
            # smarter cops look ahead and steer round traffic
            danger = [v for v in self.traffic if abs(v["x"] + v["w"] / 2 - cx) < 20 and cop["y"] - 70 < v["y"] + v["h"] < cop["y"] + 6]
            if danger and smart_roll < cop["smart"] * dt * 8:
                want = cx + (40 if cx < 200 else -40)
            if cop["back"] <= 0:
                cop["x"] += max(-(55 + 10 * stage) * dt, min((55 + 10 * stage) * dt, want - cx))
            if cop["x"] < ROAD_L - 2 or cop["x"] > ROAD_R - CAR_W + 2:
                self.crash_cop(cop)
                continue
            for v in self.traffic:
                if self.overlap(v, cop, 2):
                    self.crash_cop(cop)
                    break
            if cop["crash"]:
                continue
            for other in self.cops:
                if other is not cop and not other["crash"] and self.overlap(other, cop, 3):
                    self.crash_cop(cop)
                    self.crash_cop(other)
                    break
            if cop["crash"]:
                continue
            if self.overlap(cop, self.player_rect(), 3):
                behind = cop["y"] > PLAYER_Y + 14
                if behind and "down" in inp.held:
                    self.crash_cop(cop)               # brake check!
                elif self.invuln <= 0:
                    cop["y"] += 60
                    cop["back"] = 2.0
                    cop["lock"] = 0.0
                    self.hit("cop")
        for cop in self.cops:
            if not cop["crash"] and cop["y"] >= H + 60:
                self.shaken += 1
                self.score += 150
                self.banner = ("SHOOK HIM!", 1.0)
        self.cops = [cp for cp in self.cops if cp["y"] < H + 60 and not (cp["crash"] and cp["crash"] <= 0)]

    def crash_cop(self, cop, quiet=False):
        if cop["crash"]:
            return
        cop["crash"] = 2.2
        self.puffs.append([cop["x"] + 8, cop["y"] + 12, 4.0, 1.2])
        if quiet:
            return
        self.crashed += 1
        self.score += 250
        self.sfx("crash")
        if self.taunt_cool <= 0:
            self.taunt, self.taunt_cool = 1.6, 2.4
            self.say("taunt")

    def hit(self, by):
        self.hits += 1
        self.invuln = 2.0
        self.speed = 110
        self.sfx("crash" if by == "traffic" else "hurt")
        self.puffs.append([self.px + 8, PLAYER_Y + 6, 5.0, 1.0])
        if self.hits >= MAX_HITS:
            self.end_reason = "BUSTED!" if by == "cop" else "WRECKED!"
            self.game_over()

    def update_arrive(self, dt, inp):
        self.speed = max(0.0, self.speed - 90 * dt)
        self.dist += self.speed * dt
        for v in self.traffic:
            v["y"] += (self.speed + 80) * dt
        for cop in self.cops:
            cop["y"] += 160 * dt
            cop["spin"] += 360 * dt
        if self.phase_t > 6.0 or (self.phase_t > 2.5 and "a" in inp.pressed):
            self.score += 5000 + 1000 * (MAX_HITS - self.hits) + 100 * self.crashed
            self.win = True
            self.end_reason = "He made it to the mall!"
            self.game_over()

    # ----- drawing -----
    def draw_title_art(self, surf):
        self.draw_road(surf, 0, 0)
        surf.blit(self.player_car, (LANES[1] - 8, PLAYER_Y))
        surf.blit(self.cop_car, (LANES[2] - 8, PLAYER_Y + 40))

    def draw(self, surf):
        if self.phase == "intro":
            self.draw_intro(surf)
            return
        stage = min(3, int(self.dist // STRETCH))
        self.draw_road(surf, self.dist, stage)
        if self.phase == "arrive":
            self.draw_mall(surf)
        for v in self.traffic:
            surf.blit(v["surf"], (int(v["x"]), int(v["y"])))
        for cop in self.cops:
            img = self.cop_car.copy()
            if not cop["crash"]:
                warn = cop.get("lock", 0.0) > LUNGE_AFTER * 0.45
                blue = int(self.time * (16 if warn else 6)) % 2
                pygame.draw.rect(img, (60, 110, 255) if blue else (240, 40, 40), (3, 13, 5, 2))
                pygame.draw.rect(img, (240, 40, 40) if blue else (60, 110, 255), (8, 13, 5, 2))
            else:
                img = pygame.transform.rotate(img, cop["spin"])
            r = img.get_rect(center=(int(cop["x"] + CAR_W / 2), int(cop["y"] + CAR_H / 2)))
            surf.blit(img, r)
            if not cop["crash"] and cop.get("lock", 0.0) > LUNGE_AFTER * 0.45 and int(self.time * 10) % 2:
                text(surf, "!", (r.centerx, r.top - 8), 16, (255, 220, 60), center=True)
        if self.phase != "arrive" or self.phase_t < 2.5:
            if self.invuln <= 0 or int(self.time * 12) % 2 == 0:
                if self.turbo > 0:
                    for i in range(3):
                        pygame.draw.circle(surf, (255, 170 - i * 40, 40), (int(self.px) + 8, PLAYER_Y + CAR_H + 3 + i * 3),
                                           4 - i)
                surf.blit(self.player_car, (int(self.px), PLAYER_Y))
        for x, y, r, t in self.puffs:
            pygame.draw.circle(surf, (150, 150, 150), (int(x), int(y)), int(r))
        if self.taunt > 0 and self.phase == "drive":
            hx, hy = int(self.px) - 9, PLAYER_Y + 7
            pygame.draw.line(surf, SHIRT, (hx + 9, hy + 7), (hx + 1, hy + 10), 3)      # arm out of the window
            surf.blit(self.faces[min(3, int(self.rage * 3.99))], (hx - 13, hy - 12))
            bubble(surf, "That's what you get!", hx - 30, hy - 36)
        self.draw_hud(surf)
        if self.banner[1] > 0 and self.phase == "drive":
            text(surf, self.banner[0], (W // 2, 70), 30, c.YELLOW, center=True)

    def draw_road(self, surf, dist, stage):
        side = [(84, 150, 70), (96, 140, 70), (120, 120, 126), (140, 140, 146)][stage]
        surf.fill(side)
        pygame.draw.rect(surf, (64, 64, 70), (ROAD_L, 0, ROAD_R - ROAD_L, H))
        pygame.draw.rect(surf, (240, 240, 240), (ROAD_L, 0, 2, H))
        pygame.draw.rect(surf, (240, 240, 240), (ROAD_R - 2, 0, 2, H))
        off = int(dist) % 40
        for lx in (150, 200, 250):
            col = (240, 200, 60) if lx == 200 else (230, 230, 230)
            for y in range(-40 + off, H, 40):
                pygame.draw.rect(surf, col, (lx - 1, y, 2, 20))
        # scenery tiles, 80 px tall, chosen from the tile number so they scroll with the road
        base = int(dist // 80)
        for k in range(-1, H // 80 + 2):
            tile = base - k
            y = H - (k + 1) * 80 + int(dist) % 80
            for left in (True, False):
                self.draw_scenery(surf, tile * 2 + (0 if left else 1), 4 if left else ROAD_R + 6, y, stage)

    def draw_scenery(self, surf, seed, x, y, stage):
        r = (seed * 2654435761) & 0xFFFF
        if stage == 0:                                   # houses and trees
            if r % 3 == 0:
                pygame.draw.circle(surf, (50, 110, 50), (x + 20 + r % 40, y + 30), 14)
            else:
                col = [(220, 200, 170), (180, 200, 220), (230, 180, 160)][r % 3]
                pygame.draw.rect(surf, col, (x + 14, y + 22, 52, 38))
                pygame.draw.polygon(surf, (150, 70, 60), [(x + 10, y + 24), (x + 40, y + 6), (x + 70, y + 24)])
                pygame.draw.rect(surf, (90, 60, 40), (x + 34, y + 44, 10, 16))
        elif stage == 1:                                 # highway: rail, signs, bushes
            pygame.draw.rect(surf, (190, 190, 196), (x + (80 if x < ROAD_L else 0), y, 4, 80))
            if r % 4 == 0:
                pygame.draw.rect(surf, (30, 120, 70), (x + 18, y + 20, 50, 22))
                text(surf, "MALL %d" % max(1, int((TOTAL - self.dist) / 3000)), (x + 22, y + 26), 14, c.WHITE, shadow=False)
            else:
                pygame.draw.circle(surf, (60, 120, 60), (x + 30 + r % 30, y + 40), 10)
        elif stage == 2:                                 # downtown blocks
            col = [(150, 110, 100), (110, 120, 150), (170, 160, 130), (120, 140, 120)][r % 4]
            pygame.draw.rect(surf, col, (x + 4, y + 4, 84, 72))
            for wy in range(y + 10, y + 70, 12):
                for wx in range(x + 10, x + 82, 14):
                    pygame.draw.rect(surf, (230, 220, 140) if (wx + wy + r) % 5 else (60, 70, 90), (wx, wy, 7, 6))
        else:                                            # mall road: parking lots and palms
            for py in range(y + 6, y + 80, 18):
                pygame.draw.line(surf, (235, 235, 235), (x + 6, py), (x + 40, py))
            if r % 2:
                pygame.draw.rect(surf, (110, 80, 50), (x + 62, y + 34, 4, 30))
                for a in range(0, 360, 72):
                    pygame.draw.line(surf, (60, 150, 70), (x + 64, y + 34),
                                     (x + 64 + int(14 * math.cos(math.radians(a))), y + 34 + int(10 * math.sin(math.radians(a)))), 3)

    def draw_mall(self, surf):
        top = int(-120 + min(1.0, self.phase_t / 2.0) * 130)
        pygame.draw.rect(surf, (200, 190, 220), (30, top, 340, 110))
        pygame.draw.rect(surf, (120, 100, 160), (30, top, 340, 110), 3)
        pygame.draw.rect(surf, (60, 70, 100), (170, top + 60, 60, 50))
        text(surf, "THE MALL", (W // 2, top + 18), 34, (250, 220, 90), center=True)
        if self.phase_t > 2.5:
            wx = 200 - 4 + int(min(1.0, (self.phase_t - 2.5) / 2.0) * 0)
            wy = int(PLAYER_Y - min(1.0, (self.phase_t - 2.5) / 2.0) * (PLAYER_Y - top - 70))
            surf.blit(self.player_car, (int(self.px), PLAYER_Y))
            pygame.draw.rect(surf, SHIRT, (wx, wy + 8, 8, 12))
            pygame.draw.ellipse(surf, SKIN, (wx, wy, 8, 9))
            pygame.draw.rect(surf, SHADES, (wx + 1, wy + 3, 6, 2))
            bubble(surf, "New phone, here I come!", wx - 40, wy - 26)

    def draw_hud(self, surf):
        pygame.draw.rect(surf, (20, 20, 28), (0, 0, W, 16))
        text(surf, "%d" % int(self.score), (4, 1), 18, c.WHITE)
        pygame.draw.rect(surf, (70, 70, 80), (120, 5, 160, 6))
        pygame.draw.rect(surf, (250, 200, 70), (120, 5, int(160 * self.progress), 6))
        text(surf, "MALL", (284, 1), 16, c.YELLOW)
        for i in range(MAX_HITS):
            col = (220, 60, 60) if i >= self.hits else (70, 70, 80)
            pygame.draw.rect(surf, col, (W - 14 - (MAX_HITS - i) * 14, 4, 10, 8), border_radius=2)
        live = len([cp for cp in self.cops if not cp["crash"]])
        if live:
            text(surf, "COPS %d" % live, (4, 20), 16, (120, 160, 255))
        surf.blit(self.faces[min(3, int(self.rage * 3.99))], (6, H - 36))
        if self.rage > 0.9 and int(self.time * 4) % 2 == 0:
            pygame.draw.circle(surf, (230, 230, 230), (14, H - 40), 3)
            pygame.draw.circle(surf, (230, 230, 230), (26, H - 42), 4)
        if self.turbo_cool > 0:
            pygame.draw.rect(surf, (70, 70, 80), (W - 70, H - 10, 64, 5))
            pygame.draw.rect(surf, (255, 150, 40), (W - 70, H - 10, int(64 * (1 - self.turbo_cool / TURBO_COOL)), 5))
        else:
            text(surf, "TURBO", (W - 52, H - 16), 14, (255, 170, 60))

    def draw_intro(self, surf):
        t = self.phase_t
        surf.fill((120, 80, 50))                                     # deck
        for y in range(0, H, 12):
            pygame.draw.line(surf, (100, 66, 40), (0, y), (W, y))
        pygame.draw.rect(surf, (150, 150, 162), (86, 50, 228, 156), border_radius=26)   # tub
        pygame.draw.rect(surf, (190, 190, 202), (90, 50, 220, 150), border_radius=24)
        pygame.draw.rect(surf, (70, 170, 210), (102, 62, 196, 126), border_radius=18)   # water
        pygame.draw.rect(surf, (110, 200, 232), (110, 68, 180, 10), border_radius=5)
        for i in range(14):                                          # bubbles
            bx = 110 + (i * 37 + int(t * 40)) % 180
            by = 180 - (i * 53 + int(t * 30)) % 110
            pygame.draw.circle(surf, (210, 240, 255), (bx, by), 2 + i % 3)
        jump = max(0.0, t - 7.6) * 260                               # leaps out at the end
        mood = "calm" if t < 2.0 else ("phone" if t < 5.6 else "angry")
        fig = tub_man(mood)
        hx, hy = 200, int(96 - jump)
        bobble = int(math.sin(t * 2) * 1.5) if mood == "calm" else (int(math.sin(t * 50) * 1.5) if mood == "angry" else 0)
        surf.blit(fig, (40 + bobble, 28 - int(jump)))
        if jump <= 0:                                                # the water closes round his chest
            pygame.draw.ellipse(surf, (70, 170, 210), (106, 150, 188, 44))
            for k in range(7):
                wx = 122 + k * 24 + int(math.sin(t * 3 + k) * 3)
                pygame.draw.arc(surf, (210, 240, 255), (wx, 146, 20, 8), 0.2, 2.9, 1)
        if 2.0 < t < 3.6:
            text(surf, "RING! RING!", (hx + 66, hy - 30), 18, c.YELLOW)
        for i in range(3):                                           # steam
            sy = 40 - (int(t * 20) + i * 15) % 40
            pygame.draw.circle(surf, (230, 230, 230), (130 + i * 70, sy), 6)
        if t < 2.0:
            self.textbox(surf, ["Uncle T, relaxing in the hot tub..."])
        elif t < 3.6:
            self.textbox(surf, ["*phone ringing*"])
        elif t < 5.6:
            self.textbox(surf, ["Unknown caller:", "\"Come check out the new iPhone!\""])
        elif t < 7.6:
            bubble(surf, "#@%&! ALICE! I'M IN THE #@%&! HOT TUB!", hx - 132, hy - 62, 18)
        else:
            self.textbox(surf, ["Uncle T heads for the car..."])
        if int(t * 2) % 2 == 0:
            text(surf, "Big button: skip", (W - 104, H - 14), 14, c.WHITE)

    def textbox(self, surf, lines):
        pygame.draw.rect(surf, (20, 20, 30), (20, H - 58, W - 40, 44), border_radius=6)
        pygame.draw.rect(surf, (240, 240, 240), (20, H - 58, W - 40, 44), 1, border_radius=6)
        for i, line in enumerate(lines):
            text(surf, line, (30, H - 52 + i * 16), 18, c.WHITE)

    def render(self, surf):
        super().render(surf)
        if self.state == "over" and self.end_reason:
            text(surf, self.end_reason, (W // 2, 30), 24, c.YELLOW if self.win else (255, 160, 160), center=True)


def make(**kw):
    return UncleT(**kw)


if __name__ == "__main__":
    c.main(make)
