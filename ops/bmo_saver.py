"""Screen saver pictures for bmo-ctl.sh.

  list                 Count the screen saver pictures
  import <folder>      Copy every picture in a folder (and its sub folders) into
                       screensaver/, shrunk to fit BMO's 800 x 480 screen so the
                       3 second rotation stays smooth. The originals are left alone.
"""
import os
import re
import sys

from PIL import Image, ImageOps

from core import music_library as ml

SIZE = (800, 480)


def shrink(src, dst):
    img = Image.open(src)
    img.draft("RGB", SIZE)                      # fast decode for big JPEGs
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((SIZE[0] * 2, SIZE[1] * 2), Image.Resampling.LANCZOS)
    img = ImageOps.pad(img, SIZE, Image.Resampling.LANCZOS, color="#000000")
    img.save(dst, "JPEG", quality=90)


def cmd_import(folder, target=None):
    target = target or ml.SCREENSAVER_DIR
    os.makedirs(target, exist_ok=True)
    done = skipped = 0
    for path in ml.screensaver_pictures(folder):
        rel = os.path.relpath(path, folder)
        name = re.sub(r"[^a-z0-9]+", "_", os.path.splitext(rel)[0].lower()).strip("_") + ".jpg"
        try:
            shrink(path, os.path.join(target, name))
            done += 1
        except Exception as e:
            print("skipped %s: %s" % (rel, e))
            skipped += 1
    print("%d pictures ready for the screen saver (%d skipped); %d in all" % (
        done, skipped, len(ml.screensaver_pictures(target))))
    return done


def main(argv):
    if len(argv) >= 2 and argv[0] == "import":
        cmd_import(argv[1])
    else:
        print("%d screen saver pictures" % len(ml.screensaver_pictures()))


if __name__ == "__main__":
    main(sys.argv[1:])
