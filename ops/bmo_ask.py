"""Send one text question down the same path a spoken question takes after
transcription (edge skills first, then the model on the Spark) and report the
route, the time to the first sentence, and the total time.

Uses a throwaway history file, so tests never touch BMO's real chat memory.

Usage: bmo_ask.py [--expect edge|spark] "question"
"""
import contextlib
import io
import os
import sys
import tempfile
import time


def main(argv):
    expect = None
    if len(argv) >= 2 and argv[0] == "--expect":
        expect, argv = argv[1], argv[2:]
    question = " ".join(argv).strip()
    if not question:
        print('usage: bmo_ask.py [--expect edge|spark] "question"')
        return 2

    quiet = io.StringIO()
    with contextlib.redirect_stdout(quiet):
        import core.llm as llm
        llm.MEMORY_FILE = os.path.join(tempfile.mkdtemp(prefix="bmo-ask-"), "memory.json")
        brain = llm.Brain()
        start = time.time()
        first = None
        parts = []
        for chunk in brain.stream_think(question):
            if first is None:
                first = time.time() - start
            parts.append(chunk)
        total = time.time() - start

    route = "edge" if "Edge skill handled" in quiet.getvalue() else "spark"
    reply = " ".join(p.strip() for p in parts)
    print(f"reply: {reply}")
    print(f"route={route} first_sentence={first if first is not None else total:.2f}s total={total:.2f}s")
    failed = any(m in reply for m in ("Could not connect to my brain", "having trouble"))
    if failed:
        return 1
    if expect and route != expect:
        print(f"expected route {expect}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
