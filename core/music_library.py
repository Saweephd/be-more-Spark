"""BMO's song library: every song has a name BMO can be asked for.

Songs are sound files in sounds/music. A song's name comes from its file name
("bacon_pancakes.wav" is "Bacon Pancakes") unless core/music/library.json gives
it a title and other names it may be called. Pictures in slides/ play as a
slideshow while a song plays; pictures in slides/<song file name>/ belong to
that one song. The songs, the names file and the pictures stay on BMO and are
never copied to GitHub.

Everything here is plain logic so it can be tested without BMO's hardware."""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = os.path.join(ROOT, "sounds", "music")
SLIDES_DIR = os.path.join(ROOT, "slides")
SCREENSAVER_DIR = os.path.join(ROOT, "screensaver")
NAMES_FILE = os.path.join(ROOT, "core", "music", "library.json")
PICTURE_TYPES = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")

# Words that carry no meaning when matching a spoken request to a song name.
_FILLER = {"the", "a", "an", "song", "music", "tune", "theme", "track", "please", "bmo", "by", "from", "of", "to", "me", "for", "us", "some"}
_PLAY = r"\b(play\w*|sing|put on|start|hear|listen to)\b"      # play\w*: speech to text often hears "playback", "playing"
_STOP = (r"\b(stop|pause|end|quit|kill|turn off|shut off|cut)( the| that| this| your)? ?(music|song|singing|playing|tune|jam|jamming)\b|"
         r"\b(music|song) off\b|\bno more (music|songs)\b")
_LIST = (r"\b(what|which) (songs|music|tunes)\b|\b(list|name)( me)?( the| your| all)*( of)?( the| your)? (songs|tunes|music)\b|"
         r"\bwhat can you (play|sing)\b|\bwhat do you (play|sing)\b")


def _norm(text):
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower().replace("'", "")).strip()


def _words(text):
    return [w for w in _norm(text).split() if w not in _FILLER]


def _title_from_file(name):
    stem = os.path.splitext(name)[0]
    return re.sub(r"[_\-]+", " ", stem).strip().title().replace("Bmo", "BMO")


def _load_names(names_file):
    try:
        with open(names_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def tracks(music_dir=None, names_file=None):
    """Every song on the device: a list of {"file", "path", "title", "aliases"}."""
    music_dir = music_dir or MUSIC_DIR
    names = _load_names(names_file or NAMES_FILE)
    found = []
    try:
        files = sorted(os.listdir(music_dir))
    except OSError:
        files = []
    for name in files:
        if not name.lower().endswith(".wav"):
            continue
        entry = names.get(name) or names.get(os.path.splitext(name)[0]) or {}
        if isinstance(entry, str):
            entry = {"title": entry}
        found.append({
            "file": name,
            "path": os.path.join(music_dir, name),
            "title": entry.get("title") or _title_from_file(name),
            "aliases": [a for a in entry.get("aliases", []) if isinstance(a, str)],
        })
    return found


def _sounds_like(word, said):
    """A near miss from speech to text ("pancake" for "pancakes", "adventur" for "adventure")."""
    import difflib
    return len(word) >= 5 and any(difflib.SequenceMatcher(None, word, w).ratio() >= 0.82 for w in said)


def match_track(text, library=None):
    """The song a spoken request names, or None. "Play some music" names no song."""
    t = _norm(text)
    if not t or not re.search(_PLAY, t):
        return None
    library = tracks() if library is None else library
    said = set(_words(t))
    best, best_score = None, 0
    for track in library:
        for name in [track["title"]] + track["aliases"]:
            want = _words(name)
            if not want:
                continue
            if _norm(name) in t:
                score = 100 + len(want)
            else:
                hits = sum(1 for w in want if w in said or _sounds_like(w, said))
                # Every word for short names; one miss allowed in names of three or more words.
                need = len(want) if len(want) < 3 else len(want) - 1
                score = hits if hits >= need else 0
            if score > best_score:
                best, best_score = track, score
    return best


def match_stop(text):
    return bool(re.search(_STOP, _norm(text)))


def match_list(text):
    return bool(re.search(_LIST, _norm(text)))


def spoken_list(library=None, limit=8):
    library = tracks() if library is None else library
    if not library:
        return "BMO has no songs yet."
    titles = [t["title"] for t in library]
    if len(titles) == 1:
        return "BMO knows one song: %s." % titles[0]
    shown = titles[:limit]
    more = len(titles) - len(shown)
    line = "BMO knows %d songs: %s" % (len(titles), ", ".join(shown[:-1]))
    line += (", %s, and %d more." % (shown[-1], more)) if more else (", and %s." % shown[-1])
    return line + " Ask BMO to play one by name."


def screensaver_pictures(folder=None):
    """Every picture in the screen saver folder, including sub folders, in name order."""
    folder = folder or SCREENSAVER_DIR
    found = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        found += [os.path.join(root, f) for f in files if f.lower().endswith(PICTURE_TYPES) and not f.startswith(".")]
    return sorted(found)


def slides_for(track=None, slides_dir=None):
    """Pictures to show while a song plays: the song's own folder first, else the shared ones."""
    slides_dir = slides_dir or SLIDES_DIR

    def pictures(folder):
        try:
            return sorted(os.path.join(folder, f) for f in os.listdir(folder)
                          if f.lower().endswith(PICTURE_TYPES) and not f.startswith("."))
        except OSError:
            return []

    if track:
        own = pictures(os.path.join(slides_dir, os.path.splitext(track["file"])[0]))
        if own:
            return own
    return pictures(slides_dir)
