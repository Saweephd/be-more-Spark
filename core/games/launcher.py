"""The game menu: pick a game with the D-pad, big button to play."""
import importlib

import pygame

from . import GAMES, common as c
from .. import tvmode
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
        self.sound = c._sound.Silent()
        self.tv_box = pygame.Rect(W - 92, 4, 88, 17)      # the TV mode switch, top right
        self.pitch = 18 if len(self.games) <= 10 else max(13, 180 // len(self.games))   # row spacing: a long list closes up

    def toggle_tv(self):
        tvmode.set_mode(not tvmode.on())
        self.sound.play("select")

    def step(self, dt, inp):
        self.time += dt
        if not self.games:
            return
        if "down" in inp.pressed:
            self.index = (self.index + 1) % len(self.games)
            self.sound.play("move")
        if "up" in inp.pressed:
            self.index = (self.index - 1) % len(self.games)
            self.sound.play("move")
        if "left" in inp.pressed or "right" in inp.pressed:
            self.toggle_tv()
        if inp.touch is not None and "a" in inp.pressed:
            if self.tv_box.inflate(8, 8).collidepoint(inp.touch):
                self.toggle_tv()
                inp.pressed.discard("a")
                return
            row = (inp.touch[1] - 26) // self.pitch
            if 0 <= row < len(self.games):
                self.index = row
        if "a" in inp.pressed or "start" in inp.pressed:
            self.choice = self.games[self.index][0]
            self.sound.play("select")
        if "b" in inp.pressed:
            self.done = True
            self.sound.play("back")

    def render(self, surf):
        surf.fill((18, 60, 66))
        for i in range(0, W, 20):
            pygame.draw.line(surf, (22, 70, 76), (i, 0), (i, H))
        text(surf, "GAMES", (W // 2, 3), 26, c.YELLOW, center=True)
        scores = c.load_scores(self.scores_path)
        for i, (name, title) in enumerate(self.games):
            y = 26 + i * self.pitch
            sel = i == self.index
            small = self.pitch < 18
            pygame.draw.rect(surf, (60, 190, 170) if sel else (30, 96, 100), (50, y, W - 100, self.pitch - 1), border_radius=4)
            text(surf, title, (64, y + (1 if small else 2)), 16 if small else 18, c.INK if sel else c.WHITE, shadow=not sel)
            text(surf, "best %d" % int(scores.get(name, 0)), (W - 124, y + (2 if small else 3)), 14, c.INK if sel else (170, 210, 210), shadow=False)
        tv = tvmode.on()
        pygame.draw.rect(surf, (240, 200, 70) if tv else (30, 96, 100), self.tv_box, border_radius=4)
        text(surf, "< TV: %s >" % ("ON" if tv else "OFF"), (self.tv_box.centerx, self.tv_box.y + 2), 16,
             c.INK if tv else c.WHITE, center=True, shadow=not tv)
        note = tvmode.hint() or self.message
        if note:
            text(surf, note, (W // 2, 208), 14, c.YELLOW if tvmode.hint() else c.WHITE, center=True)
        text(surf, "Up/down: choose  Left/right: TV  Big button: play", (W // 2, 224), 16, c.WHITE, center=True)


def run_menu(screen=None, max_frames=None):
    """Show the menu until the player leaves. Returns the result of the last game played."""
    own = screen is None
    if own:
        screen = c.open_screen()
        pygame.display.set_caption("BMO Games")
    canvas = pygame.Surface((W, H))
    clock = pygame.time.Clock()
    inp = c.Input()
    try:
        pygame.joystick.init()
    except pygame.error:
        pass
    pads = c.Pads()
    for i in range(pygame.joystick.get_count() if pygame.joystick.get_init() else 0):
        pads.add(i)
    menu = Menu()
    menu.sound = c._sound.get()
    menu.sound.music("menu")
    last = {"game": None, "played": False, "score": 0, "best": 0, "new_best": False, "title": ""}
    on_tv = tvmode.use_tv()
    start_held = 0.0
    frames = 0
    while not menu.done:
        dt = min(clock.tick(c.FPS) / 1000.0, 1 / 20)
        for ev in pygame.event.get():
            if pads.handle(ev, lambda slot: [inp]):
                continue
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
        if own and tvmode.use_tv() != on_tv:         # TV mode switched, or the TV connected: move the picture
            on_tv = tvmode.use_tv()
            pygame.display.quit()
            screen = c.open_screen()
            pygame.display.set_caption("BMO Games")
            pygame.event.clear()
            c._sound.reset()                          # and the sound goes with it
            menu.sound = c._sound.get()
            menu.sound.music("menu")
        if menu.choice:
            name, menu.choice = menu.choice, None
            game = importlib.import_module("core.games." + name).make()
            menu.sound.stop_music()
            res = c.run(game, screen=screen)
            menu.sound.music("menu")
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
    menu.sound.stop_music()
    if own:
        pygame.display.quit()
    return last
