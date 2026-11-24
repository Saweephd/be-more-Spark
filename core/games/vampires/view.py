"""Everything Vampires, Oh Well... puts on the screen, drawn at the full 800 x 480 (the game's own
measurements are half that, so every position is doubled here)."""
import math

import pygame

from ..alien_storm import hud
from . import art, cards, levels

FLOOR = levels.FLOOR
K = art.K


def _shade(col, f):
    return tuple(max(0, min(255, int(v * f))) for v in col)


def _text(screen, msg, pos, size, col, center=False, bold=True):
    """Text with a dark edge all round, readable over anything."""
    f = hud.font(size, bold)
    img = f.render(msg, True, col)
    x, y = pos
    if center:
        x -= img.get_width() // 2
    edge = f.render(msg, True, art.INK)
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (2, 3)):
        screen.blit(edge, (x + dx, y + dy))
    screen.blit(img, (x, y))
    return img.get_width()


def world(g, screen):
    shake = g.rng.choice((-4, 4)) if getattr(g, "shake", 0) > 0 and g.state == "play" else 0
    cam = g.cam * 2 + shake
    theme = art.THEMES[g.stage]
    wall = art.wall(g.stage)
    off = int(cam * 0.55) % wall.get_width()
    screen.blit(wall, (-off, 0))
    if wall.get_width() - off < 800:
        screen.blit(wall, (wall.get_width() - off, 0))
    fy = FLOOR * 2
    floor = theme[3]
    for a, b in g.level["ground"]:                                     # the floor, in slabs
        x0, x1 = int(a * 2 - cam), int(b * 2 - cam)
        if x1 < 0 or x0 > 800:
            continue
        pygame.draw.rect(screen, _shade(floor, 0.62), (x0, fy, x1 - x0, 480 - fy))
        pygame.draw.rect(screen, floor, (x0, fy, x1 - x0, 22))
        pygame.draw.rect(screen, _shade(floor, 1.5), (x0, fy, x1 - x0, 4))
        pygame.draw.rect(screen, _shade(floor, 0.45), (x0, fy + 22, x1 - x0, 3))
        for sx in range(int(a) * 2 // 64 * 64, int(b) * 2, 64):
            px = int(sx - cam)
            if x0 < px < x1:
                pygame.draw.line(screen, _shade(floor, 0.7), (px, fy + 4), (px, fy + 22), 2)
                pygame.draw.line(screen, _shade(floor, 0.45), (px + 32, fy + 25), (px + 32, 480), 2)
    for (_, end), (start, _) in zip(g.level["ground"], g.level["ground"][1:]):    # holes in it
        x0, x1 = int(end * 2 - cam), int(start * 2 - cam)
        if x1 < 0 or x0 > 800:
            continue
        for i in range(8):
            pygame.draw.rect(screen, (max(0, 26 - i * 4), max(0, 10 - i * 2), max(0, 30 - i * 4)), (x0, fy + i * 8, x1 - x0, 8))
        pygame.draw.rect(screen, _shade(floor, 0.45), (x0 - 3, fy, 3, 64)); pygame.draw.rect(screen, _shade(floor, 0.45), (x1, fy, 3, 64))
        for sx in range(x0 + 6, x1 - 6, 14):                              # something sharp at the bottom
            pygame.draw.polygon(screen, (70, 64, 84), [(sx, 480), (sx + 7, 452), (sx + 14, 480)])
    for lx, ly, lw in g.level["ledges"]:                                # catwalks
        x0, y0, w = int(lx * 2 - cam), ly * 2, lw * 2
        if x0 + w < 0 or x0 > 800:
            continue
        shade = pygame.Surface((w, 10), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 70))
        screen.blit(shade, (x0 + 6, y0 + 22))
        pygame.draw.rect(screen, (60, 62, 76), (x0, y0 + 10, w, 8))
        pygame.draw.rect(screen, (136, 140, 156), (x0 - 2, y0, w + 4, 10), border_radius=3)
        pygame.draw.rect(screen, (190, 194, 210), (x0, y0, w, 3))
        for k in range(x0 + 10, x0 + w - 4, 28):
            pygame.draw.circle(screen, (80, 84, 100), (k, y0 + 6), 2)
        for bx in (x0 + 8, x0 + w - 8):                                    # brackets
            pygame.draw.polygon(screen, (60, 62, 76), [(bx - 5, y0 + 18), (bx + 5, y0 + 18), (bx, y0 + 40)])
    lit = []
    for lamp in g.lamps:
        x, y = int(lamp[0] * 2 - cam), lamp[1] * 2
        if -60 < x < 860:
            img = art.hd_small("lamp")
            screen.blit(img, (x - img.get_width() // 2, y - img.get_height() + 4))
            lit.append((x, y - 30, 70, (70, 60, 26)))
    for chest in g.chests:
        if chest:
            x, y = int(chest[0] * 2 - cam), chest[1] * 2
            img = art.hd_small("chest", size=2.6)
            screen.blit(img, (x - img.get_width() // 2, y - img.get_height() + 6))
            if int(g.time * 3) % 3 == 0:                                   # a glint, so chests are noticed
                gx, gy = x + 14, y - 44
                pygame.draw.line(screen, (255, 250, 200), (gx - 7, gy), (gx + 7, gy), 2); pygame.draw.line(screen, (255, 250, 200), (gx, gy - 7), (gx, gy + 7), 2)
    for d in g.drops:
        img = art.hd_small(d["kind"], size=2.4)
        bob = int(math.sin(g.time * 6 + d["x"]) * 3)
        screen.blit(img, (int(d["x"] * 2 - cam) - img.get_width() // 2, int(d["y"] * 2) - img.get_height() // 2 - 8 + bob))
        if d["kind"] == "card":
            lit.append((int(d["x"] * 2 - cam), int(d["y"] * 2) - 10, 60, (60, 40, 80)))

    def shadow(x, y, w):
        if y >= fy - 2 or any(abs(y - ly * 2) < 3 for _, ly, _ in g.level["ledges"]):
            blob = pygame.Surface((w, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(blob, (0, 0, 0, 90), (0, 0, w, 12))
            screen.blit(blob, (x - w // 2, y - 4))

    for b in g.beasts:
        img = art.hd_monster(b.kind, int(b.t * 5) % 2, b.scale, b.look, b.flash > 0, b.face)
        x, y = int(b.x * 2 - cam), int(b.y * 2)
        if not b.flies():
            shadow(x, y, int(img.get_width() * 0.7))
        screen.blit(img, (x - img.get_width() // 2, y - img.get_height() + int(2 * K) + art.PAD))
        if b.boss and b.kind in ("vampire", "ghost"):
            lit.append((x, y - img.get_height() // 2, 110, (50, 16, 30) if b.kind == "vampire" else (24, 44, 60)))
    for p in g.players:
        if p.out or (p.inv > 0 and int(g.time * 20) % 2):
            continue
        if "bat" in p.fx:
            pose, frame = "bat", int(g.time * 10) % 2
        elif p.hurt_t > 0:
            pose, frame = "hurt", 0
        elif p.attack_t > 0:
            pose, frame = "attack", 0
        elif not p.ground:
            pose, frame = "jump", 0
        elif abs(p.vx) > 1:
            pose, frame = "walk", int(p.walk_t * 9) % 4
        else:
            pose, frame = "stand", 0
        img = art.hd_hunter(p.kind, pose, frame, p.fire and pose == "attack", p.face)
        x, y = int(p.x * 2 - cam), int(p.y * 2)
        shadow(x, y, 54)
        ax = 20 * K if p.face > 0 else (art.HW - 20) * K
        screen.blit(img, (int(x - ax) - art.PAD, int(y - art.HH * K + K) - art.PAD))
        if p.attack_t > 0 and pose == "attack":                          # the swish of the swing
            reach = p.reach() * 2
            arc = pygame.Surface((reach + 30, 70), pygame.SRCALPHA)
            col = (255, 170, 70, 150) if p.fire else (255, 255, 255, 120)
            pygame.draw.arc(arc, col, (-reach, 0, reach * 2 + 20, 70), -0.9, 0.9, 6)
            if p.face < 0:
                arc = pygame.transform.flip(arc, True, False)
            screen.blit(arc, (x + (10 if p.face > 0 else -reach - 40), y - 86))
            if p.fire:
                lit.append((x + p.face * reach, y - 50, 60, (90, 50, 10)))
        if "garlic" in p.fx:
            for i in range(10):
                a = g.time * 3 + i * math.pi / 5
                gx, gy = int(x + math.cos(a) * 48), int(y - 44 + math.sin(a) * 48)
                pygame.draw.circle(screen, art.INK, (gx, gy), 6); pygame.draw.circle(screen, (250, 240, 200), (gx, gy), 4)
        if "hallpass" in p.fx:
            friend = art.hd_monster("ghost", int(g.time * 4) % 2, 0.7, None, False, p.face)
            screen.blit(friend, (int(x + math.cos(g.time * 2) * 60) - 24, int(y - 120 + math.sin(g.time * 3) * 12)))
        if "coffee" in p.fx and int(g.time * 12) % 2:
            pygame.draw.line(screen, (255, 230, 150), (x - p.face * 30, y - 60), (x - p.face * 56, y - 60), 3)
            pygame.draw.line(screen, (255, 230, 150), (x - p.face * 26, y - 36), (x - p.face * 50, y - 36), 3)
    for s in g.shots:
        img = art.hd_small(s["kind"], s["vx"] >= 0, 2.4)
        screen.blit(img, (int(s["x"] * 2 - cam) - img.get_width() // 2, int(s["y"] * 2) - (img.get_height() - 6 if s["kind"] == "wave" else img.get_height() // 2)))
        if s["kind"] in ("orb", "scream", "wave"):
            lit.append((int(s["x"] * 2 - cam), int(s["y"] * 2) - 6, 44, (60, 20, 34) if s["kind"] == "orb" else (40, 50, 60)))
    for q in getattr(g, "sparks", []):
        k = q[4] / q[5]
        pygame.draw.circle(screen, q[6], (int(q[0] * 2 - cam), int(q[1] * 2)), max(1, int(5 * k)))
    for x, y, r, col in lit:                                              # lights are added, the dark is laid over
        screen.blit(art.glow(r, col), (x - r, y - r), special_flags=pygame.BLEND_RGB_ADD)
    beams = art.beams(g.stage)
    boff = int(cam * 1.25) % beams.get_width()
    screen.blit(beams, (-boff, 0))
    if beams.get_width() - boff < 800:
        screen.blit(beams, (beams.get_width() - boff, 0))
    screen.blit(art.vignette(), (0, 0))
    for q in g.pops:
        _text(screen, q[2], (int(q[0] * 2 - cam), int(q[1] * 2)), 28, (255, 226, 110), center=True)
    if getattr(g, "dawn", 0) > 0:
        flash = pygame.Surface((800, 480), pygame.SRCALPHA)
        flash.fill((255, 240, 170, int(230 * g.dawn / 0.6)))
        screen.blit(flash, (0, 0))


def heart(screen, x, y, fill):
    """fill: 2 full, 1 half, 0 empty."""
    for col, on in (((60, 40, 56), True), ((236, 70, 96), fill >= 1)):
        if not on:
            continue
        clip = None
        if col != (60, 40, 56) and fill == 1:
            clip = screen.get_clip()
            screen.set_clip(pygame.Rect(x, y, 11, 22))
        pygame.draw.circle(screen, col, (x + 6, y + 7), 6); pygame.draw.circle(screen, col, (x + 16, y + 7), 6)
        pygame.draw.polygon(screen, col, [(x, y + 9), (x + 22, y + 9), (x + 11, y + 21)])
        if clip is not None:
            screen.set_clip(clip)
    pygame.draw.circle(screen, (255, 190, 200), (x + 5, y + 5), 2)


def overlay(g, screen):
    bar = pygame.Surface((800, 58), pygame.SRCALPHA)
    for y in range(58):
        pygame.draw.line(bar, (8, 6, 16, int(170 * (1 - y / 58.0))), (0, y), (800, y))
    screen.blit(bar, (0, 0))
    for p in g.players:
        x0 = 12 if p.slot == 0 else 800 - 12 - 250
        face = art.hd_hunter(p.kind, "stand", 0, False, 1, 1.5)
        screen.blit(face, (x0 - 14, -6), (0, 0, 60, 44))
        _text(screen, p.d["title"] + ("  x%d" % p.lives if not p.out else "  out"), (x0 + 42, 4), 24, (255, 255, 255))
        for i in range(4):
            heart(screen, x0 + 42 + i * 26, 26, max(0, min(2, p.hp - i * 2)))
        note = cards.info(p.card)[1] if p.card else ""
        if p.staples:
            note = (note + "   " if note else "") + "staples %d" % p.staples
        for key, left in p.fx.items():
            note = (note + "   " if note else "") + "%s %d" % (cards.info(key)[1], int(left) + 1)
        if note:
            if p.card:
                screen.blit(art.hd_small("card", size=1.4), (x0 + 150, 20))
            _text(screen, note, (x0 + (178 if p.card else 150), 30), 20, (255, 226, 110), bold=False)
    _text(screen, "%d" % g.score, (400, 6), 34, (255, 255, 255), center=True)
    if len(g.players) == 1 and not g.boss_on and g.stage == 0 and g.cam < 200 and int(g.time) % 6 < 3:
        _text(screen, "Second controller: press a button to join", (400, 452), 22, (255, 255, 255), center=True, bold=False)
    bosses = [b for b in g.beasts if b.boss]
    if bosses:
        total = sum(b.max_hp for b in bosses)
        left = sum(max(0, b.hp) for b in bosses)
        _text(screen, g.level["boss"]["name"], (400, 418), 24, (255, 226, 110), center=True)
        pygame.draw.rect(screen, art.INK, (196, 446, 408, 20), border_radius=6)
        pygame.draw.rect(screen, (70, 20, 34), (200, 450, 400, 12), border_radius=4)
        pygame.draw.rect(screen, (226, 50, 76), (200, 450, int(400 * left / float(total)), 12), border_radius=4)
        pygame.draw.rect(screen, (255, 140, 160), (200, 450, int(400 * left / float(total)), 3))
    if g.banner_t > 0:
        k = min(1.0, g.banner_t / 0.4, (3.0 - g.banner_t) / 0.3 if g.banner_t > 2.6 else 1.0)
        band = pygame.Surface((800, 70), pygame.SRCALPHA)
        band.fill((8, 6, 16, int(170 * k)))
        screen.blit(band, (0, 110))
        _text(screen, g.banner, (400, 124), 52, (255, 226, 110), center=True)
    if g.say_t > 0 and g.say_line:
        hero = next((p for p in g.players if p.kind == g.say_who and not p.out), None)
        if hero is not None:
            f = hud.font(26)
            rows = hud.wrap(g.say_line, f, 300)
            wide = max(f.size(r)[0] for r in rows) + 24
            hx = int((hero.x - g.cam) * 2)
            x = max(8, min(800 - wide - 8, hx - wide // 2))
            y = max(64, int(hero.y * 2) - 150 - 24 * len(rows))
            box = pygame.Rect(x, y, wide, 16 + 24 * len(rows))
            pygame.draw.rect(screen, (255, 255, 255), box, border_radius=10)
            pygame.draw.rect(screen, art.INK, box, 3, border_radius=10)
            tx = max(box.x + 14, min(box.right - 14, hx))
            pygame.draw.polygon(screen, (255, 255, 255), [(tx - 9, box.bottom - 3), (tx + 9, box.bottom - 3), (tx, box.bottom + 14)])
            for i, row in enumerate(rows):
                screen.blit(f.render(row, True, (30, 26, 30)), (x + 12, y + 8 + i * 24))


def dim(screen, alpha=170):
    shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    shade.fill((8, 4, 16, alpha))
    screen.blit(shade, (0, 0))


def title(g, screen):
    wall = art.wall(4)
    off = int(g.time * 24) % wall.get_width()
    screen.blit(wall, (-off, 0))
    screen.blit(wall, (wall.get_width() - off, 0))
    pygame.draw.rect(screen, _shade(art.THEMES[4][3], 0.62), (0, 416, 800, 64)); pygame.draw.rect(screen, art.THEMES[4][3], (0, 416, 800, 22))
    me = art.hd_hunter("lucas", "stand", 0, False, 1, 5.0)
    screen.blit(me, (10, 440 - me.get_height()))
    boss = art.hd_monster("vampire", int(g.time * 2) % 2, 1.7, "chairman", False, -1, 2.6)
    screen.blit(boss, (620, 440 - boss.get_height()))
    screen.blit(art.vignette(), (0, 0))
    _text(screen, "VAMPIRES,", (400, 14), 84, (236, 60, 84), center=True)
    _text(screen, "OH WELL...", (400, 78), 84, (236, 60, 84), center=True)
    for i, line in enumerate(g.help_lines):
        _text(screen, line, (400, 158 + i * 26), 26, (255, 255, 255), center=True, bold=False)
    rows = g.title_options()
    for i, row in enumerate(rows):
        if row == "level":
            label = "Start at: %d. %s" % (g.level_choice + 1, g.levels[g.level_choice])
        elif row == "mode":
            label = "Level: %s" % g.modes[g.mode]
        else:
            label = "Player %s: %s" % ("two" if row == "p2" else "one", art.HUNTERS[g.p2_kind if row == "p2" else g.p1_kind]["title"])
        sel = i == g.option_row
        if sel:
            pygame.draw.rect(screen, (236, 196, 70), (230, 220 + 34 * i, 340, 32), border_radius=8)
        f = hud.font(28, True)
        img = f.render(("<  %s  >" if sel else "%s") % label, True, art.INK if sel else (255, 255, 255))
        screen.blit(img, (400 - img.get_width() // 2, 226 + 34 * i))
    if int(g.time * 2) % 2 == 0:
        _text(screen, "Big button: start", (400, 368), 38, (255, 226, 110), center=True)
    _text(screen, "Triangle: card album (%d of %d)        Best %d" % (bin(g.found).count("1"), len(cards.KEYS), g.best),
          (400, 444), 24, (255, 255, 255), center=True, bold=False)


def album(g, screen):
    i, turn, _ = g.album
    screen.fill((16, 10, 24))
    _text(screen, "Card album", (400, 6), 40, (236, 196, 70), center=True)
    for side, j in ((-1, (i - 1) % len(cards.KEYS)), (1, (i + 1) % len(cards.KEYS))):       # the neighbours, small
        face = cards.front(cards.KEYS[j]) if g.found >> j & 1 else cards.card_back()
        mini = pygame.transform.smoothscale(face, (150, 210))
        mini.set_alpha(110)
        screen.blit(mini, (400 + side * 250 - 75, 130))
    if g.found >> i & 1:
        cards.show(screen, cards.KEYS[i], turn, (400, 236))
    else:
        screen.blit(cards.card_back(), (400 - cards.CW // 2, 236 - cards.CH // 2))
        _text(screen, "Not found yet", (400, 222), 30, (255, 255, 255), center=True)
    _text(screen, "%d of %d" % (i + 1, len(cards.KEYS)), (400, 416), 28, (255, 255, 255), center=True)
    _text(screen, "Left and right: browse     Big button: turn over     Triangle: back", (400, 448), 22, (200, 190, 220), center=True, bold=False)


def draw(g, screen):
    if g.state == "title":
        (album if g.album is not None else title)(g, screen)
        return
    if g.scene is not None:
        g.scene.draw(screen)
        return
    world(g, screen)
    overlay(g, screen)
    if g.cardview is not None:
        v = g.cardview
        dim(screen, 200)
        _text(screen, "%s found a card!" % v["p"].d["title"], (400, 8), 40, (236, 196, 70), center=True)
        rise = min(1.0, v["t"] / 0.35)
        cards.show(screen, v["key"], v["turn"], (400, int(244 + (1 - rise) * 260)))
        if v["turn"] >= 0.99:
            _text(screen, "Big button: back to work", (400, 438), 30, (255, 255, 255), center=True)
    elif g.state == "paused":
        dim(screen)
        _text(screen, "PAUSED", (400, 170), 84, (255, 226, 110), center=True)
        _text(screen, "Small button or plus: carry on     Hold it: quit     Home: games menu", (400, 270), 26, (255, 255, 255), center=True, bold=False)
    elif g.state == "over":
        dim(screen, 190)
        if g.win:
            _text(screen, "THE DAY SHIFT WINS!", (400, 90), 72, (255, 226, 110), center=True)
            _text(screen, "I don't really care about winning, but I still win. Sheesh.", (400, 170), 26, (255, 255, 255), center=True, bold=False)
        else:
            _text(screen, "GAME OVER", (400, 100), 88, (236, 60, 84), center=True)
        _text(screen, "Score %d" % g.last_score, (400, 226), 48, (255, 255, 255), center=True)
        _text(screen, "New best!" if g.new_best else "Best %d" % g.best, (400, 280), 32, (255, 226, 110), center=True)
        _text(screen, "Big button: play again     Home: games menu", (400, 370), 28, (255, 255, 255), center=True, bold=False)
