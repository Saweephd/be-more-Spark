"""Music Teacher's Pet: play the notes Heather sets, earn check marks, dodge the ruler."""


def make(seed=None, scores_path=None):
    from .game import MusicTeacher
    return MusicTeacher(seed=seed, scores_path=scores_path)
