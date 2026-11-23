"""Music Teacher's Pet.

Heather is the music teacher. She sets a piece; its notes slide down the lanes toward the piano and you
press the button for each lane as its note reaches the line. A right note sounds and earns a check mark
on the blackboard. A wrong or missed note brings her ruler down on the desk. Play all four lessons and
finish one without a single mistake to be named Teacher's Pet.

Lanes, left to right: D-pad left, down, up, right, then the big circle and the triangle on the harder levels.
"""
import pygame

from .. import common as c
from .. import sound as snd
from ..alien_storm import hud
from ..common import H, W, Game, text
from . import art, songs

BUTTONS = ("left", "down", "up", "right", "a", "b")
LANE_COLORS = ((236, 96, 96), (244, 170, 70), (240, 220, 90), (110, 200, 120), (100, 170, 240), (190, 130, 230))
# mode: lanes, shortest gap between notes you must play (seconds), time a note is in view, good window, perfect window
MODES = ((4, 0.42, 2.3, 0.20, 0.09), (5, 0.23, 1.9, 0.15, 0.07), (6, 0.0, 1.6, 0.12, 0.06))
GRADES = ((100, "Teacher's Pet"), (95, "A+"), (90, "A"), (80, "B"), (70, "C"), (60, "D"), (0, "See me after class"))
PASS_MARK = 60
BOARD = pygame.Rect(8, 6, 264, 72)
LANE_TOP, HIT_Y, KEYS_Y = 84, 196, 206
LANE_CX, TOP_W, BOT_W = 140, 110, 252
CHECK_COLS, CHECK_ROWS = 16, 3

INTRO = ("Sit up straight. We begin with Chopin: listen for the raindrops.",
         "Beethoven next. Light fingers, and count in three.",
         "Mozart's Turkish march. Crisp, like little drums.",
         "Last lesson. Chopin again, and this one runs. Deep breath.")
PRAISE = ("Lovely phrasing.", "Now that is what practice sounds like.", "Beautiful. Keep that touch.",
          "Miles and Felix should hear this.", "I may put this on a live reel.", "You have been practicing!")
SCOLD = ("Count it! One, two, three, four.", "Eyes on the music, please.", "Again, and this time with feeling.",
         "Did you practice at all this week?", "That was not in the score.", "Gently. It is a piano, not a drum.")
REPORT = {"Teacher's Pet": "Not one wrong note. You are officially Teacher's Pet.",
          "A+": "Nearly perfect. One more clean run and the title is yours.",
          "A": "Excellent work. I am impressed.", "B": "Good. A little more practice at home.",
          "C": "It will do. Slow down and count.", "D": "We pass, barely. Practice, practice, practice.",
          "See me after class": "Oh dear. We will take that one again."}


def grade_for(percent):
    for floor, name in GRADES:
        if percent >= floor:
            return name
    return GRADES[-1][1]


def chart(right_hand, lanes, gap):
    """Choose which melody notes the player must press, and a lane for each.
    Returns (notes to press, notes the game plays itself). A note: dict t, midi, lane."""
    melody = [(t, max(m)) for t, m, _ in right_hand]
    keep, auto, last = [], [], None
    for t, m in melody:
        if last is None or t - last >= gap - 1e-6:
            keep.append([t, m])
            last = t
        else:
            auto.append({"t": t, "midi": m})
    out, prev = [], None
    for i, (t, m) in enumerate(keep):
        near = [k[1] for k in keep[max(0, i - 4):i + 5]]
        lo, hi = min(near), max(near)
        lane = (lanes - 1) // 2 if hi == lo else int(round((m - lo) / float(hi - lo) * (lanes - 1)))
        if prev is not None and m != prev["midi"] and lane == prev["lane"]:      # a new pitch should feel like a move
            step = 1 if m > prev["midi"] else -1
            if 0 <= lane + step < lanes:
                lane += step
        elif prev is not None and m == prev["midi"]:
            lane = prev["lane"]
        note = {"t": t, "midi": m, "lane": lane, "state": None}
        out.append(note)
        prev = note
    return out, auto


