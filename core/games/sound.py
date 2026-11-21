"""Chip-style sound effects and music for BMO's games, made in code.

Nothing is loaded from files: every effect and tune is built from square,
triangle and noise waves when the game starts, like an old handheld console.
All the tunes are original to this project.

If the speaker cannot be opened (or BMO_GAME_SOUND=0), every call quietly does
nothing, so the games still run silently and the tests need no audio device.
"""
import math
import os

RATE = 22050
_NOTE = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}


def note_freq(name):
    """'A4' is 440 Hz; sharps as 'F#4', flats as 'Bb3'."""
    letter = name[0].upper()
    rest = name[1:]
    semis = _NOTE[letter]
    while rest and rest[0] in "#b":
        semis += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    octave = int(rest)
    return 440.0 * 2 ** ((semis + (octave - 4) * 12) / 12.0)


# ---------- wave building (numpy) ----------
def _np():
    import numpy
    return numpy


def _env(n, attack=0.004, release=0.04, decay=None):
    np = _np()
    e = np.ones(n, dtype=np.float32)
    a = min(n, int(attack * RATE))
    r = min(n - a, int(release * RATE))
    if a:
        e[:a] = np.linspace(0, 1, a, dtype=np.float32)
    if r:
        e[n - r:] *= np.linspace(1, 0, r, dtype=np.float32)
    if decay:
        e *= np.exp(-np.arange(n, dtype=np.float32) / (decay * RATE))
    return e


