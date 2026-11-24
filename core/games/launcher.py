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
        self.tv_box = pygame.Rect(278, 6, 116, 20)        # the TV mode switch, top right (in touch measurements)
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
            row = (inp.touch[1] * 2 - self.TOP) // self.ROW_H
            if 0 <= row < min(self.ROWS, len(self.games)):
                self.index = self.first_row() + row
        if "a" in inp.pressed or "start" in inp.pressed:
            self.choice = self.games[self.index][0]
            self.sound.play("select")
        if "back" in inp.pressed:                    # the minus (select) button; the triangle no longer leaves,
            self.done = True                          # because it was pressed by accident too often
            self.sound.play("back")

    ROWS, ROW_H, TOP = 7, 52, 64                        # the list on the full 800 x 480 screen

    def first_row(self):
        """The list scrolls so the chosen game stays near the middle."""
        return max(0, min(len(self.games) - self.ROWS, self.index - self.ROWS // 2))

    def render(self, surf):
        surf.fill((14, 44, 50))

    def render_hd(self, screen):
        """Drawn at full resolution with large smooth lettering, so it reads from across the room on a big TV."""
        from .alien_storm import hud
        screen.fill((12, 40, 46))
        for y in range(0, 480, 4):
            k = y / 480.0
            pygame.draw.rect(screen, (int(14 + 10 * k), int(52 - 16 * k), int(60 - 16 * k)), (0, y, 800, 4))
        hud.label(screen, "GAMES", (24, 10), 56, c.YELLOW, bold=True)
        tv = tvmode.on()
        box = pygame.Rect(556, 12, 232, 40)
        pygame.draw.rect(screen, (240, 200, 70) if tv else (26, 84, 90), box, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), box, 2, border_radius=10)
        hud.label(screen, "<  TV: %s  >" % ("ON" if tv else "OFF"), (box.centerx, box.y + 8), 30, c.INK if tv else (255, 255, 255),
                  center=True, bold=True, shadow=not tv)
        scores = c.load_scores(self.scores_path)
        first = self.first_row()
        for row in range(min(self.ROWS, len(self.games))):
            i = first + row
            name, title = self.games[i]
            y = self.TOP + row * self.ROW_H
            sel = i == self.index
            r = pygame.Rect(16 if sel else 40, y, 768 if sel else 720, self.ROW_H - 6)
            if sel:
                pygame.draw.rect(screen, (255, 255, 255), r.inflate(8, 8), border_radius=14)
                pygame.draw.rect(screen, (255, 214, 70), r, border_radius=12)
                pygame.draw.polygon(screen, c.INK, [(r.x + 14, y + 10), (r.x + 34, y + 23), (r.x + 14, y + 36)])
                hud.label(screen, title, (r.x + 48, y + 6), 44, c.INK, bold=True, shadow=False)
                hud.label(screen, "best %d" % int(scores.get(name, 0)), (r.right - 150, y + 12), 30, (60, 50, 20), shadow=False)
            else:
                pygame.draw.rect(screen, (24, 78, 84), r, border_radius=10)
                hud.label(screen, title, (r.x + 24, y + 9), 36, (236, 244, 244))
                hud.label(screen, "best %d" % int(scores.get(name, 0)), (r.right - 140, y + 13), 26, (150, 200, 200), shadow=False)
        if first > 0:
            pygame.draw.polygon(screen, (255, 255, 255), [(388, self.TOP - 4), (412, self.TOP - 4), (400, self.TOP - 16)])
        if first + self.ROWS < len(self.games):
            yb = self.TOP + self.ROWS * self.ROW_H - 2
            pygame.draw.polygon(screen, (255, 255, 255), [(388, yb), (412, yb), (400, yb + 12)])
        hud.label(screen, "%d of %d" % (self.index + 1, len(self.games)), (780 - 90, 444), 24, (170, 210, 210), shadow=False)
        note = tvmode.hint() or self.message
        if note:
            f = hud.font(24)
            while f.size(note)[0] > 330 and len(note) > 8:
                note = note[:-4] + "..."
            hud.label(screen, note, (380, 22), 24, c.YELLOW if tvmode.hint() else (255, 255, 255), center=True)
        hud.label(screen, "Big button: play     Left/right: TV     Minus: leave", (400, 444), 24, (255, 255, 255), center=True)


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
        menu.render_hd(screen)
        pygame.display.flip()
        inp.end_frame()
        frames += 1
        if max_frames is not None and frames >= max_frames:
            break
    menu.sound.stop_music()
    if own:
        pygame.display.quit()
    return last