class MusicTeacher(Game):
    name = "music_teacher"
    title = "Music Teacher's Pet"
    title_color = (250, 244, 220)
    music = None                                    # the lesson is the music
    levels = tuple(s["title"] for s in songs.SONGS)
    modes = ("Practice", "Recital", "Conservatory")
    help_lines = ("Press each lane's button as its note reaches the line",)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.loaded = set()
        self.shake = 0.0
        self.pose, self.pose_t = "calm", 0.0
        self.say_line, self.say_t = "", 0.0
        self.phase = "title"
        self.lesson = 0
        self.checks, self.boards = [], 0
        self.notes, self.auto, self.backing = [], [], []
        self.lanes = 4
        self.pops = []

    # ------------------------------------------------------------ set-up
    def reset(self):
        self.score = 0
        self.win = False
        self.pets = 0
        self.start_lesson(self.level_choice)

    def start_lesson(self, index):
        self.lesson = index
        self.reach_level(index)
        song = songs.SONGS[index]
        self.lanes, gap, self.travel, self.good, self.perfect = MODES[self.mode]
        rh, lh = songs.hands(song)
        self.notes, self.auto = chart(rh, self.lanes, gap)
        self.backing = [{"t": t, "midi": m} for t, m, _ in lh]
        self.beat = 60.0 / song["bpm"]
        self.end_t = songs.length(song) + 1.5
        self.clock = -max(2.6, 4 * self.beat) - 0.01
        self.ticks = 0
        self.ai = self.bi = 0
        self.hits = self.perfects = self.misses = self.slips = 0
        self.combo = self.best_combo = 0
        self.checks, self.boards = [], 0
        self.lesson_score = int(self.score)
        self.pops = []
        self.lit = [0.0] * 6
        self.phase = "intro"
        self.phase_t = 0.0
        self.set_pose("calm", 0)
        self.say(INTRO[index], 6.0)
        self.load_sounds(set(n["midi"] for n in self.notes + self.auto), set(m for b in self.backing for m in b["midi"]))

    def load_sounds(self, melody, backing):
        if not getattr(self.sound, "enabled", False):
            return
        for m in melody:
            if ("r", m) not in self.loaded:
                self.sound.add("mtp_r%d" % m, snd.piano(songs.freq(m), 1.0, 0.62))
                self.loaded.add(("r", m))
        for m in backing:
            if ("l", m) not in self.loaded:
                self.sound.add("mtp_l%d" % m, snd.piano(songs.freq(m), 0.9, 0.3))
                self.loaded.add(("l", m))
        if "fx" not in self.loaded:
            self.sound.add("mtp_crack", snd.mix(snd.tone(900, 0.07, "noise", vol=0.75, decay=0.02),
                                                 snd.tone(170, 0.12, "square", vol=0.3, slide=70, decay=0.04)))
            self.sound.add("mtp_tick", snd.tone(1500, 0.03, "square", vol=0.3, decay=0.01))
            self.sound.add("mtp_chalk", snd.tone(4200, 0.05, "noise", vol=0.12, decay=0.03))
            self.loaded.add("fx")

    # ------------------------------------------------------------ small helpers
    def set_pose(self, pose, seconds):
        self.pose, self.pose_t = pose, seconds

    def say(self, line, seconds=3.0):
        self.say_line, self.say_t = line, seconds

    def lane_x(self, lane, y):
        """Centre of a lane at height y: the lanes spread as they come toward the player."""
        k = (y - LANE_TOP) / float(HIT_Y - LANE_TOP)
        width = TOP_W + (BOT_W - TOP_W) * k
        return LANE_CX + ((lane + 0.5) / self.lanes - 0.5) * width

    def percent(self):
        total = len(self.notes) + self.slips
        return int(100.0 * self.hits / total) if total else 0

    def add_check(self, perfect):
        self.checks.append(perfect)
        if len(self.checks) > CHECK_COLS * CHECK_ROWS:
            self.checks = [perfect]
            self.boards += 1

    def wrong(self, lane=None):
        self.combo = 0
        self.shake = 0.3
        self.set_pose("strike", 0.4)
        self.sfx("mtp_crack")
        if self.rng.random() < 0.45:
            self.say(self.rng.choice(SCOLD), 2.4)
        if lane is not None:
            self.pops.append([self.lane_x(lane, HIT_Y), HIT_Y - 12.0, "X", 0.5, c.RED])

    def right(self, note, off):
        perfect = abs(off) <= self.perfect
        self.hits += 1
        self.perfects += 1 if perfect else 0
        self.combo += 1
        self.best_combo = max(self.best_combo, self.combo)
        self.score += (100 if perfect else 60) * (1 + min(4, self.combo // 10))
        self.add_check(perfect)
        self.sfx("mtp_r%d" % note["midi"])
        self.lit[note["lane"]] = 0.18
        if self.pose not in ("strike",) or self.pose_t <= 0:
            self.set_pose("write", 0.22)
        self.pops.append([self.lane_x(note["lane"], HIT_Y), HIT_Y - 14.0, "Perfect" if perfect else "Good", 0.5,
                          c.YELLOW if perfect else c.WHITE])
        if self.combo in (10, 25, 50, 80, 120):
            self.set_pose("delighted", 1.4)
            self.say(self.rng.choice(PRAISE), 2.6)

    def pressed_lanes(self, inp):
        out = []
        touch = inp.touch is not None and "a" in inp.pressed
        if touch and inp.touch[0] < 280:
            width = float(BOT_W)
            lane = int((inp.touch[0] - (LANE_CX - width / 2)) / width * self.lanes)
            out.append(max(0, min(self.lanes - 1, lane)))
        for i, name in enumerate(BUTTONS[:self.lanes]):
            if name in inp.pressed and not (name == "a" and touch):
                out.append(i)
        return out

    # ------------------------------------------------------------ update
    def update(self, dt, inp):
        self.shake = max(0.0, self.shake - dt)
        self.say_t = max(0.0, self.say_t - dt)
        self.lit = [max(0.0, v - dt) for v in self.lit]
        if self.pose_t > 0:
            self.pose_t -= dt
            if self.pose_t <= 0:
                self.set_pose("stern", 0.9) if self.pose == "strike" else self.set_pose("calm", 0)
        for p in self.pops:
            p[1] -= 26 * dt
            p[3] -= dt
        self.pops = [p for p in self.pops if p[3] > 0]
        self.phase_t += dt
        if self.phase == "intro":
            if "a" in inp.pressed and self.phase_t > 0.4:
                self.phase = "song"
                self.say("", 0)
            return
        if self.phase == "report":
            if "a" in inp.pressed and self.phase_t > 1.0:
                self.after_report()
            return
        self.clock += dt
        t = self.clock
        if t < 0:                                                  # the count-in
            due = 4 - int(-t / self.beat) - 1
            if due >= self.ticks and due >= 0:
                self.ticks = due + 1
                self.sfx("mtp_tick")
        while self.bi < len(self.backing) and self.backing[self.bi]["t"] <= t:
            for m in self.backing[self.bi]["midi"]:
                self.sfx("mtp_l%d" % m)
            self.bi += 1
        while self.ai < len(self.auto) and self.auto[self.ai]["t"] <= t:
            self.sfx("mtp_r%d" % self.auto[self.ai]["midi"])
            self.ai += 1
        for lane in self.pressed_lanes(inp):
            best = None
            for n in self.notes:
                if n["state"] is None and n["lane"] == lane and abs(n["t"] - t) <= self.good:
                    if best is None or abs(n["t"] - t) < abs(best["t"] - t):
                        best = n
                if n["t"] - t > self.good:
                    break
            if best is not None:
                best["state"] = "hit"
                self.right(best, best["t"] - t)
            else:
                self.slips += 1
                self.wrong(lane)
        for n in self.notes:
            if n["state"] is None and t - n["t"] > self.good:
                n["state"] = "miss"
                self.misses += 1
                self.wrong(n["lane"])
            if n["t"] > t:
                break
        if t >= self.end_t:
            self.finish_lesson()

    def finish_lesson(self):
        self.phase, self.phase_t = "report", 0.0
        self.grade = grade_for(self.percent())
        if self.grade == "Teacher's Pet":
            self.pets += 1
            self.score += 5000
        self.passed = self.percent() >= PASS_MARK or self.mode == 0
        self.set_pose("delighted" if self.percent() >= 90 else ("pleased" if self.passed else "stern"), 0)
        self.pose_t = 0
        self.say(REPORT[self.grade], 60)
        self.sfx("win" if self.passed else "over")

    def after_report(self):
        if not self.passed:
            self.score = self.lesson_score
            self.start_lesson(self.lesson)
        elif self.lesson + 1 < len(songs.SONGS):
            self.start_lesson(self.lesson + 1)
        else:
            self.win = True
            self.say("", 0)
            self.game_over()

    # ------------------------------------------------------------ drawing (the small canvas)
    def draw_room(self, surf, ox=0):
        surf.fill((222, 206, 172))
        pygame.draw.rect(surf, (204, 186, 150), (0, 78, W, 6))
        pygame.draw.rect(surf, (120, 86, 60), (0, KEYS_Y - 4, W, H - KEYS_Y + 4))
        b = BOARD.move(ox, 0)
        pygame.draw.rect(surf, (128, 86, 46), b.inflate(8, 8), border_radius=3)
        pygame.draw.rect(surf, (36, 78, 60), b)
        pygame.draw.rect(surf, (48, 96, 74), (b.x + 2, b.y + 2, b.w - 4, 3))
        pygame.draw.rect(surf, (150, 104, 60), (b.x - 4, b.bottom + 2, b.w + 8, 4))
        pygame.draw.rect(surf, (250, 250, 250), (b.x + 20, b.bottom, 10, 3))
        pygame.draw.rect(surf, (90, 90, 100), (b.right - 40, b.bottom - 1, 16, 4))

    def draw_lanes(self, surf, ox):
        top_l, top_r = LANE_CX - TOP_W / 2 + ox, LANE_CX + TOP_W / 2 + ox
        bot_l, bot_r = LANE_CX - BOT_W / 2 + ox, LANE_CX + BOT_W / 2 + ox
        pygame.draw.polygon(surf, (40, 36, 52), [(top_l, LANE_TOP), (top_r, LANE_TOP), (bot_r, KEYS_Y), (bot_l, KEYS_Y)])
        for i in range(self.lanes + 1):
            k = i / float(self.lanes)
            pygame.draw.line(surf, (86, 80, 106), (top_l + (top_r - top_l) * k, LANE_TOP), (bot_l + (bot_r - bot_l) * k, KEYS_Y))
        for i in range(self.lanes):
            x = self.lane_x(i, HIT_Y) + ox
            wide = BOT_W / self.lanes
            col = LANE_COLORS[i]
            if self.lit[i] > 0:
                glow = pygame.Surface((int(wide) - 2, 14), pygame.SRCALPHA)
                glow.fill(col + (150,))
                surf.blit(glow, (int(x - wide / 2) + 1, HIT_Y - 7))
            pygame.draw.ellipse(surf, col, (int(x) - 11, HIT_Y - 5, 22, 10), 2)
        pygame.draw.line(surf, (250, 250, 250), (self.lane_x(0, HIT_Y) - BOT_W / self.lanes / 2 + ox, HIT_Y),
                         (self.lane_x(self.lanes - 1, HIT_Y) + BOT_W / self.lanes / 2 + ox, HIT_Y))

    def draw_keys(self, surf, ox):
        left = int(LANE_CX - BOT_W / 2) + ox
        pygame.draw.rect(surf, (30, 26, 30), (left - 4, KEYS_Y, BOT_W + 8, H - KEYS_Y))
        n = self.lanes * 3
        kw = BOT_W / float(n)
        for i in range(n):
            lane = i // 3
            col = (250, 248, 240)
            if self.lit[lane] > 0:
                col = tuple(int((a + b) / 2) for a, b in zip(col, LANE_COLORS[lane]))
            pygame.draw.rect(surf, col, (int(left + i * kw) + 1, KEYS_Y + 2, int(kw) - 1, H - KEYS_Y - 3))
        for i in range(n - 1):
            if i % 3 != 2:
                pygame.draw.rect(surf, (24, 22, 28), (int(left + (i + 1) * kw) - 3, KEYS_Y + 2, 6, 17))
        for lane in range(self.lanes):                              # which button plays this lane
            x, y = int(self.lane_x(lane, HIT_Y)) + ox, H - 9
            col = tuple(int(v * 0.6) for v in LANE_COLORS[lane])
            name = BUTTONS[lane]
            if name == "left":
                pygame.draw.polygon(surf, col, [(x - 5, y), (x + 3, y - 5), (x + 3, y + 5)])
            elif name == "right":
                pygame.draw.polygon(surf, col, [(x + 5, y), (x - 3, y - 5), (x - 3, y + 5)])
            elif name == "up":
                pygame.draw.polygon(surf, col, [(x, y - 5), (x - 5, y + 3), (x + 5, y + 3)])
            elif name == "down":
                pygame.draw.polygon(surf, col, [(x, y + 5), (x - 5, y - 3), (x + 5, y - 3)])
            elif name == "a":
                pygame.draw.circle(surf, col, (x, y), 5)
            else:
                pygame.draw.polygon(surf, col, [(x, y - 5), (x - 5, y + 4), (x + 5, y + 4)], 2)

    def draw_notes(self, surf, ox):
        t = self.clock
        for n in self.notes:
            ahead = n["t"] - t
            if ahead > self.travel:
                break
            if n["state"] == "hit" or ahead < -0.25:
                continue
            k = 1.0 - ahead / self.travel
            y = LANE_TOP + (HIT_Y - LANE_TOP) * k
            x = self.lane_x(n["lane"], min(y, KEYS_Y)) + ox
            r = 3.0 + 5.0 * min(1.0, k)
            col = LANE_COLORS[n["lane"]] if n["state"] is None else (110, 100, 110)
            pygame.draw.line(surf, col, (x + r - 1, y), (x + r - 1, y - r * 2.6), 2)        # the stem
            pygame.draw.ellipse(surf, c.INK, (x - r - 1, y - r * 0.7 - 1, r * 2 + 2, r * 1.4 + 2))
            pygame.draw.ellipse(surf, col, (x - r, y - r * 0.7, r * 2, r * 1.4))

    def draw_board(self, surf, ox):
        song = songs.SONGS[self.lesson]
        b = BOARD.move(ox, 0)
        text(surf, "Lesson %d: %s" % (self.lesson + 1, song["title"]), (b.x + 8, b.y + 6), 18, (250, 246, 226), shadow=False)
        text(surf, song["by"], (b.x + 8, b.y + 20), 14, (190, 214, 196), shadow=False)
        for i, perfect in enumerate(self.checks):
            col = (255, 232, 120) if perfect else (240, 240, 240)
            surf.blit(art.check(col), (b.x + 8 + (i % CHECK_COLS) * 15, b.y + 33 + (i // CHECK_COLS) * 12))
        if self.boards:
            text(surf, "+%d boards" % self.boards, (b.right - 62, b.y + 20), 14, (255, 232, 120), shadow=False)

    def draw(self, surf):
        ox = int(self.rng.choice((-2, 2)) * (self.shake / 0.3)) if self.shake > 0 and self.state == "play" else 0
        self.draw_room(surf, ox)
        if self.phase == "title":
            return
        self.draw_board(surf, ox)
        self.draw_lanes(surf, ox)
        self.draw_notes(surf, ox)
        self.draw_keys(surf, ox)
        for p in self.pops:
            text(surf, p[2], (int(p[0]) + ox, int(p[1])), 16, p[4], center=True)
        if self.phase == "song" and self.clock < 0:
            n = min(4, int(-self.clock / self.beat) + 1)
            text(surf, str(n), (LANE_CX, 120), 60, c.YELLOW, center=True)
        if self.phase == "intro":
            self.panel(surf, ("Lesson %d" % (self.lesson + 1), songs.SONGS[self.lesson]["title"],
                              songs.SONGS[self.lesson]["by"] + ", " + songs.SONGS[self.lesson]["opus"],
                              "%s: %d lanes, %d notes to play" % (self.modes[self.mode], self.lanes, len(self.notes)),
                              "Big button: begin"))
        elif self.phase == "report":
            rows = ["Grade: %s" % self.grade, "%d%% right" % self.percent(),
                    "Perfect %d   Good %d" % (self.perfects, self.hits - self.perfects),
                    "Missed %d   Wrong keys %d   Best run %d" % (self.misses, self.slips, self.best_combo)]
            if not self.passed:
                rows.append("Big button: take the lesson again")
            elif self.lesson + 1 < len(songs.SONGS):
                rows.append("Big button: next lesson")
            else:
                rows.append("Big button: school is out")
            self.panel(surf, rows)

    def panel(self, surf, rows):
        box = pygame.Surface((252, 108), pygame.SRCALPHA)
        box.fill((20, 18, 34, 225))
        surf.blit(box, (14, 88))
        pygame.draw.rect(surf, (250, 246, 226), (14, 88, 252, 108), 1)
        for i, row in enumerate(rows):
            big = i == 0 or (i == 1 and self.phase == "intro")
            col = c.YELLOW if i == 0 or i == len(rows) - 1 else c.WHITE
            text(surf, row, (LANE_CX, 94 + i * 20), 22 if big else 16, col, center=True)

    def render(self, surf):
        if self.state != "title":
            return super().render(surf)
        self.phase = "title"
        self.draw_room(surf)
        b = BOARD
        text(surf, "Music Teacher's Pet", (b.centerx, b.y + 12), 34, (250, 246, 226), center=True, shadow=False)
        text(surf, "four lessons with Miss Heather", (b.centerx, b.y + 44), 16, (190, 214, 196), center=True, shadow=False)
        for i in range(7):
            surf.blit(art.check((255, 232, 120)), (b.x + 70 + i * 18, b.y + 58))
        text(surf, "Press each lane's button as its", (140, 96), 18, c.INK, center=True, shadow=False)
        text(surf, "note reaches the white line.", (140, 110), 18, c.INK, center=True, shadow=False)
        text(surf, "Right: a check mark.  Wrong: the ruler!", (140, 126), 16, (120, 40, 40), center=True, shadow=False)
        rows = self.title_options()
        for i, row in enumerate(rows):
            if row == "level":
                label = "Start at: %d. %s" % (self.level_choice + 1, self.levels[self.level_choice])
            else:
                label = "Level: %s" % self.modes[self.mode]
            text(surf, "<  %s  >" % label, (140, 144 + 17 * i), 18, (160, 60, 30) if i == self.option_row else c.INK,
                 center=True, shadow=False)
        if int(self.time * 2) % 2 == 0:
            text(surf, "Press the big button", (140, 184), 20, (160, 60, 30), center=True, shadow=False)
        text(surf, "Best %d" % self.best, (140, 218), 18, c.WHITE, center=True)

    # ------------------------------------------------------------ drawing (full resolution, over the top)
    def render_hd(self, screen):
        if self.state == "over":
            return
        ox = int(self.rng.choice((-4, 4)) * (self.shake / 0.3)) if self.shake > 0 and self.state == "play" else 0
        pose = self.pose if self.state != "title" else ("pleased" if int(self.time / 2.5) % 2 == 0 else "calm")
        screen.blit(art.props(), (560 + ox, 332))
        screen.blit(art.heather(pose), (566 + ox, 136))
        screen.blit(art.desk(), (560 + ox, 388))
        if pose == "strike":
            hud.label(screen, "CRACK!", (600 + ox, 348), 44, (255, 236, 120), bold=True)
        if self.state == "title":
            return
        hud.label(screen, "Score %d" % self.score, (572, 12), 30, (40, 34, 30), shadow=False)
        if self.phase == "song":
            hud.label(screen, "%d/%d" % (self.hits, len(self.notes)), (716, 14), 26, (40, 34, 30), shadow=False)
            if self.combo >= 5:
                hud.label(screen, "%d in a row" % self.combo, (572, 40), 26, (150, 60, 30), shadow=False)
        if self.say_t > 0 and self.say_line:
            f = hud.font(24)
            rows = hud.wrap(self.say_line, f, 204)
            h = 16 + 22 * len(rows)
            y = max(66, 150 - h)
            box = pygame.Rect(566, y, 226, h)
            pygame.draw.rect(screen, (255, 255, 255), box, border_radius=10)
            pygame.draw.rect(screen, (40, 34, 30), box, 2, border_radius=10)
            pygame.draw.polygon(screen, (255, 255, 255), [(660, box.bottom - 2), (684, box.bottom - 2), (676, box.bottom + 12)])
            for i, row in enumerate(rows):
                screen.blit(f.render(row, True, (30, 26, 30)), (box.x + 11, box.y + 8 + i * 22))
