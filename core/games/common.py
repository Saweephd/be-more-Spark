"""Shared code for BMO's games: screen, input, pixel art, text, scores, main loop.

Games draw on a small 400 by 240 canvas that is doubled onto the 800 by 480
screen, which gives the chunky look of an old console and keeps drawing cheap.

Controls (the face buttons arrive as keyboard keys from the Feather board):
    D-pad          arrow keys
    big circle     Space        button A
    triangle       Left Shift   button B
    small circle   Enter        start / pause; hold two seconds to quit
A tap on the touchscreen also counts as button A.
"""
import json
import os
import random
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

from . import sound as _sound  # noqa: E402

W, H = 400, 240
SCALE = 2
FPS = 60
QUIT_HOLD_S = 2.0
SCORES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scores.json")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
INK = (24, 24, 32)
YELLOW = (255, 220, 80)
RED = (220, 60, 60)

KEYMAP = {
    pygame.K_UP: "up", pygame.K_DOWN: "down", pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
    pygame.K_SPACE: "a", pygame.K_z: "a",
    pygame.K_LSHIFT: "b", pygame.K_x: "b",
    pygame.K_RETURN: "start",
}


PAD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pad.json")
# Button numbers differ between gamepads; these cover the common layouts. pad.json can override them.
DEFAULT_PAD = {"a": [0, 2], "b": [1, 3], "start": [6, 7, 9, 10, 11]}
AXIS_ON, AXIS_OFF = 0.55, 0.35


def load_pad_map(path=None):
    try:
        with open(path or PAD_FILE) as fh:
            data = json.load(fh)
        return {k: [int(x) for x in v] for k, v in data.items() if k in ("a", "b", "start")}
    except (OSError, ValueError, TypeError, AttributeError):
        return dict(DEFAULT_PAD)


class Pads:
    """Bluetooth or USB gamepads. Pad 1 drives player one (as do BMO's own buttons); pad 2 drives player two."""

    def __init__(self, pad_map=None):
        self.map = pad_map or load_pad_map()
        self.sticks = {}          # instance id -> (slot, joystick)
        self.inputs = []          # one Input per slot
        self.dirs = {}            # (slot, source) -> set of directions held from that source

    def slot_for(self, instance_id):
        entry = self.sticks.get(instance_id)
        return entry[0] if entry else None

    def add(self, device_index):
        try:
            js = pygame.joystick.Joystick(device_index)
            js.init()
        except pygame.error:
            return
        iid = js.get_instance_id()
        if iid in self.sticks:
            return
        used = {slot for slot, _ in self.sticks.values()}
        slot = next(i for i in range(8) if i not in used)
        self.sticks[iid] = (slot, js)
        while len(self.inputs) <= slot:
            self.inputs.append(Input())

    def remove(self, instance_id):
        self.sticks.pop(instance_id, None)

    def button_name(self, button):
        for name, numbers in self.map.items():
            if button in numbers:
                return name
        return None

    def set_dirs(self, slot, source, active, targets):
        before = self.dirs.get((slot, source), set())
        for d in before - active:
            for t in targets:
                t.up(d)
        for d in active - before:
            for t in targets:
                t.down(d)
        self.dirs[(slot, source)] = set(active)

    def handle(self, ev, targets_for):
        """Feed one pygame event. targets_for(slot) gives the Inputs that pad slot drives."""
        if ev.type == pygame.JOYDEVICEADDED:
            self.add(ev.device_index)
            return True
        if ev.type == pygame.JOYDEVICEREMOVED:
            self.remove(ev.instance_id)
            return True
        if ev.type not in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP, pygame.JOYHATMOTION, pygame.JOYAXISMOTION):
            return False
        slot = self.slot_for(ev.instance_id)
        if slot is None:
            return True
        targets = targets_for(slot)
        if ev.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP):
            name = self.button_name(ev.button)
            if name:
                for t in targets:
                    (t.down if ev.type == pygame.JOYBUTTONDOWN else t.up)(name)
        elif ev.type == pygame.JOYHATMOTION and ev.hat == 0:
            x, y = ev.value
            active = {d for d, on in (("left", x < 0), ("right", x > 0), ("up", y > 0), ("down", y < 0)) if on}
            self.set_dirs(slot, "hat", active, targets)
        elif ev.type == pygame.JOYAXISMOTION and ev.axis in (0, 1):
            key = (slot, "axis")
            held = set(self.dirs.get(key, set()))
            neg, pos = ("left", "right") if ev.axis == 0 else ("up", "down")
            for d, on, off in ((neg, ev.value < -AXIS_ON, ev.value > -AXIS_OFF), (pos, ev.value > AXIS_ON, ev.value < AXIS_OFF)):
                if on:
                    held.add(d)
                elif off:
                    held.discard(d)
            self.set_dirs(slot, "axis", held, targets)
        return True


