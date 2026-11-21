"""Full resolution (800 x 480) portraits and speech for Alien Storm, drawn over the doubled game picture."""
import pygame

from . import art

NAMES = {"alex": "ALEX", "kj": "KJ", "stephen": "STEPHEN", "heather": "HEATHER", "poppa": "ANGRY POPPA"}
_fonts = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        f = pygame.font.Font(None, size)
        f.set_bold(bold)
        _fonts[key] = f
    return _fonts[key]


def wrap(msg, f, width):
    out, cur = [], ""
    for word in msg.split():
        trial = (cur + " " + word).strip()
        if f.size(trial)[0] > width and cur:
            out.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        out.append(cur)
    return out


def label(screen, msg, pos, size=28, color=(255, 255, 255), center=False, bold=False, shadow=True):
    f = font(size, bold)
    im = f.render(msg, True, color)
    x, y = pos
    if center:
        x -= im.get_width() // 2
    if shadow:
        screen.blit(f.render(msg, True, (10, 12, 20)), (x + 2, y + 2))
    screen.blit(im, (x, y))
    return im.get_width()


def bubble(screen, who, mood, line, x, y, right=False, size=96, width=330, shown=None):
    """A portrait with a speech box beside it. shown = how many letters have been typed so far."""
    face = art.portrait(who, mood, size)
    f = font(26 if size > 72 else 22)
    rows = wrap(line, f, width - 24)
    h = max(size, 30 + len(rows) * 24)
    px = x if not right else x + width + 8
    bx = x + size + 8 if not right else x
    box = pygame.Surface((width, h), pygame.SRCALPHA)
    pygame.draw.rect(box, (12, 16, 30, 225), (0, 0, width, h), border_radius=10)
    pygame.draw.rect(box, (240, 240, 240), (0, 0, width, h), 2, border_radius=10)
    screen.blit(box, (bx, y))
    screen.blit(face, (px, y))
    label(screen, NAMES[who], (bx + 12, y + 6), 20, (255, 214, 90), bold=True, shadow=False)
    left = len(line) if shown is None else shown
    for i, row in enumerate(rows):
        part = row[:max(0, left)]
        left -= len(row) + 1
        if part:
            screen.blit(f.render(part, True, (255, 255, 255)), (bx + 12, y + 26 + i * 24))


def talk(screen, talk):
    """In flight chatter: player one's crew bottom left, player two's bottom right."""
    for side, (who, mood, line, left) in talk.items():
        if not line:
            continue
        if side == 0:
            bubble(screen, who, mood, line, 6, 402, size=72, width=290)
        else:
            bubble(screen, who, mood, line, 426, 402, right=True, size=72, width=290)
