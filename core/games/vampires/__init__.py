"""Vampires, Oh Well...: Lucas the daywalker goes to work and finds the night shift never left."""


def make(seed=None, scores_path=None):
    from .game import Vampires
    return Vampires(seed=seed, scores_path=scores_path)
