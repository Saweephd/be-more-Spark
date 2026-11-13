"""Speak text through Piper and the speaker, to test audio out.

Usage: bmo_say.py "text"
"""
import sys
import time

from core.tts import play_audio_on_hardware

text = " ".join(sys.argv[1:]).strip()
if not text:
    print('usage: bmo_say.py "text"')
    sys.exit(2)
start = time.time()
play_audio_on_hardware(text)
print(f"spoke {len(text)} characters in {time.time() - start:.1f}s")
