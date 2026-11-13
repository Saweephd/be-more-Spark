"""Microphone capture helpers for BMO.

Three pieces, kept free of GUI code so they can be unit tested:

* ``Decimator``        48 kHz -> 16 kHz down-sampler that keeps its filter state
                       between blocks, so a continuous stream stays continuous.
* ``EndpointDetector`` decides when the user has started and finished speaking.
                       Everything is measured in milliseconds, never in
                       "chunks", so it does not depend on how often the sound
                       card calls back.
* ``MicStream``        one long-lived input stream with fixed-size blocks.  The
                       wake word loop and the recorder read from the same
                       stream, so no audio is lost between "Hey BMO" and the
                       question that follows.

Changelog
  1.0.0  2026-11-12  First version (pack 1: recording reliability).
"""

from __future__ import annotations

import collections
import threading
import time

import numpy as np
import scipy.signal

CAPTURE_RATE = 48000
TARGET_RATE = 16000
# 3840 samples at 48 kHz = 80 ms = 1280 samples at 16 kHz, which is exactly the
# frame size openWakeWord expects.
BLOCK_FRAMES = 3840
BLOCK_MS = BLOCK_FRAMES * 1000.0 / CAPTURE_RATE


def block_rms(block: np.ndarray) -> float:
    """Root-mean-square level of an int16 block, in int16 units (0..32768)."""
    if block is None or block.size == 0:
        return 0.0
    x = block.astype(np.float64)
    return float(np.sqrt(np.mean(x * x)))


