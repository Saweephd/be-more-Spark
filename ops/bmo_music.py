"""Song library helper for bmo-ctl.sh.

  list                 Show every song BMO can be asked for, and the picture count
  import <folder>      Copy songs and pictures from a folder into BMO.
                       Sound files become plain WAV files in sounds/music (ffmpeg does
                       the conversion); pictures go to slides/. A sub folder named
                       after a song keeps its pictures for that song only.
"""
import os
import re
import shutil
import subprocess
import sys

from core import music_library as ml

SOUND_TYPES = (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma")


def safe_name(name):
    stem = os.path.splitext(os.path.basename(name))[0].lower()
    return re.sub(r"[^a-z0-9]+", "_", stem).strip("_") or "song"


def cmd_list():
    library = ml.tracks()
    for t in library:
        own = ml.slides_for(t)
        names = (" (also: %s)" % ", ".join(t["aliases"])) if t["aliases"] else ""
        print("%-28s %s%s  [%d pictures]" % (t["file"], t["title"], names, len(own)))
    print("%d songs, %d shared pictures" % (len(library), len(ml.slides_for(None))))
    return 0


def cmd_import(folder):
    if not os.path.isdir(folder):
        print("import: no such folder: %s" % folder)
        return 2
    os.makedirs(ml.MUSIC_DIR, exist_ok=True)
    os.makedirs(ml.SLIDES_DIR, exist_ok=True)
    songs = pictures = failed = 0
    for base, _dirs, files in os.walk(folder):
        rel = os.path.relpath(base, folder)
        for name in sorted(files):
            src = os.path.join(base, name)
            low = name.lower()
            if low.endswith(SOUND_TYPES):
                dst = os.path.join(ml.MUSIC_DIR, safe_name(name) + ".wav")
                done = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vn",
                                       "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", dst])
                if done.returncode == 0:
                    songs += 1
                    print("song     %s -> %s" % (name, os.path.basename(dst)))
                else:
                    failed += 1
                    print("FAILED   %s" % name)
            elif low.endswith(ml.PICTURE_TYPES):
                sub = "" if rel == "." else safe_name(rel.split(os.sep)[0])
                target = os.path.join(ml.SLIDES_DIR, sub)
                os.makedirs(target, exist_ok=True)
                shutil.copy2(src, os.path.join(target, name))
                pictures += 1
    print("imported %d songs and %d pictures, %d failed" % (songs, pictures, failed))
    return 1 if failed else 0


def main(argv):
    if len(argv) >= 1 and argv[0] == "list":
        return cmd_list()
    if len(argv) >= 2 and argv[0] == "import":
        return cmd_import(argv[1])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
