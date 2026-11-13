"""Compare speech to text on the network service and on the Pi, for one WAV.

Usage: bmo_stt.py [file.wav]     (default: the last recorded request, input.wav)
"""
import os
import sys
import time

from core import config
from core.stt import clean_transcript, transcribe_local
from core.stt_remote import transcribe_wav

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "input.wav")
if not os.path.exists(path):
    print(f"no such file: {path}")
    sys.exit(1)

rc = 0
if config.STT_REMOTE:
    for attempt in (1, 2):
        start = time.time()
        try:
            text = clean_transcript(transcribe_wav(path, config.STT_REMOTE))
            print(f"remote {config.STT_REMOTE} run {attempt}: {time.time() - start:.2f}s  {text!r}")
        except Exception as e:
            print(f"remote {config.STT_REMOTE} run {attempt}: FAILED after {time.time() - start:.2f}s ({e})")
            rc = 1
else:
    print("remote: switched off (STT_REMOTE is empty)")
start = time.time()
text = transcribe_local(path)
print(f"local whisper.cpp: {time.time() - start:.2f}s  {text!r}")
sys.exit(rc)