class Decimator:
    """Stateful integer-factor down-sampler (low-pass FIR, then keep every Nth)."""

    def __init__(self, factor: int = CAPTURE_RATE // TARGET_RATE, taps: int = 63):
        self.factor = int(factor)
        if self.factor < 1:
            raise ValueError("factor must be >= 1")
        if self.factor == 1:
            self._fir = None
            self._zi = None
        else:
            # Cut off a little below the new Nyquist frequency.
            self._fir = scipy.signal.firwin(taps, 0.9 / self.factor)
            self._zi = np.zeros(taps - 1, dtype=np.float64)
        self._phase = 0  # index of the next sample to keep, carried across blocks

    def process(self, block: np.ndarray) -> np.ndarray:
        flat = np.asarray(block).reshape(-1)
        if self._fir is None:
            return flat.astype(np.int16)
        filtered, self._zi = scipy.signal.lfilter(
            self._fir, [1.0], flat.astype(np.float64), zi=self._zi
        )
        out = filtered[self._phase::self.factor]
        consumed = len(filtered) - self._phase
        self._phase = (-consumed) % self.factor
        return np.clip(out, -32768, 32767).astype(np.int16)

    def reset(self) -> None:
        if self._zi is not None:
            self._zi[:] = 0.0
        self._phase = 0


class NoiseFloor:
    """Rolling estimate of the room's background level.

    Uses a low percentile of recent block levels, so somebody talking near BMO
    just before the wake word does not inflate the estimate much."""

    def __init__(self, window_blocks: int = 60, percentile: float = 20.0, default: float = 150.0):
        self._levels = collections.deque(maxlen=window_blocks)
        self._percentile = percentile
        self._default = default

    def add(self, rms: float) -> None:
        self._levels.append(float(rms))

    @property
    def value(self) -> float:
        if len(self._levels) < 5:
            return self._default
        return float(np.percentile(np.fromiter(self._levels, dtype=np.float64), self._percentile))


class EndpointDetector:
    """Decide when a spoken request has ended.

    Feed it the level of each block with :meth:`feed`.  It returns ``True``
    once recording should stop.  ``reason`` then says why:

    ``end_of_speech``  the user spoke, then stayed quiet for ``end_silence_ms``
    ``no_speech``      nobody spoke within ``start_timeout_ms``
    ``max_length``     the hard cap was reached
    """

    def __init__(
        self,
        noise_rms: float = 150.0,
        block_ms: float = BLOCK_MS,
        speech_factor: float = 3.0,
        min_speech_rms: float = 400.0,
        silence_ratio: float = 0.6,
        start_blocks: int = 2,
        min_speech_ms: float = 250.0,
        end_silence_ms: float = 900.0,
        start_timeout_ms: float = 5000.0,
        max_ms: float = 15000.0,
        grace_ms: float = 240.0,
    ):
        self.block_ms = float(block_ms)
        self.noise_rms = float(noise_rms)
        # A block counts as speech when it is clearly above the room noise.
        self.speech_threshold = max(self.noise_rms * speech_factor, min_speech_rms)
        # ...and as silence only when it falls well back below that (hysteresis).
        self.silence_threshold = self.speech_threshold * silence_ratio
        self.start_blocks = int(start_blocks)
        self.min_speech_ms = float(min_speech_ms)
        self.end_silence_ms = float(end_silence_ms)
        self.start_timeout_ms = float(start_timeout_ms)
        self.max_ms = float(max_ms)
        # The tail of the wake word ("...MO") lands in the first blocks; ignore
        # it when deciding whether the user has started their question.
        self.grace_ms = float(grace_ms)

        self.elapsed_ms = 0.0
        self.speech_ms = 0.0          # total time judged to be speech
        self.silence_run_ms = 0.0     # current run of quiet since speech began
        self.quiet_since_ms = 0.0     # time since the last speech (or since start)
        self._loud_run = 0
        self.speaking = False
        self.heard_speech = False     # True once enough real speech was heard
        self.reason = None
        self.peak_rms = 0.0

    def feed(self, rms: float) -> bool:
        self.elapsed_ms += self.block_ms
        self.peak_rms = max(self.peak_rms, rms)
        in_grace = self.elapsed_ms <= self.grace_ms

        if rms >= self.speech_threshold and not in_grace:
            self._loud_run += 1
            if self.speaking or self._loud_run >= self.start_blocks:
                if not self.speaking:
                    self.speaking = True
                    # The blocks that confirmed the start were speech too.
                    self.speech_ms += self.block_ms * (self._loud_run - 1)
                self.speech_ms += self.block_ms
                self.silence_run_ms = 0.0
                self.quiet_since_ms = 0.0
                if self.speech_ms >= self.min_speech_ms:
                    self.heard_speech = True
        else:
            self._loud_run = 0
            self.quiet_since_ms += self.block_ms
            if self.speaking and rms < self.silence_threshold:
                self.silence_run_ms += self.block_ms
                if self.silence_run_ms >= self.end_silence_ms:
                    if self.heard_speech:
                        self.reason = "end_of_speech"
                        return True
                    # Only a click or a cough so far: keep waiting for real speech.
                    self.speaking = False
                    self.speech_ms = 0.0
                    self.silence_run_ms = 0.0

        if not self.heard_speech and self.quiet_since_ms >= self.start_timeout_ms:
            self.reason = "no_speech"
            return True
        if self.elapsed_ms >= self.max_ms:
            self.reason = "max_length"
            return True
        return False

    def summary(self) -> str:
        return (
            f"reason={self.reason} length={self.elapsed_ms / 1000:.1f}s "
            f"speech={self.speech_ms / 1000:.1f}s noise={self.noise_rms:.0f} "
            f"threshold={self.speech_threshold:.0f} peak={self.peak_rms:.0f}"
        )


class MicStream:
    """One long-lived microphone stream delivering fixed-size int16 blocks."""

    def __init__(self, device, samplerate: int = CAPTURE_RATE, block_frames: int = BLOCK_FRAMES,
                 max_queued_blocks: int = 50):
        self.device = device
        self.samplerate = samplerate
        self.block_frames = block_frames
        self._queue = collections.deque(maxlen=max_queued_blocks)
        self._cond = threading.Condition()
        self._stream = None
        self.last_block_at = 0.0
        self.overflows = 0

    def _callback(self, indata, frames, time_info, status):
        if status and getattr(status, "input_overflow", False):
            self.overflows += 1
        block = indata[:, 0].copy()
        with self._cond:
            self._queue.append(block)
            self.last_block_at = time.time()
            self._cond.notify()

    def start(self) -> None:
        if self._stream is not None:
            return
        import sounddevice as sd  # imported here so the pure classes test without PortAudio
        self._stream = sd.InputStream(
            samplerate=self.samplerate, device=self.device, channels=1, dtype="int16",
            blocksize=self.block_frames, callback=self._callback,
        )
        self._stream.start()
        self.last_block_at = time.time()

    def read(self, timeout: float = 1.0):
        """Return the next block, or ``None`` if none arrived within ``timeout``."""
        with self._cond:
            if not self._queue:
                self._cond.wait(timeout)
            if self._queue:
                return self._queue.popleft()
        return None

    def flush(self) -> None:
        with self._cond:
            self._queue.clear()

    def close(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        self.flush()

    @property
    def running(self) -> bool:
        return self._stream is not None
