"""Record from the microphone for a few seconds and report what BMO hears.

Prints the background level, the speech threshold that follows from it, and
what the end-of-speech detector would have decided.  With --transcribe it also
runs Whisper on the recording and reports how long that took.

Usage: bmo_listen.py <seconds> [--transcribe]
"""
import sys
import time

import numpy as np

from core import config
from core.audio_capture import BLOCK_MS, EndpointDetector, MicStream, block_rms


def main(argv):
    seconds = int(argv[0]) if argv else 5
    transcribe = "--transcribe" in argv
    quiet_start = config.MIC_DEVICE_INDEX  # resolves the device (prints its own line)

    mic = MicStream(quiet_start, samplerate=config.MIC_SAMPLE_RATE)
    mic.start()
    blocks = []
    deadline = time.time() + seconds
    while time.time() < deadline:
        block = mic.read(timeout=1.0)
        if block is not None:
            blocks.append(block)
    mic.close()
    if not blocks:
        print("no audio received from the microphone")
        return 1

    levels = np.array([block_rms(b) for b in blocks])
    floor = float(np.percentile(levels, 20))
    print(f"blocks={len(blocks)} block_ms={BLOCK_MS:.0f} overflows={mic.overflows}")
    print(f"level rms: floor(p20)={floor:.0f} median={np.median(levels):.0f} "
          f"p95={np.percentile(levels, 95):.0f} max={levels.max():.0f}")

    detector = EndpointDetector(noise_rms=floor, max_ms=seconds * 1000.0 + BLOCK_MS)
    stopped_at = None
    for i, level in enumerate(levels):
        if detector.feed(float(level)):
            stopped_at = (i + 1) * BLOCK_MS / 1000.0
            break
    print(f"detector: {detector.summary()}")
    if stopped_at is not None:
        print(f"detector would have stopped at {stopped_at:.1f}s; heard_speech={detector.heard_speech}")
    else:
        print(f"detector still listening after {seconds}s; heard_speech={detector.heard_speech}")

    if transcribe:
        import scipy.io.wavfile
        import scipy.signal
        from core.stt import transcribe_audio
        data = np.concatenate(blocks).astype(np.float32)
        ratio = config.MIC_SAMPLE_RATE // 16000
        if ratio >= 2:
            data = scipy.signal.resample_poly(data, 1, ratio)
        wav = "/tmp/bmo-listen.wav"
        scipy.io.wavfile.write(wav, 16000, np.clip(data, -32768, 32767).astype(np.int16))
        start = time.time()
        text = transcribe_audio(wav)
        print(f"transcript: {text!r}")
        print(f"speech to text took {time.time() - start:.2f}s for {len(blocks) * BLOCK_MS / 1000:.1f}s of audio")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
