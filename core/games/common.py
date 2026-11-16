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


class Input:
    """What the player is doing this frame."""

    def __init__(self):
        self.held = set()        # buttons currently down
        self.pressed = set()     # buttons that went down this frame
        self.touch = None        # (x, y) on the 400x240 canvas while a finger is down

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


def save_score(name, score, path=None):
    """Record a score. Returns (best, is_new_best)."""
    path = path or SCORES_FILE
    scores = load_scores(path)
    best = int(scores.get(name, 0))
    new_best = score > best
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

    def __init__(self, seed=None, scores_path=None):
        self.rng = random.Random(seed)
        self.scores_path = scores_path
        self.state = "title"     # title, play, paused, over
        self.score = 0
        self.best = int(load_scores(scores_path).get(self.name, 0))
        self.new_best = False
        self.time = 0.0
        self.last_score = 0

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

    def game_over(self):
        self.state = "over"
        self.last_score = int(self.score)
        self.best, self.new_best = save_score(self.name, int(self.score), self.scores_path)
        self.over_time = self.time

    def step(self, dt, inp):
        """Advance one frame, including the title, pause and game over screens."""
        self.time += dt
        if self.state == "title":
            if "a" in inp.pressed or "start" in inp.pressed:
                self.reset()
                self.state = "play"
        elif self.state == "play":
            if "start" in inp.pressed:
                self.state = "paused"
            else:
                self.update(dt, inp)
        elif self.state == "paused":
            if "start" in inp.pressed or "a" in inp.pressed:
                self.state = "play"
        elif self.state == "over":
            if self.time - self.over_time > 0.8 and ("a" in inp.pressed or "start" in inp.pressed):
                self.reset()
                self.new_best = False
                self.state = "play"

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
            if int(self.time * 2) % 2 == 0:
                text(surf, "Press the big button", (W // 2, 190), 20, YELLOW, center=True)
            text(surf, "Best %d" % self.best, (W // 2, 216), 18, WHITE, center=True)
            return
        self.draw(surf)
        if self.state == "paused":
            text(surf, "PAUSED", (W // 2, 100), 40, YELLOW, center=True)
            text(surf, "Hold the small button to quit", (W // 2, 140), 18, WHITE, center=True)
        elif self.state == "over":
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 140))
            surf.blit(shade, (0, 0))
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
    start_held = 0.0
    frames = 0
    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 1 / 20)
        for ev in pygame.event.get():
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
        pygame.transform.scale(canvas, screen.get_size(), screen)
        pygame.display.flip()
        inp.end_frame()
        frames += 1
        if max_frames is not None and frames >= max_frames:
            running = False
    res = game.result()
    if own:
        pygame.display.quit()
    return res


def main(make):
    res = run(make())
    print("RESULT " + json.dumps(res), flush=True)
    return 0