class Input:
    """What the player is doing this frame."""

    def __init__(self):
        self.held = set()        # buttons currently down
        self.pressed = set()     # buttons that went down this frame
        self.touch = None        # (x, y) on the 400x240 canvas while a finger is down
        self.p2 = None           # player two's Input in two-player games, when a second pad is connected

    def down(self, name):
        if name not in self.held:
            self.pressed.add(name)
        self.held.add(name)

    def up(self, name):
        self.held.discard(name)

    def end_frame(self):
        self.pressed = set()


# ---------- pixel art ----------
def sprite(rows, palette, scale=1):
    """Build a Surface from rows of characters. '.' and ' ' are transparent."""
    h = len(rows)
    w = max(len(r) for r in rows)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in ". ":
                continue
            surf.set_at((x, y), palette[ch])
    if scale != 1:
        surf = pygame.transform.scale(surf, (w * scale, h * scale))
    return surf


def flip(surf):
    return pygame.transform.flip(surf, True, False)


_fonts = {}


def text(surf, msg, pos, size=16, color=WHITE, center=False, shadow=True):
    """Draw text without smoothing so it stays crisp when doubled."""
    font = _fonts.get(size)
    if font is None:
        font = _fonts[size] = pygame.font.Font(None, size)
    img = font.render(str(msg), False, color)
    x, y = pos
    if center:
        x -= img.get_width() // 2
    if shadow:
        surf.blit(font.render(str(msg), False, INK), (x + 1, y + 1))
    surf.blit(img, (x, y))
    return img.get_width()


# ---------- scores ----------
def load_scores(path=None):
    try:
        with open(path or SCORES_FILE) as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_score(name, score, path=None, best=True):
    """Record a score. Returns (best, is_new_best). With best=False the value is simply stored."""
    path = path or SCORES_FILE
    scores = load_scores(path)
    old = int(scores.get(name, 0))
    new_best = score > old or (not best and score != old)
    best = old
    if new_best:
        scores[name] = int(score)
        try:
            tmp = path + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(scores, fh)
            os.replace(tmp, path)
        except OSError:
            pass
        best = int(score)
    return best, new_best


