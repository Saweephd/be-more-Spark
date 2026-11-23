"""The five floors of Brightwell Remedies (an invented company). Each floor is laid out from a fixed
recipe, so it is the same every time, and ends in a boss room."""
import random

FLOOR = 208
STAGES = (
    dict(name="The Loading Dock", length=2200, monsters=("zombie", "bat"), pits=0, count=14,
         boss=dict(kind="zombie", look="watchman", name="The Night Watchman", hp=22, scale=1.8, move="walk", attack="wave")),
    dict(name="The Pill Press Hall", length=2500, monsters=("zombie", "skeleton", "bat"), pits=2, count=17,
         boss=dict(kind="ghost", look="banshee", name="The Receptionist", hp=26, scale=1.9, move="float", attack="scream")),
    dict(name="The Bottling Line", length=2800, monsters=("wolf", "ghost", "zombie"), pits=3, count=19,
         boss=dict(kind="wolf", look="alpha", name="The Alpha", hp=32, scale=1.7, move="leap", attack="leap")),
    dict(name="The Laboratory", length=3000, monsters=("skeleton", "vampire", "bat", "ghost"), pits=4, count=21,
         boss=dict(kind="vampire", look="twin_b", name="The Twins", hp=20, scale=1.25, move="blink", attack="orb", pair=True)),
    dict(name="The Executive Floor", length=3200, monsters=("vampire", "wolf", "skeleton", "ghost", "zombie"), pits=4, count=24,
         boss=dict(kind="vampire", look="chairman", name="The Chairman", hp=54, scale=1.7, move="blink", attack="orb", forms=True)),
)
NAMES = tuple(s["name"] for s in STAGES)
ARENA = 400                                    # the boss room is one screen wide


def build(index):
    """Returns dict: length, ground [(x0, x1)], ledges [(x, y, w)], lamps [(x, y)], chests [(x, y)], spawns [(x, kind)], boss."""
    st = STAGES[index]
    rng = random.Random(900 + index)
    length = st["length"]
    pits = sorted(rng.sample(range(500, length - ARENA - 300, 60), st["pits"])) if st["pits"] else []
    pits = [p for i, p in enumerate(pits) if i == 0 or p - pits[i - 1] > 200]
    ground, x = [], 0
    for p in pits:
        ground.append((x, p))
        x = p + 46
    ground.append((x, length))
    ledges, lamps = [], []
    x = 220
    while x < length - ARENA - 120:
        w = rng.choice((70, 90, 110))
        y = rng.choice((162, 162, 150))
        ledges.append((x, y, w))
        if rng.random() < 0.5:
            ledges.append((x + w + 24, y - 44, 70))
            lamps.append((x + w + 50, y - 44))
        if rng.random() < 0.6:
            lamps.append((x + w // 2, y))
        x += w + rng.randrange(150, 260)
    for p in pits:                                                # a ledge over every pit keeps it fair
        ledges.append((p - 22, 164, 90))
    lamps += [(gx, FLOOR) for gx in range(160, length - ARENA, 330) if not any(p - 20 < gx < p + 60 for p in pits)]
    high = [l for l in ledges if l[1] < 130]
    spots = rng.sample(high, min(2, len(high))) if high else []
    chests = [(l[0] + l[2] // 2, l[1]) for l in spots]
    while len(chests) < 2:
        chests.append((600 + 700 * len(chests), FLOOR))
    spawns = []
    for i in range(st["count"]):
        sx = 360 + i * (length - ARENA - 520) // st["count"] + rng.randrange(-40, 40)
        spawns.append((sx, rng.choice(st["monsters"])))
    return dict(length=length, ground=ground, ledges=ledges, lamps=lamps, chests=chests, spawns=sorted(spawns), boss=st["boss"],
                name=st["name"])
