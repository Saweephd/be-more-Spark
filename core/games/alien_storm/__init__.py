"""Alien Storm: Tom Cat Alley. A vertical scrolling shooter for BMO. All art, sound and music are original."""


def make(seed=None, scores_path=None):
    from .game import AlienStorm
    return AlienStorm(seed=seed, scores_path=scores_path)


if __name__ == "__main__":
    import sys
    from ..common import main
    sys.exit(main(make))