# ---------- game base ----------
class Game:
    name = "game"
    title = "Game"
    help_lines = ()
    title_color = YELLOW
    music = None            # name of this game's tune in sound.TUNES
    sound = _sound.Silent()  # run() swaps in the real player
    levels = ()             # level names: the title screen lets you start at any level reached
    modes = ()              # play modes chosen on the title screen, for example ("Relax", "Challenge")

    def __init__(self, seed=None, scores_path=None):
        self.rng = random.Random(seed)
        self.scores_path = scores_path
        self.state = "title"     # title, play, paused, over
        self.score = 0
        self.best = int(load_scores(scores_path).get(self.name, 0))
        self.new_best = False
        self.time = 0.0
        self.last_score = 0
        saved = load_scores(scores_path)
        self.unlocked = max(1, min(len(self.levels) or 1, int(saved.get(self.name + "_level", 1))))
        self.level_choice = self.unlocked - 1    # index of the level to start on
        self.mode = int(saved.get(self.name + "_mode", 0)) % (len(self.modes) or 1)
        self.option_row = 0

    # games override these three
    def reset(self):
        self.score = 0

    def update(self, dt, inp):
        pass

    def draw(self, surf):
        surf.fill(BLACK)

    def draw_title_art(self, surf):
        """Optional picture behind the title text."""
        self.draw(surf)

    def sfx(self, name):
        self.sound.play(name)

    def reach_level(self, index):
        """Call when the player gets to level `index` (from 0): it becomes choosable on the title screen."""
        if index + 1 > self.unlocked and index < len(self.levels):
            self.unlocked = index + 1
            save_score(self.name + "_level", self.unlocked, self.scores_path)

    def title_options(self):
        rows = []
        if len(self.levels) > 1 and self.unlocked > 1:
            rows.append("level")
        if len(self.modes) > 1:
            rows.append("mode")
        return rows

    def title_input(self, inp):
        rows = self.title_options()
        if not rows:
            return
        self.option_row = min(self.option_row, len(rows) - 1)
        if "up" in inp.pressed and self.option_row > 0:
            self.option_row -= 1
            self.sfx("select")
        if "down" in inp.pressed and self.option_row < len(rows) - 1:
            self.option_row += 1
            self.sfx("select")
        step = (1 if "right" in inp.pressed else 0) - (1 if "left" in inp.pressed else 0)
        if not step:
            return
        if rows[self.option_row] == "level":
            self.level_choice = (self.level_choice + step) % self.unlocked
        else:
            self.mode = (self.mode + step) % len(self.modes)
            save_score(self.name + "_mode", self.mode, self.scores_path, best=False)
        self.sfx("select")

    def game_over(self):
        self.sound.stop_music()
        self.sfx("win" if getattr(self, "win", False) else "over")
        self.state = "over"
        self.last_score = int(self.score)
        self.best, self.new_best = save_score(self.name, int(self.score), self.scores_path)
        self.over_time = self.time

    def step(self, dt, inp):
        """Advance one frame, including the title, pause and game over screens."""
        self.time += dt
        if self.state == "title":
            self.title_input(inp)
            if "a" in inp.pressed or "start" in inp.pressed:
                self.reset()
                self.state = "play"
                self.sfx("start")
                self.sound.music(self.music)
        elif self.state == "play":
            if "start" in inp.pressed:
                self.state = "paused"
                self.sfx("pause")
                self.sound.pause_music()
            else:
                self.update(dt, inp)
        elif self.state == "paused":
            if "start" in inp.pressed or "a" in inp.pressed:
                self.state = "play"
                self.sfx("pause")
                self.sound.resume_music()
        elif self.state == "over":
            if self.time - self.over_time > 0.8 and ("a" in inp.pressed or "start" in inp.pressed):
                self.reset()
                self.new_best = False
                self.state = "play"
                self.sfx("start")
                self.sound.music(self.music)

    def render(self, surf):
        if self.state == "title":
            self.draw_title_art(surf)
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 120))
            surf.blit(shade, (0, 0))
            text(surf, self.title, (W // 2, 44), 44, self.title_color, center=True)
            y = 104
            for line in self.help_lines:
                text(surf, line, (W // 2, y), 18, WHITE, center=True)
                y += 16
            rows = self.title_options()
            oy = 196 - 18 * len(rows)
            for i, row in enumerate(rows):
                if row == "level":
                    label = "Start at: %d. %s" % (self.level_choice + 1, self.levels[self.level_choice])
                else:
                    label = "Mode: %s" % self.modes[self.mode]
                col = YELLOW if i == self.option_row else WHITE
                text(surf, "<  %s  >" % label, (W // 2, oy + 18 * i), 18, col, center=True)
            if int(self.time * 2) % 2 == 0:
                text(surf, "Press the big button", (W // 2, 200), 20, YELLOW, center=True)
            text(surf, "Best %d" % self.best, (W // 2, 222), 18, WHITE, center=True)
            return
        self.draw(surf)
        if self.state == "paused":
            text(surf, "PAUSED", (W // 2, 100), 40, YELLOW, center=True)
            text(surf, "Hold the small button to quit", (W // 2, 140), 18, WHITE, center=True)
        elif self.state == "over":
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 140))
            surf.blit(shade, (0, 0))
            if getattr(self, "win", False):
                text(surf, "YOU WIN!", (W // 2, 60), 44, YELLOW, center=True)
            else:
                text(surf, "GAME OVER", (W // 2, 60), 44, RED, center=True)
            text(surf, "Score %d" % self.last_score, (W // 2, 112), 26, WHITE, center=True)
            if self.new_best:
                text(surf, "New best!", (W // 2, 138), 22, YELLOW, center=True)
            else:
                text(surf, "Best %d" % self.best, (W // 2, 138), 20, WHITE, center=True)
            text(surf, "Big button: play again", (W // 2, 176), 18, WHITE, center=True)
            text(surf, "Hold small button: quit", (W // 2, 194), 18, WHITE, center=True)

    def result(self):
        played = self.state in ("over", "play", "paused") or self.last_score > 0
        score = int(self.score) if self.state in ("play", "paused") else self.last_score
        if self.state in ("play", "paused") and score > 0:
            self.best, self.new_best = save_score(self.name, score, self.scores_path)
        return {"game": self.name, "title": self.title, "played": bool(played),
                "score": score, "best": self.best, "new_best": bool(self.new_best)}


def open_screen():
    """Open the 800x480 game screen. Set BMO_GAME_WINDOWED=1 for a desktop window."""
    pygame.display.init()
    pygame.font.init()
    flags = 0 if os.environ.get("BMO_GAME_WINDOWED") else pygame.FULLSCREEN
    second = 0
    if os.path.exists("/tmp/bmo_streaming") and pygame.display.get_num_displays() > 1:
        second = 1                                   # a TV stream is running: play on the screen the TV shows
    try:
        screen = pygame.display.set_mode((W * SCALE, H * SCALE), flags, display=second)
    except pygame.error:
        screen = pygame.display.set_mode((W * SCALE, H * SCALE), flags)
    pygame.mouse.set_visible(False)
    return screen


def run(game, screen=None, max_frames=None):
    """Play `game` until the player quits. Returns the result dictionary."""
    own = screen is None
    if own:
        screen = open_screen()
        pygame.display.set_caption(game.title)
    canvas = pygame.Surface((W, H))
    clock = pygame.time.Clock()
    inp = Input()
    try:
        pygame.joystick.init()
    except pygame.error:
        pass
    pads = Pads()
    for i in range(pygame.joystick.get_count() if pygame.joystick.get_init() else 0):
        pads.add(i)
    coop = getattr(game, "players_max", 1) > 1

    def targets_for(slot):
        # In two-player games the second pad is player two; every other pad is player one.
        if coop and slot == 1:
            while len(pads.inputs) < 2:
                pads.inputs.append(Input())
            inp.p2 = pads.inputs[1]
            return [pads.inputs[1]]
        return [inp]
    game.sound = _sound.get()
    start_held = 0.0
    frames = 0
    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 1 / 20)
        for ev in pygame.event.get():
            if pads.handle(ev, targets_for):
                continue
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key in KEYMAP:
                    inp.down(KEYMAP[ev.key])
            elif ev.type == pygame.KEYUP:
                if ev.key in KEYMAP:
                    inp.up(KEYMAP[ev.key])
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                inp.touch = (ev.pos[0] // SCALE, ev.pos[1] // SCALE)
                inp.down("a")
            elif ev.type == pygame.MOUSEMOTION and inp.touch is not None:
                inp.touch = (ev.pos[0] // SCALE, ev.pos[1] // SCALE)
            elif ev.type == pygame.MOUSEBUTTONUP:
                inp.touch = None
                inp.up("a")
        if "start" in inp.held:
            start_held += dt
            if start_held >= QUIT_HOLD_S:
                running = False
        else:
            start_held = 0.0
        game.step(dt, inp)
        game.render(canvas)
        if start_held > 0.4:
            pygame.draw.rect(canvas, INK, (W // 2 - 62, H - 16, 124, 10))
            pygame.draw.rect(canvas, YELLOW, (W // 2 - 60, H - 14, int(120 * min(1, start_held / QUIT_HOLD_S)), 6))
        if not getattr(game, "hd_only", False):
            pygame.transform.scale(canvas, screen.get_size(), screen)
        hd = getattr(game, "render_hd", None)        # sharp full resolution extras, drawn over the doubled picture
        if hd is not None:
            hd(screen)
        pygame.display.flip()
        inp.end_frame()
        if inp.p2 is not None:
            inp.p2.end_frame()
        frames += 1
        if max_frames is not None and frames >= max_frames:
            running = False
    game.sound.stop_music()
    res = game.result()
    if own:
        pygame.display.quit()
    return res


def main(make):
    res = run(make())
    print("RESULT " + json.dumps(res), flush=True)
    return 0
