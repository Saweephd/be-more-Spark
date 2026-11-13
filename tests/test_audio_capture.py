"""Tests for core/audio_capture.py.  No microphone or PortAudio needed.

Run: python -m unittest tests.test_audio_capture
"""
import unittest

import numpy as np

from core.audio_capture import (
    BLOCK_FRAMES, BLOCK_MS, Decimator, EndpointDetector, NoiseFloor, block_rms,
)

NOISE = 130.0    # measured room level on BMO's microphone, 12 Nov 2026
SPEECH = 2500.0


def run(detector, levels):
    """Feed levels; return the time in ms at which the detector stopped, or None."""
    for i, level in enumerate(levels):
        if detector.feed(level):
            return (i + 1) * detector.block_ms
    return None


def blocks(ms):
    return int(round(ms / BLOCK_MS))


class EndpointDetectorTests(unittest.TestCase):
    def test_block_is_80_ms(self):
        self.assertAlmostEqual(BLOCK_MS, 80.0)

    def test_pause_between_words_does_not_end_recording(self):
        # The original bug: about 0.17 s of quiet ended the recording.
        d = EndpointDetector(noise_rms=NOISE)
        levels = ([NOISE] * blocks(400) + [SPEECH] * blocks(800) + [NOISE] * blocks(500)
                  + [SPEECH] * blocks(800) + [NOISE] * blocks(1500))
        stopped = run(d, levels)
        self.assertEqual(d.reason, "end_of_speech")
        # Must run past the second phrase: 400 + 800 + 500 + 800 = 2500 ms.
        self.assertGreater(stopped, 2500 + 800)
        self.assertLess(stopped, 2500 + 1100)
        self.assertTrue(d.heard_speech)

    def test_slow_start_is_tolerated(self):
        # The original code gave up after about 0.35 s without speech.
        d = EndpointDetector(noise_rms=NOISE)
        levels = [NOISE] * blocks(3000) + [SPEECH] * blocks(1000) + [NOISE] * blocks(1500)
        run(d, levels)
        self.assertEqual(d.reason, "end_of_speech")
        self.assertTrue(d.heard_speech)

    def test_nobody_speaks(self):
        d = EndpointDetector(noise_rms=NOISE)
        stopped = run(d, [NOISE] * blocks(8000))
        self.assertEqual(d.reason, "no_speech")
        self.assertFalse(d.heard_speech)
        self.assertAlmostEqual(stopped, 5040.0, delta=BLOCK_MS)

    def test_noise_spikes_are_not_speech(self):
        # Single loud blocks (a door, a click) separated by quiet never count,
        # however many there are.  The old counter added them up forever.
        d = EndpointDetector(noise_rms=NOISE)
        levels = ([NOISE] * 5 + [3000.0]) * 20
        run(d, levels)
        self.assertFalse(d.heard_speech)
        self.assertEqual(d.reason, "no_speech")

    def test_short_cough_then_real_speech(self):
        d = EndpointDetector(noise_rms=NOISE)
        levels = ([NOISE] * blocks(400) + [SPEECH] * 2 + [NOISE] * blocks(1200)
                  + [SPEECH] * blocks(1200) + [NOISE] * blocks(1500))
        run(d, levels)
        self.assertEqual(d.reason, "end_of_speech")
        self.assertGreaterEqual(d.speech_ms, 1100)

    def test_wake_word_tail_is_ignored(self):
        # "...MO" lands in the first blocks; the user then pauses before asking.
        d = EndpointDetector(noise_rms=NOISE)
        levels = ([SPEECH] * 3 + [NOISE] * blocks(1500) + [SPEECH] * blocks(1000)
                  + [NOISE] * blocks(1500))
        stopped = run(d, levels)
        self.assertEqual(d.reason, "end_of_speech")
        self.assertGreater(stopped, 240 + 1500 + 1000)

    def test_hard_cap(self):
        d = EndpointDetector(noise_rms=NOISE)
        stopped = run(d, [SPEECH] * blocks(20000))
        self.assertEqual(d.reason, "max_length")
        self.assertAlmostEqual(stopped, 15040.0, delta=BLOCK_MS)

    def test_threshold_follows_a_noisy_room(self):
        quiet = EndpointDetector(noise_rms=100)
        noisy = EndpointDetector(noise_rms=600)
        self.assertEqual(quiet.speech_threshold, 400)      # floor
        self.assertEqual(noisy.speech_threshold, 1800)     # 3 x noise
        self.assertLess(noisy.silence_threshold, noisy.speech_threshold)

    def test_timing_does_not_depend_on_block_length(self):
        # Same audio in 10 ms blocks must give the same decision as 80 ms blocks.
        results = []
        for block_ms in (10.0, 80.0):
            d = EndpointDetector(noise_rms=NOISE, block_ms=block_ms,
                                 start_blocks=max(2, int(160 / block_ms)))
            n = lambda ms: int(ms / block_ms)
            levels = [NOISE] * n(400) + [SPEECH] * n(1200) + [NOISE] * n(2000)
            results.append(run(d, levels))
        self.assertAlmostEqual(results[0], results[1], delta=160)


class DecimatorTests(unittest.TestCase):
    def test_output_length_and_type(self):
        d = Decimator(3)
        out = d.process(np.zeros(BLOCK_FRAMES, dtype=np.int16))
        self.assertEqual(len(out), 1280)
        self.assertEqual(out.dtype, np.int16)

    def test_stream_is_continuous_across_blocks(self):
        t = np.arange(48000) / 48000.0
        tone = (8000 * np.sin(2 * np.pi * 440 * t)).astype(np.int16)
        whole = Decimator(3).process(tone)
        d = Decimator(3)
        pieces = np.concatenate([d.process(tone[i:i + 1000]) for i in range(0, len(tone), 1000)])
        self.assertEqual(len(pieces), len(whole))
        self.assertLessEqual(int(np.max(np.abs(pieces.astype(int) - whole.astype(int)))), 1)

    def test_tone_above_new_nyquist_is_removed(self):
        t = np.arange(48000) / 48000.0
        high = (8000 * np.sin(2 * np.pi * 12000 * t)).astype(np.int16)
        low = (8000 * np.sin(2 * np.pi * 1000 * t)).astype(np.int16)
        self.assertLess(block_rms(Decimator(3).process(high)[200:]), 100)
        self.assertGreater(block_rms(Decimator(3).process(low)[200:]), 5000)

    def test_factor_one_passes_through(self):
        x = np.arange(100, dtype=np.int16)
        np.testing.assert_array_equal(Decimator(1).process(x), x)


class NoiseFloorTests(unittest.TestCase):
    def test_default_until_enough_data(self):
        self.assertEqual(NoiseFloor(default=150).value, 150)

    def test_ignores_brief_loud_sounds(self):
        nf = NoiseFloor()
        for _ in range(40):
            nf.add(120)
        for _ in range(8):
            nf.add(4000)
        self.assertLess(nf.value, 200)

    def test_block_rms(self):
        self.assertEqual(block_rms(np.zeros(10, dtype=np.int16)), 0.0)
        self.assertAlmostEqual(block_rms(np.full(10, 100, dtype=np.int16)), 100.0)
        self.assertEqual(block_rms(np.array([], dtype=np.int16)), 0.0)


if __name__ == "__main__":
    unittest.main()
