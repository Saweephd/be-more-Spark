"""Measure Alien Storm's frame time on this machine: python3 ops/alien_storm_bench.py
Runs flight on each stage with the boss, and each cutscene, drawing every frame the way the game loop does."""
import os
import sys
import tempfile
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("BMO_GAME_SOUND", "0")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame  # noqa: E402

from core.games import common  # noqa: E402
from core.games.alien_storm import game as G, scenes  # noqa: E402


def report(name, times):
    times.sort()
    avg = sum(times) / len(times)
    p99 = times[int(len(times) * 0.99)]
    print("%-22s avg %5.1f ms   99%% %5.1f ms   worst %5.1f ms   (%.0f fps headroom)" % (name, avg * 1000, p99 * 1000, times[-1] * 1000, 1 / p99))


def main():
    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode((800, 480))
    canvas = pygame.Surface((400, 240))
    for stage in range(4):
        g = G.AlienStorm(seed=4, scores_path=os.path.join(tempfile.mkdtemp(), "s.json"))
        g.scenes = False
        g.unlocked, g.level_choice = 4, stage
        inp = common.Input()
        inp.pressed = {"a"}
        g.step(1 / 60, inp)
        g.t = 30.0
        g.waves = [w for w in g.waves if w[0] > 30]
        times = []
        for f in range(60 * 30):
            inp.pressed = set()
            inp.held = {"a"} if f % 90 < 50 else set()
            inp.held.add("left" if (f // 70) % 2 else "right")
            for j in g.jets:
                j.safe = 9
            if f == 60 * 12:
                g.waves, g.t = [], G.STAGE_LEN + 1
            a = time.perf_counter()
            g.step(1 / 60, inp)
            g.render(canvas)
            pygame.transform.scale(canvas, (800, 480), screen)
            g.render_hd(screen)
            times.append(time.perf_counter() - a)
        report("stage %d flight+boss" % (stage + 1), times)
    g.scenes = False
    for name, make in (("takeoff", lambda: scenes.takeoff(g, True)), ("battle 1", lambda: scenes.set_piece(g, 0)),
                       ("battle 2", lambda: scenes.set_piece(g, 1)), ("battle 3", lambda: scenes.set_piece(g, 2)),
                       ("battle 4", lambda: scenes.set_piece(g, 3)), ("ending", lambda: scenes.ending(g))):
        sc = make()
        times = []
        for i, shot in enumerate(sc.shots):
            sc.i, t = i, 0.0
            while t < shot["dur"]:
                sc.t = t
                a = time.perf_counter()
                sc.draw(screen)
                times.append(time.perf_counter() - a)
                t += 1 / 20
        report("scene " + name, times)


if __name__ == "__main__":
    main()