def tone(freq, dur, wave="square", duty=0.5, vol=0.5, slide=0.0, decay=None, vibrato=0.0):
    """One note. slide is the frequency at the end (0 for none)."""
    np = _np()
    n = max(1, int(dur * RATE))
    t = np.arange(n, dtype=np.float32) / RATE
    f = np.full(n, freq, dtype=np.float32) if not slide else np.linspace(freq, slide, n, dtype=np.float32)
    if vibrato:
        f = f * (1 + 0.012 * np.sin(2 * math.pi * vibrato * t))
    phase = np.cumsum(f) / RATE
    frac = phase - np.floor(phase)
    if wave == "square":
        w = np.where(frac < duty, 1.0, -1.0).astype(np.float32)
    elif wave == "triangle":
        w = (4 * np.abs(frac - 0.5) - 1).astype(np.float32)
    elif wave == "noise":
        rng = np.random.default_rng(int(freq))
        step = max(1, int(RATE / max(freq, 1)))
        w = np.repeat(rng.uniform(-1, 1, n // step + 1).astype(np.float32), step)[:n]
    else:
        w = np.sin(2 * math.pi * phase).astype(np.float32)
    return w * _env(n, decay=decay) * vol


def chain(*parts):
    np = _np()
    return np.concatenate([p for p in parts if p is not None and len(p)])


def mix(*parts):
    np = _np()
    n = max(len(p) for p in parts)
    out = np.zeros(n, dtype=np.float32)
    for p in parts:
        out[:len(p)] += p
    return out


def rest(dur):
    np = _np()
    return np.zeros(max(1, int(dur * RATE)), dtype=np.float32)


# ---------- effects ----------
def _effects():
    sq, tri, nz = "square", "triangle", "noise"
    return {
        "move":     lambda: tone(660, 0.035, sq, 0.25, 0.25),
        "select":   lambda: chain(tone(660, 0.05, sq, 0.25, 0.3), tone(990, 0.08, sq, 0.25, 0.3)),
        "back":     lambda: chain(tone(520, 0.05, sq, 0.25, 0.25), tone(390, 0.07, sq, 0.25, 0.25)),
        "start":    lambda: chain(*[tone(note_freq(n), 0.07, sq, 0.25, 0.32) for n in ("C5", "E5", "G5", "C6")]),
        "pause":    lambda: chain(tone(880, 0.06, sq, 0.5, 0.25), rest(0.03), tone(660, 0.08, sq, 0.5, 0.25)),
        "jump":     lambda: tone(300, 0.14, sq, 0.25, 0.3, slide=720),
        "land":     lambda: tone(140, 0.05, tri, vol=0.4, slide=90),
        "duck":     lambda: tone(260, 0.07, sq, 0.125, 0.22, slide=170),
        "coin":     lambda: chain(tone(988, 0.05, sq, 0.25, 0.3), tone(1319, 0.14, sq, 0.25, 0.3, decay=0.08)),
        "gem":      lambda: chain(*[tone(note_freq(n), 0.04, sq, 0.25, 0.28) for n in ("E6", "G#6", "B6")]),
        "catch":    lambda: tone(880, 0.08, sq, 0.25, 0.28, slide=1320),
        "combo":    lambda: chain(*[tone(note_freq(n), 0.045, sq, 0.125, 0.28) for n in ("C6", "E6", "G6", "C7")]),
        "heart":    lambda: chain(tone(523, 0.08, tri, vol=0.5), tone(784, 0.16, tri, vol=0.5, decay=0.12)),
        "hurt":     lambda: mix(tone(220, 0.25, sq, 0.5, 0.3, slide=80), tone(900, 0.12, nz, vol=0.18)),
        "dash":     lambda: tone(2500, 0.12, nz, vol=0.22, decay=0.05),
        "swat":     lambda: mix(tone(1800, 0.06, nz, vol=0.28), tone(1200, 0.07, sq, 0.125, 0.15, slide=300)),
        "zap":      lambda: mix(tone(3000, 0.09, nz, vol=0.25, decay=0.04), tone(1600, 0.09, sq, 0.25, 0.2, slide=2400)),
        "splat":    lambda: tone(700, 0.08, nz, vol=0.3, decay=0.03),
        "spray":    lambda: tone(6000, 0.22, nz, vol=0.16, decay=0.15),
        "empty":    lambda: chain(tone(200, 0.05, sq, 0.5, 0.2), rest(0.03), tone(200, 0.05, sq, 0.5, 0.2)),
        "pump":     lambda: tone(150, 0.09, sq, 0.5, 0.22, slide=260),
        "pot":      lambda: mix(tone(400, 0.25, nz, vol=0.3, decay=0.08), tone(160, 0.2, tri, vol=0.4, slide=60)),
        "powerup":  lambda: chain(*[tone(note_freq(n), 0.06, sq, 0.25, 0.28) for n in ("C5", "G5", "C6", "E6", "G6", "C7")]),
        "donut":    lambda: chain(tone(392, 0.07, tri, vol=0.5), tone(523, 0.07, tri, vol=0.5), tone(659, 0.14, tri, vol=0.5)),
        "soda":     lambda: chain(tone(1200, 0.12, nz, vol=0.15), tone(500, 0.2, sq, 0.25, 0.25, slide=1500)),
        "clear":    lambda: chain(*[tone(note_freq(n), 0.09, sq, 0.5, 0.25) for n in ("G5", "C6", "E6", "G6")], tone(1568, 0.25, sq, 0.5, 0.25, decay=0.2)),
        "stairs":   lambda: chain(*[tone(note_freq(n), 0.06, sq, 0.25, 0.25) for n in ("C5", "D5", "E5", "F5", "G5", "A5", "B5", "C6")]),
        "queen":    lambda: chain(tone(110, 0.3, sq, 0.5, 0.35, vibrato=7), tone(98, 0.5, sq, 0.5, 0.35, vibrato=7)),
        "queen_hit": lambda: mix(tone(500, 0.1, sq, 0.5, 0.25, slide=250), tone(2000, 0.08, nz, vol=0.2)),
        "ring":     lambda: chain(*[mix(tone(1400, 0.045, sq, 0.5, 0.18), tone(1750, 0.045, sq, 0.5, 0.12)) for _ in range(6)], rest(0.25),
                                  *[mix(tone(1400, 0.045, sq, 0.5, 0.18), tone(1750, 0.045, sq, 0.5, 0.12)) for _ in range(6)]),
        "siren":    lambda: chain(tone(620, 0.32, sq, 0.5, 0.16, slide=980), tone(980, 0.32, sq, 0.5, 0.16, slide=620),
                                  tone(620, 0.32, sq, 0.5, 0.16, slide=980)),
        "crash":    lambda: mix(tone(900, 0.45, nz, vol=0.4, decay=0.14), tone(120, 0.3, tri, vol=0.5, slide=50),
                                tone(3000, 0.25, nz, vol=0.15, decay=0.06)),
        "horn":     lambda: mix(tone(392, 0.32, sq, 0.5, 0.18), tone(494, 0.32, sq, 0.5, 0.14)),
        "turbo":    lambda: mix(tone(150, 0.5, sq, 0.5, 0.18, slide=600), tone(2500, 0.5, nz, vol=0.12)),
        "skid":     lambda: tone(4200, 0.25, nz, vol=0.16, decay=0.12),
        "scrape":   lambda: tone(2600, 0.12, nz, vol=0.14, decay=0.05),
        "cry":      lambda: chain(tone(620, 0.22, sq, 0.25, 0.22, slide=480, vibrato=11), tone(700, 0.35, sq, 0.25, 0.22, slide=420, vibrato=11)),
        "throw":    lambda: chain(tone(300, 0.08, sq, 0.5, 0.25, slide=180), tone(5000, 0.1, nz, vol=0.12, decay=0.05)),
        "bonk":     lambda: mix(tone(240, 0.1, tri, vol=0.5, slide=120), tone(1800, 0.06, nz, vol=0.2)),
        "shot":     lambda: mix(tone(900, 0.06, sq, 0.25, 0.16, slide=300), tone(3000, 0.04, nz, vol=0.12, decay=0.02)),
        "eshot":    lambda: tone(500, 0.08, sq, 0.5, 0.12, slide=250),
        "tick":     lambda: tone(1300, 0.03, sq, 0.5, 0.14),
        "boom":     lambda: mix(tone(600, 0.5, nz, vol=0.42, decay=0.16), tone(90, 0.45, tri, vol=0.55, slide=35)),
        "drone":    lambda: mix(tone(70, 1.6, sq, 0.5, 0.16, vibrato=4), tone(105, 1.6, sq, 0.5, 0.08)),
        "whoosh":   lambda: tone(2000, 0.5, nz, vol=0.2, decay=0.3),
        # Black Warrior
        "punch":    lambda: mix(tone(180, 0.07, sq, 0.5, 0.3, slide=90), tone(2200, 0.05, nz, vol=0.26, decay=0.03)),
        "kick":     lambda: mix(tone(140, 0.1, sq, 0.5, 0.32, slide=60), tone(1600, 0.07, nz, vol=0.28, decay=0.04)),
        "whiff":    lambda: tone(3500, 0.08, nz, vol=0.12, decay=0.05),
        "thud":     lambda: mix(tone(90, 0.22, tri, vol=0.6, slide=40), tone(600, 0.14, nz, vol=0.25, decay=0.06)),
        "grab":     lambda: tone(220, 0.06, sq, 0.25, 0.22, slide=260),
        "bark":     lambda: chain(mix(tone(520, 0.07, sq, 0.5, 0.3, slide=300), tone(900, 0.05, nz, vol=0.2)), rest(0.06),
                                  mix(tone(560, 0.09, sq, 0.5, 0.32, slide=320), tone(900, 0.06, nz, vol=0.2))),
        "mask":     lambda: chain(tone(1200, 0.05, sq, 0.125, 0.18, slide=2400), tone(2600, 0.12, tri, vol=0.3, decay=0.1)),
        "rift":     lambda: mix(tone(80, 1.2, sq, 0.5, 0.22, slide=160, vibrato=6), tone(4000, 1.0, nz, vol=0.08, decay=0.8)),
        "slash":    lambda: chain(tone(6000, 0.18, nz, vol=0.3, decay=0.08), tone(1800, 0.3, tri, vol=0.4, slide=3600, decay=0.2)),
        "ding":     lambda: chain(tone(1568, 0.12, tri, vol=0.4, decay=0.1), tone(1319, 0.3, tri, vol=0.4, decay=0.25)),
        "special":  lambda: chain(*[tone(note_freq(n), 0.04, sq, 0.25, 0.26) for n in ("E5", "B5", "E6", "G#6", "B6", "E7")]),
        "orders":   lambda: chain(*[tone(note_freq(n), d, sq, 0.5, 0.25) for n, d in (("G4", 0.12), ("C5", 0.12), ("E5", 0.12), ("G5", 0.36))]),
        "over":     lambda: chain(*[tone(note_freq(n), d, sq, 0.5, 0.3) for n, d in (("G4", 0.16), ("E4", 0.16), ("C4", 0.16), ("G3", 0.45))]),
        "win":      lambda: chain(*[tone(note_freq(n), d, sq, 0.5, 0.3) for n, d in
                                    (("C5", 0.1), ("E5", 0.1), ("G5", 0.1), ("C6", 0.2), ("G5", 0.1), ("C6", 0.5))]),
    }


# ---------- music ----------
# Each tune: beats per minute, steps per beat, and parts written as "note:steps" tokens
# ("R" is a rest). Every tune here was written for BMO's games.
TUNES = {
    "menu": (112, 2, {
        "lead": "E5:2 G5:2 C6:2 G5:2 A5:2 G5:2 E5:4 F5:2 A5:2 D6:2 A5:2 G5:6 R:2 "
                "E5:2 G5:2 C6:2 E6:2 D6:2 C6:2 A5:4 G5:2 E5:2 D5:2 F5:2 C5:6 R:2",
        "bass": "C3:4 G3:4 C3:4 G3:4 F3:4 C4:4 G3:4 G2:4 C3:4 G3:4 A2:4 E3:4 F3:4 G3:4 C3:8",
    }),
    "mazee_run": (150, 2, {
        "lead": "G5:1 R:1 G5:1 A5:1 B5:2 D6:2 B5:1 A5:1 G5:2 E5:2 R:2 "
                "C6:1 R:1 C6:1 B5:1 A5:2 F#5:2 G5:4 D5:4 "
                "G5:1 R:1 G5:1 A5:1 B5:2 D6:2 E6:2 D6:2 B5:2 G5:2 "
                "A5:2 B5:1 A5:1 F#5:2 D5:2 G5:6 R:2",
        "bass": "G2:2 D3:2 G2:2 D3:2 E2:2 B2:2 E2:2 B2:2 C3:2 G3:2 D3:2 A3:2 G2:2 D3:2 G2:2 D3:2 "
                "G2:2 D3:2 G2:2 D3:2 C3:2 G3:2 E3:2 B3:2 D3:2 A3:2 D3:2 F#3:2 G2:2 D3:2 G2:4",
        "drum": "K:2 H:2 S:2 H:2 " * 8,
    }),
    "bmo_catch": (128, 2, {
        "lead": "F5:2 A5:2 C6:2 A5:1 G5:1 F5:2 C5:2 R:4 Bb5:2 A5:2 G5:2 E5:2 F5:4 R:4 "
                "A5:2 C6:2 F6:2 E6:1 D6:1 C6:2 A5:2 R:4 G5:2 Bb5:2 A5:2 E5:2 F5:6 R:2",
        "bass": "F2:4 C3:4 F2:4 C3:4 Bb2:4 C3:4 F2:4 F3:4 F2:4 C3:4 D3:4 A2:4 Bb2:4 C3:4 F2:8",
        "drum": "K:4 S:4 " * 8,
    }),
    "angry_poppa": (138, 2, {
        "lead": "A4:2 C5:2 E5:2 A5:2 G5:2 E5:2 D5:2 E5:2 F5:2 E5:2 D5:2 C5:2 B4:4 E4:4 "
                "A4:2 C5:2 E5:2 A5:2 B5:2 C6:2 B5:2 A5:2 G5:2 F5:2 E5:2 D5:2 E5:6 R:2",
        "bass": "A2:2 A3:2 A2:2 A3:2 G2:2 G3:2 G2:2 G3:2 F2:2 F3:2 F2:2 F3:2 E2:2 E3:2 E2:2 E3:2 "
                "A2:2 A3:2 A2:2 A3:2 G2:2 G3:2 G2:2 G3:2 F2:2 F3:2 G2:2 G3:2 A2:2 A3:2 A2:4",
        "drum": "K:2 H:1 H:1 S:2 H:2 " * 8,
    }),
    "queen": (168, 2, {
        "lead": "E5:1 F5:1 E5:1 D#5:1 E5:2 B4:2 C5:2 A4:2 R:4 E5:1 F5:1 E5:1 D#5:1 E5:2 B4:2 D5:2 C5:2 B4:4 "
                "A4:1 B4:1 C5:1 D5:1 E5:2 A5:2 G#5:2 E5:2 R:4 F5:2 E5:2 D5:2 C5:2 B4:2 G#4:2 A4:4",
        "bass": "A2:1 R:1 A2:1 R:1 A2:2 E2:2 " * 4 + "F2:1 R:1 F2:1 R:1 F2:2 C3:2 E2:1 R:1 E2:1 R:1 E2:2 B2:2 " * 2,
        "drum": "K:1 H:1 S:1 H:1 " * 16,
    }),
    # Uncle T's road: synth rock in A minor. Power chords chug on the eighths under a square-wave lead.
    "uncle_t": (152, 2, {
        "lead": "E5:2 A5:2 G5:1 E5:1 D5:2 E5:3 R:1 C5:2 D5:2 F5:2 A5:2 C6:2 A5:2 G5:3 F5:1 E5:2 D5:2 "
                "E5:1 E5:1 A5:2 B5:1 C6:1 B5:2 A5:3 R:1 E5:2 G5:2 F5:2 E5:1 F5:1 A5:2 C6:2 B5:4 G#5:2 E5:2",
        "rbass": ("A2:1 A2:1 A3:1 A2:1 A2:1 G2:1 A2:1 C3:1 " * 2 + "F2:1 F2:1 F3:1 F2:1 F2:1 E2:1 F2:1 A2:1 "
                  "G2:1 G2:1 G3:1 G2:1 G2:1 F2:1 G2:1 B2:1 ") * 1 + "A2:1 A2:1 A3:1 A2:1 A2:1 G2:1 A2:1 C3:1 " * 2
                 + "F2:1 F2:1 F3:1 F2:1 F2:1 E2:1 F2:1 A2:1 E2:1 E2:1 E3:1 E2:1 E2:1 D2:1 E2:1 G#2:1",
        "chord": ("A3+E4:1 R:1 A3+E4:1 A3+E4:1 R:1 A3+E4:1 A3+E4:2 " * 2 + "F3+C4:1 R:1 F3+C4:1 F3+C4:1 R:1 F3+C4:1 F3+C4:2 "
                  "G3+D4:1 R:1 G3+D4:1 G3+D4:1 R:1 G3+D4:1 G3+D4:2 ") + "A3+E4:1 R:1 A3+E4:1 A3+E4:1 R:1 A3+E4:1 A3+E4:2 " * 2
                 + "F3+C4:1 R:1 F3+C4:1 F3+C4:1 R:1 F3+C4:1 F3+C4:2 E3+B3:1 R:1 E3+B3:1 E3+B3:1 R:1 E3+B3:1 E3+B3:2",
        "drum": "K:1 H:1 S:1 H:1 K:1 K:1 S:1 H:1 " * 8,
    }),
    # Scary Babies: a music-box lullaby in E minor, gone a little wrong.
    "scary_babies": (126, 2, {
        "lead": "E5:2 G5:1 F#5:1 E5:2 B4:4 R:2 C5:2 E5:1 D5:1 C5:2 B4:4 R:2 A4:2 C5:1 B4:1 A4:2 G4:2 B4:2 E5:2 "
                "D#5:2 F#5:2 A5:2 G5:4 F#5:2",
        "bass": "E3:2 B3:2 B3:2 E3:2 B3:2 B3:2 A2:2 E3:2 E3:2 E3:2 B3:2 B3:2 A2:2 E3:2 E3:2 E3:2 G3:2 G3:2 "
                "B2:2 F#3:2 F#3:2 E3:2 B3:2 E3:2",
        "drum": "K:2 H:2 H:2 " * 8,
    }),
    # Soldiers vs Spies: a military march in D minor with snare rolls.
    "soldiers": (144, 2, {
        "lead": "D5:2 D5:1 D5:1 F5:2 A5:2 G5:2 F5:1 E5:1 D5:4 A4:2 A4:1 A4:1 C5:2 E5:2 D5:2 C5:1 A4:1 D5:4 "
                "F5:2 F5:1 F5:1 A5:2 D6:2 C6:2 A5:1 G5:1 F5:4 E5:2 F5:1 G5:1 A5:2 C#5:2 D5:6 R:2",
        "rbass": "D2:1 D2:1 D3:1 D2:1 D2:1 D2:1 D3:1 D2:1 " * 2 + "A1:1 A1:1 A2:1 A1:1 A1:1 A1:1 A2:1 A1:1 "
                 "D2:1 D2:1 D3:1 D2:1 D2:1 D2:1 D3:1 D2:1 "
                 "Bb1:1 Bb1:1 Bb2:1 Bb1:1 F2:1 F2:1 F3:1 F2:1 " * 2 + "A1:1 A1:1 A2:1 A1:1 A1:1 A1:1 A2:1 A1:1 "
                 "D2:1 D2:1 D3:1 D2:1 D2:1 D2:1 D3:1 D2:1",
        "drum": "K:1 S:1 S:1 S:1 K:1 S:1 K:1 H:1 " * 8,
    }),
    # Boss fights: faster and darker.
    "soldiers_boss": (168, 2, {
        "lead": "D5:1 D5:1 R:1 D5:1 F5:1 E5:1 D5:1 C5:1 D5:1 D5:1 R:1 D5:1 G5:1 F5:1 E5:1 C#5:1 " * 2,
        "rbass": "D2:1 D3:1 D2:1 D3:1 D2:1 D3:1 C3:1 C#3:1 " * 4,
        "drum": "K:1 H:1 S:1 H:1 K:1 K:1 S:1 S:1 " * 4,
    }),
    # Black Warrior: a funky street groove in E minor, then the boss and the city waking up.
    "black_warrior": (112, 4, {
        "lead": "E5:2 R:1 E5:1 G5:2 A5:2 B5:3 A5:1 G5:2 E5:2 D5:2 E5:2 G5:2 R:2 R:4 "
                "E5:2 R:1 E5:1 G5:2 A5:2 B5:3 D6:1 B5:2 A5:2 G5:2 A5:2 E5:4 R:4",
        "rbass": "E2:2 R:1 E2:1 R:2 E3:1 E2:1 G2:2 R:1 G2:1 A2:2 B2:2 " * 2
                 + "C3:2 R:1 C3:1 R:2 C3:1 B2:1 A2:2 R:1 A2:1 B2:2 D3:2 "
                 "E2:2 R:1 E2:1 R:2 E3:1 E2:1 G2:2 A2:2 B2:2 D3:2",
        "chord": "R:2 E4+G4:1 R:3 E4+G4:1 R:1 R:2 D4+F#4:1 R:3 D4+F#4:1 R:1 " * 4,
        "drum": "K:2 H:2 S:2 H:1 K:1 H:2 K:2 S:2 H:2 " * 4,
    }),
    "bw_boss": (138, 4, {
        "lead": "E5:2 F5:2 E5:2 B4:2 C5:2 B4:2 G4:4 E5:2 F5:2 E5:2 B4:2 D5:2 C5:2 B4:4 " * 2,
        "rbass": "E2:1 E2:1 E3:1 E2:1 F2:1 F2:1 F3:1 F2:1 " * 8,
        "chord": "E3+B3:2 R:2 E3+B3:2 R:2 F3+C4:2 R:2 F3+C4:2 R:2 " * 4,
        "drum": "K:1 H:1 S:1 H:1 K:1 K:1 S:1 H:1 " * 8,
    }),
    "bw_reform": (96, 2, {
        "lead": "G5:2 A5:2 B5:2 D6:2 C6:3 B5:1 A5:4 G5:2 A5:2 B5:2 G5:2 E6:4 D6:4 "
                "C6:2 B5:2 A5:2 G5:2 A5:3 B5:1 G5:4 E5:2 F#5:2 G5:4 R:4",
        "bass": "G2:4 D3:4 C3:4 G3:4 G2:4 D3:4 C3:4 D3:4 C3:4 G2:4 D3:4 A2:4 C3:4 D3:4 G2:8",
        "drum": "K:2 H:2 S:2 H:2 " * 8,
    }),
    # Hot tub lounge: slow and smooth, until the phone rings.
    "hottub": (88, 2, {
        "lead": "E5:3 D5:1 C5:2 A4:2 B4:3 A4:1 G4:4 A4:3 C5:1 E5:2 G5:2 F5:4 E5:4",
        "bass": "A2:4 E3:4 G2:4 D3:4 F2:4 C3:4 E2:4 B2:4",
        "drum": "H:2 H:2 H:2 H:2 " * 4,
    }),
}


def render_tune(name):
    np = _np()
    bpm, per_beat, parts = TUNES[name]
    step = 60.0 / bpm / per_beat
    tracks = []
    for part, notes in parts.items():
        pieces = []
        for tok in notes.split():
            n, steps = tok.split(":")
            dur = step * int(steps)
            if n == "R":
                pieces.append(rest(dur))
            elif part == "drum":
                hit = {"K": tone(90, 0.09, "triangle", vol=0.55, slide=45),
                       "S": tone(1500, 0.08, "noise", vol=0.2, decay=0.04),
                       "H": tone(7000, 0.03, "noise", vol=0.07, decay=0.01)}[n]
                pieces.append(chain(hit[:int(dur * RATE)], rest(max(0.0, dur - len(hit) / RATE))))
            elif part == "chord":
                notes = n.split("+")
                pieces.append(mix(*[tone(note_freq(x), dur * 0.8, "square", 0.5, 0.075, decay=0.14) for x in notes]))
                pieces.append(rest(dur * 0.2))
            elif part == "rbass":
                pieces.append(tone(note_freq(n), dur * 0.85, "square", 0.5, 0.16, decay=0.25))
                pieces.append(rest(dur * 0.15))
            elif part == "bass":
                pieces.append(tone(note_freq(n), dur * 0.9, "triangle", vol=0.42) if dur > 0 else None)
                pieces.append(rest(dur * 0.1))
            else:
                pieces.append(tone(note_freq(n), dur * 0.85, "square", 0.25, 0.17, vibrato=5 if dur > step * 3 else 0))
                pieces.append(rest(dur * 0.15))
        tracks.append(chain(*pieces))
    return mix(*tracks)


# ---------- player ----------
class Silent:
    """Stands in when there is no sound, so games never need to check."""
    enabled = False

    def play(self, name):
        pass

    def music(self, name):
        pass

    def add(self, name, wave):
        """Register a ready-made sound (a numpy wave at RATE) under a name."""
        pass

    def stop_music(self):
        pass

    def pause_music(self):
        pass

    def resume_music(self):
        pass


class Player(Silent):
    enabled = True

    def __init__(self, pygame, volume):
        self.pg = pygame
        self.volume = volume
        self.effects = {}
        self.tunes = {}
        self.makers = _effects()
        self.current = None
        self.channel = pygame.mixer.Channel(0)
        pygame.mixer.set_reserved(1)

    def _sound(self, wave, vol):
        np = _np()
        data = np.clip(wave * 32767 * vol, -32767, 32767).astype(np.int16)
        init = self.pg.mixer.get_init()
        if init and init[2] == 2:                      # the device opened in stereo
            data = np.repeat(data, 2)
        return self.pg.mixer.Sound(buffer=data.tobytes())

    def play(self, name):
        try:
            if name not in self.effects:
                self.effects[name] = self._sound(self.makers[name](), 0.9 * self.volume)
            self.effects[name].play()
        except Exception:
            pass

    def add(self, name, wave):
        try:
            self.effects[name] = self._sound(wave, 1.0 * self.volume)
        except Exception:
            pass

    def music(self, name):
        if not name or name == self.current:
            return
        try:
            if name not in self.tunes:
                self.tunes[name] = self._sound(render_tune(name), 0.55 * self.volume)
            self.channel.play(self.tunes[name], loops=-1, fade_ms=150)
            self.current = name
        except Exception:
            pass

    def stop_music(self):
        self.current = None
        try:
            self.channel.fadeout(250)
        except Exception:
            pass

    def pause_music(self):
        try:
            self.channel.pause()
        except Exception:
            pass

    def resume_music(self):
        try:
            self.channel.unpause()
        except Exception:
            pass


_player = None


def get():
    """The shared player: real sound if the speaker opens, otherwise Silent."""
    global _player
    if _player is not None:
        return _player
    _player = Silent()
    if os.environ.get("BMO_GAME_SOUND", "1") == "0" or os.environ.get("SDL_AUDIODRIVER") == "dummy":
        return _player
    try:
        import pygame
        _np()
        try:
            volume = max(0.0, min(1.0, float(os.environ.get("BMO_VOLUME", "0.8"))))
        except ValueError:
            volume = 0.8
        pygame.mixer.init(frequency=RATE, size=-16, channels=1, buffer=1024)
        pygame.mixer.set_num_channels(12)
        _player = Player(pygame, volume)
    except Exception as e:
        print("[GAME] No sound: %s" % e, flush=True)
        _player = Silent()
    return _player
