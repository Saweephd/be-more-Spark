"""The game menu: pick a game with the D-pad, big button to play."""
import importlib

import pygame

from . import GAMES, common as c
from .common import H, W, text


def available():
    """Games whose module is present, in menu order."""
    out = []
    for name, title in GAMES.items():
        try:
            importlib.import_module("core.games." + name)
            out.append((name, title))
        except ImportError:
            pass
    return out


class Menu:
    def __init__(self, games=None, scores_path=None):
        self.games = games if games is not None else available()
        self.index = 0
        self.choice = None
        self.done = False
        self.time = 0.0
        self.scores_path = scores_path
        self.message = ""

    def step(self, dt, inp):
        self.time += dt
        if not self.games:
            return
        if "down" in inp.pressed:
            self.index = (self.index + 1) % len(self.games)
        if "up" in inp.pressed:
            self.index = (self.index - 1) % len(self.games)
        if inp.touch is not None and "a" in inp.pressed:
            row = (inp.touch[1] - 78) // 34
            if 0 <= row < len(self.games):
                self.index = row
        if "a" in inp.pressed or "start" in inp.pressed:
            self.choice = self.games[self.index][0]
        if "b" in inp.pressed:
            self.done = True

    def render(self, surf):
        surf.fill((18, 60, 66))
        for i in range(0, W, 20):
            pygame.draw.line(surf, (22, 70, 76), (i, 0), (i, H))
        text(surf, "GAMES", (W // 2, 22), 44, c.YELLOW, center=True)
        scores = c.load_scores(self.scores_path)
        for i, (name, title) in enumerate(self.games):
            y = 78 + i * 34
            sel = i == self.index
            pygame.draw.rect(surf, (60, 190, 170) if sel else (30, 96, 100), (50, y, W - 100, 28), border_radius=4)
            text(surf, title, (64, y + 6), 24, c.INK if sel else c.WHITE, shadow=not sel)
            text(surf, "best %d" % int(scores.get(name, 0)), (W - 124, y + 8), 18, c.INK if sel else (170, 210, 210), shadow=False)
        if self.message:
            text(surf, self.message, (W // 2, 188), 18, c.WHITE, center=True)
        text(surf, "D-pad: choose   Big button: play   Triangle: back", (W // 2, 214), 16, c.WHITE, center=True)


def run_menu(screen=None, max_frames=None):
    """Show the menu until the player leaves. Returns the result of the last game played."""
    own = screen is None
    if own:
        screen = c.open_screen()
        pygame.display.set_caption("BMO Games")
    canvas = pygame.Surface((W, H))
    clock = pygame.time.Clock()
    inp = c.Input()
    menu = Menu()
    last = {"game": None, "played": False, "score": 0, "best": 0, "new_best": False, "title": ""}
    start_held = 0.0
    frames = 0
    while not menu.done:
        dt = min(clock.tick(c.FPS) / 1000.0, 1 / 20)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                menu.done = True
            elif ev.type == pygame.KEYDOWN and ev.key in c.KEYMAP:
                inp.down(c.KEYMAP[ev.key])
            elif ev.type == pygame.KEYUP and ev.key in c.KEYMAP:
                inp.up(c.KEYMAP[ev.key])
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                inp.touch = (ev.pos[0] // c.SCALE, ev.pos[1] // c.SCALE)
                inp.down("a")
            elif ev.type == pygame.MOUSEBUTTONUP:
                inp.touch = None
                inp.up("a")
        start_held = start_held + dt if "start" in inp.held else 0.0
        if start_held >= c.QUIT_HOLD_S:
            menu.done = True
        menu.step(dt, inp)
        if menu.choice:
            name, menu.choice = menu.choice, None
            game = importlib.import_module("core.games." + name).make()
            res = c.run(game, screen=screen)
            if res.get("played"):
                last = res
                menu.message = "%s: %d" % (res["title"], res["score"])
            inp = c.Input()
            start_held = 0.0
            pygame.event.clear()
        menu.render(canvas)
        pygame.transform.scale(canvas, screen.get_size(), screen)
        pygame.display.flip()
        inp.end_frame()
        frames += 1
        if max_frames is not None and frames >= max_frames:
            break
    if own:
        pygame.display.quit()
    return last
