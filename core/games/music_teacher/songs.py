"""The four lessons. Each is an arrangement, made for this game, of a piece long in the public domain,
checked against the open scores of the Mutopia Project. Nothing is copied from a recording.

A hand is a list of bars. A bar is a row of notes: "F5:1.5" is F in octave 5 for a beat and a half,
"R:1" a rest, "C4+E4:1" a chord. A note with no length takes the hand's usual step; "T" is a third of a beat.
"""
_SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name):
    n = _SEMI[name[0]]
    rest = name[1:]
    while rest[0] in "#b":
        n += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + n


def freq(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def _dur(tok, step):
    if tok is None:
        return step
    return 1 / 3 if tok == "T" else float(tok)


def parse(bars, step, bar_beats):
    """Bars -> [(beat, [midi, ...], beats)], rests left out. Every bar must fill its length exactly."""
    out, start = [], 0.0
    for i, bar in enumerate(bars):
        at = 0.0
        for tok in bar.split():
            name, _, d = tok.partition(":")
            d = _dur(d or None, step)
            if name != "R":
                out.append((start + at, [midi(x) for x in name.split("+")], d))
            at += d
        if abs(at - bar_beats) > 1e-6:
            raise ValueError("bar %d is %.3f beats, not %s: %s" % (i + 1, at, bar_beats, bar))
        start += bar_beats
    return out


# ---------------------------------------------------------------- 1. Chopin, "Raindrop" Prelude
_R_A = ["F5:.75 Db5:.25 Ab4:2 Bb4:1", "C5:3 Db5:1", "Eb5:.75 F5:.25 Gb5:2 F5:1"]
_RAIN_RH = _R_A + ["F5:1.5 Eb5:.5 Db5:1 Eb5:1"] + _R_A + [
    "F5:1.5 Eb5:.5 Db5:1 C5:.5 Db5:.5",
    "Eb5:1 Eb5:2 F5:1", "Gb5:.5 F5:.5 Eb5:.5 Db5:.5 F5:2",
    "Eb5:.5 Cb5:.5 Bb4:.5 Ab4:.5 Bb4:1 Bb4:.75 Cb5:.25", "Ab4:1 Eb5:1 Db5:1 Fb5:1",
    "Eb5:1 Eb5:2 F5:1", "Gb5:.5 F5:.5 Eb5:.5 Db5:.5 F5:2",
    "R:.5 Db5:.5 C5:.5 Bb4:.5 C5:1 C5:.5 Db5:.5", "Bb4:1 F5:1 Eb5:1 Gb5:1",
    "F5:.5 Db5:.5 C5:.5 Bb4:.5 C5:1 C5:.75 Db5:.25", "Bb4:1 Eb5:1 F5:1 Eb5:1",
    "F5:3 Eb5:1"] + _R_A + ["F5:1.5 Eb5:.5 Db5:2", "Db5:4"]


def _rain_bar(root, drop="Ab3", second=None):
    second = second or root
    d = drop + ":.5"
    return "%s+%s:.5 %s %s %s %s+%s:.5 %s %s %s" % (root, drop, d, d, d, second, drop, d, d, d)


_RAIN_LH = [_rain_bar("Db3"), _rain_bar("Ab2"), _rain_bar("Db3"), _rain_bar("Ab2", second="Db3"),
            _rain_bar("Db3"), _rain_bar("Ab2"), _rain_bar("Db3"), _rain_bar("Ab2", second="Db3"),
            _rain_bar("Ab2"), _rain_bar("Bb2"), _rain_bar("Eb3"), _rain_bar("Ab2"),
            _rain_bar("Ab2"), _rain_bar("Bb2"),
            _rain_bar("F2", "F3"), _rain_bar("Bb2", "F3"), _rain_bar("F2", "F3"), _rain_bar("Bb2", "F3", second="Ab2"),
            _rain_bar("Db3", second="Ab2"), _rain_bar("Db3"), _rain_bar("Ab2"), _rain_bar("Db3"),
            _rain_bar("Ab2", second="Db3"), "Db3+Ab3+F4:4"]

# ---------------------------------------------------------------- 2. Beethoven, Fuer Elise (the beat is an eighth)
_E_RUN = "E5 D#5 E5 B4 D5 C5"
_E_A = [_E_RUN, "A4:1 R C4 E4 A4", "B4:1 R E4 G#4 B4", "C5:1 R E4 E5 D#5",
        _E_RUN, "A4:1 R C4 E4 A4", "B4:1 R E4 C5 B4"]
_ELISE_RH = (["R:2 E5 D#5"] + _E_A + ["A4:2 E5 D#5"] + _E_A + ["A4:1 R B4 C5 D5"] +
             ["E5:1.5 G4 F5 E5", "D5:1.5 F4 E5 D5", "C5:1.5 E4 D5 C5", "B4:1 R E4 E5 R",
              "R E5 E6 R R D#5", "E5 R R D#5 E5 D#5"] + _E_A + ["A4:3"])
_E_AM, _E_E = "A2 E3 A3 R:1.5", "E2 E3 G#3 R:1.5"
_E_LA = ["R:3", _E_AM, _E_E, _E_AM, "R:3", _E_AM, _E_E]
_ELISE_LH = (["R:3"] + _E_LA + [_E_AM] + _E_LA + [_E_AM] +
             ["C3 G3 C4 R:1.5", "G2 G3 B3 R:1.5", "A2 E3 A3 R:1.5", "E2 E3 E4 R:1.5", "R:3", "R:3"] +
             _E_LA + ["A2 E3 A3:2"])

# ---------------------------------------------------------------- 3. Mozart, Rondo alla Turca
_T_UP = "B4 A4 G#4 A4"
_T_A = ["C5:.5 R:.5 D5 C5 B4 C5", "E5:.5 R:.5 F5 E5 D#5 E5", "B5 A5 G#5 A5 B5 A5 G#5 A5", "C6:1 A5:.5 C6:.5",
        "B5:.5 A5:.5 G5:.5 A5:.5", "B5:.5 A5:.5 G5:.5 A5:.5", "B5:.5 A5:.5 G5:.5 F#5:.5"]
_T_B = ["G5:.5 G5:.5 A5 G5 F5 E5", "D5:1 E5:.5 F5:.5", "G5:.5 G5:.5 A5 G5 F5 E5", "D5:1 C5:.5 D5:.5",
        "E5:.5 E5:.5 F5 E5 D5 C5", "B4:1 C5:.5 D5:.5", "E5:.5 E5:.5 F5 E5 D5 C5"]
_TURCA_RH = (["R:1 " + _T_UP] + _T_A + ["E5:1 " + _T_UP] + _T_A + ["E5:1 E5:.5 F5:.5"] + _T_B + ["B4:1 " + _T_UP] +
             _T_A[:3] + ["C6:1 A5:.5 B5:.5", "C6:.5 B5:.5 A5:.5 G#5:.5", "A5:.5 E5:.5 F5:.5 D5:.5",
                         "C5:1 B4:1", "A4:2"])
_T_AM, _T_EM = "A3:.5 C4+E4:.5 C4+E4:.5 C4+E4:.5", "E3:.5 B3+E4:.5 B3+E4:.5 B3+E4:.5"
_T_LA = [_T_AM, _T_AM, _T_AM, _T_AM, _T_EM, _T_EM, "E3:.5 B3+E4:.5 B2:.5 B3+D#4:.5"]
_T_C, _T_G, _T_E = "C3:.5 E3+G3:.5 C3:.5 E3+G3:.5", "G2:.5 D3+G3:.5 G2:.5 D3+G3:.5", "E3:.5 G#3+B3:.5 E3:.5 G#3+B3:.5"
_T_AL = "A2:.5 C3+E3:.5 A2:.5 C3+E3:.5"
_TURCA_LH = (["R:2"] + _T_LA + ["E3:1 R:1"] + _T_LA + ["E3:1 R:1"] +
             [_T_C, _T_G, _T_C, _T_G, _T_AL, _T_E, _T_AL] + ["E3:1 R:1"] +
             [_T_AM, _T_AM, _T_AM, _T_AM, "F3:.5 A3+C4:.5 E3:.5 G#3+B3:.5", "A3:.5 C4+E4:.5 D3:.5 F3+A3:.5",
              "E3:.5 A3+C4:.5 E3:.5 G#3+B3:.5", "A2+E3+A3:2"])

# ---------------------------------------------------------------- 4. Chopin, Fantaisie-Impromptu (opening)
_F_TURN = "G#4 A4 G#4 G4 G#4 C#5 E5 D#5 C#5 D#5 C#5 C5 C#5 E5 G#5"
_FANT_RH = ["R " + _F_TURN, "R " + _F_TURN,
            "R A4 C#5 D#5 F#5 A5 C#6 D#6 B6 A6 G#6 F#6 E6 D#6 F#6 C#6",
            "C6 D#6 A5 G#5 F#5 A5 E5 D#5 F#5 C#5 C5 D#5 A4 G#4 B4 A4",
            "A4 " + _F_TURN, "R G#4 A#4 G#4 G4 G#4 C#5 E5 D#5 C#5 D#5 C#5 C5 C#5 E5 G#5",
            "D#5 E5 D#5 D5 D#5 B5 A#5 G#5 G5 E6 D#6 C#6 B5 A#5 G#5 G5",
            "A#5 G#5 B5 D5 E5 D#5 G#5 A#4 C#5 B4 D#5 G4 A#4 G#4 G4 G#4",
            "C#5:4"]
_F_CM = "C#3 G#3 C#4 E4 C#4 G#3 E3 G#3 C#4 E4 C#4 G#3"
_FANT_LH = [_F_CM, _F_CM, "D#3 A3 C#4 F#4 C#4 A3 F#3 C#4 D#4 A4 D#4 C#4",
            "G#2 D#3 F#3 C4 F#3 D#3 G#2 D#3 F#3 C4 F#3 D#3", _F_CM,
            "C#3 G#3 A#3 E4 A#3 G#3 E3 G#3 A#3 C#4 A#3 G#3",
            "D#3 G#3 B3 D#4 B3 G#3 D#3 A#3 C#4 G4 C#4 A#3",
            "G#2 D#3 G#3 B3 G#3 D#3 G#2 D#3 G#3 B3 G#3 D#3",
            "C#3+G#3+E4:4"]

SONGS = (
    {"key": "raindrop", "title": "\"Raindrop\" Prelude", "by": "Frédéric Chopin", "opus": "Opus 28, Number 15",
     "bpm": 72, "bar": 4, "rh": _RAIN_RH, "lh": _RAIN_LH, "rh_step": 1, "lh_step": .5},
    {"key": "elise", "title": "Für Elise", "by": "Ludwig van Beethoven", "opus": "WoO 59",
     "bpm": 126, "bar": 3, "rh": _ELISE_RH, "lh": _ELISE_LH, "rh_step": .5, "lh_step": .5},
    {"key": "turca", "title": "Rondo alla Turca", "by": "Wolfgang Amadeus Mozart", "opus": "Sonata K. 331",
     "bpm": 104, "bar": 2, "rh": _TURCA_RH, "lh": _TURCA_LH, "rh_step": .25, "lh_step": .5},
    {"key": "fantaisie", "title": "Fantaisie-Impromptu", "by": "Frédéric Chopin", "opus": "Opus 66 (opening)",
     "bpm": 66, "bar": 4, "rh": _FANT_RH, "lh": _FANT_LH, "rh_step": .25, "lh_step": 1 / 3},
)


def hands(song):
    """(right hand, left hand) as [(seconds, [midi], seconds long)]."""
    beat = 60.0 / song["bpm"]
    out = []
    for hand, step in (("rh", song["rh_step"]), ("lh", song["lh_step"])):
        out.append([(b * beat, m, d * beat) for b, m, d in parse(song[hand], step, song["bar"])])
    return out


def length(song):
    return len(song["rh"]) * song["bar"] * 60.0 / song["bpm"]
