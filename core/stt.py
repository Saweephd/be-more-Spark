import subprocess
import logging
import os
import re
from .config import WHISPER_CMD, WHISPER_MODEL, STT_REMOTE

logger = logging.getLogger(__name__)

# After a failed attempt the network service is skipped until this time.
REMOTE_RETRY_AFTER_S = 300
_remote_retry_at = 0.0


def clean_transcript(output: str) -> str:
    """Tidy a raw transcript and drop the text Whisper invents from silence."""
    # Remove timestamps like [00:00:00.000 --> 00:00:02.000] or [BLANK_AUDIO]
    output = re.sub(r'\[.*?\]', '', output).strip()

    # Fix capitalization of BMO
    output = re.sub(r'\b[Bb]emo\b', 'BMO', output)
    output = re.sub(r'\b[Bb]eemo\b', 'BMO', output)

    lowered = output.lower()
    hallucinations = [
        "[silence]", "(silence)", "you", "thanks for watching!",
        "[blank_audio]", "thank you.", "thank you", "thanks.",
    ]
    # Whisper often invents sound descriptions from silence or ambient audio,
    # e.g. "(eerie music)".  Reject output that is entirely inside brackets.
    is_parenthetical = bool(re.match(r'^\s*[\(\[].*[\)\]]\s*$', output.strip()))
    if is_parenthetical or lowered in hallucinations or not re.search(r'[a-zA-Z0-9]', lowered):
        logger.info(f"Whisper hallucination filtered: {repr(output)}")
        return ""
    return output


def transcribe_audio(audio_filepath: str) -> str:
    """Transcribe a 16 kHz mono WAV file produced by record_audio().

    Tries the speech to text service on the home network first (STT_REMOTE in
    core/config.py); if that is switched off or unreachable, runs whisper.cpp
    on the Pi as before."""
    if not audio_filepath or not os.path.exists(audio_filepath):
        logger.error(f"Audio file not found: {audio_filepath}")
        return ""

    global _remote_retry_at
    import time
    if STT_REMOTE and time.time() >= _remote_retry_at:
        start = time.time()
        try:
            from .stt_remote import transcribe_wav
            text = transcribe_wav(audio_filepath, STT_REMOTE)
            print(f"[STT] remote ({STT_REMOTE}) {time.time() - start:.2f}s")
            return clean_transcript(text)
        except Exception as e:
            # Do not pay the connection timeout on every request while the
            # service is down: use the Pi's Whisper for a while, then try again.
            _remote_retry_at = time.time() + REMOTE_RETRY_AFTER_S
            print(f"[STT] remote failed after {time.time() - start:.2f}s ({e}); "
                  f"using local Whisper for the next {REMOTE_RETRY_AFTER_S // 60} minutes")

    return transcribe_local(audio_filepath)


def transcribe_local(audio_filepath: str) -> str:
    """Run whisper.cpp on the Pi's own processor."""
    try:
        # Run whisper.cpp directly on the 16 kHz WAV.
        # -nt  no timestamps (we strip them anyway, skip the compute)
        # -t 3 leave one of the Pi 5's four cores free for Piper / Tk so we
        #      don't thermal-throttle when STT and TTS overlap mid-turn
        # -l en force English, skipping the language-detection pass
        cmd = [WHISPER_CMD, "-m", WHISPER_MODEL, "-f", audio_filepath, "-nt", "-t", "3", "-l", "en"]
        logger.info(f"Running whisper.cpp transcription on the CPU... CMD: {' '.join(cmd)}")
        try:
            # stderr=DEVNULL: whisper prints verbose debug/timing info to stderr.
            # We only want the clean transcript from stdout.
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Whisper CPU process failed with exit code {e.returncode}")
            return ""

        return clean_transcript(output)

    except subprocess.CalledProcessError as e:
        logger.error(f"Whisper CPU process failed: {e}")
        return ""
    except Exception as e:
        logger.error(f"Transcription Error: {e}")
        return ""
