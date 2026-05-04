# BMO Build — Patches & Configuration Notes

**Build:** Stan Waddell, May 2026
**Hardware:** Raspberry Pi 5 (16GB) + Hailo-10H AI HAT 2+ + Pi Camera v2 + FREENOVE 5" LCD + Adafruit USB mic + Adafruit USB speaker
**Software base:** [moorew/be-more-hailo](https://github.com/moorew/be-more-hailo) (fork of brenpoly/be-more-agent)

This document records every fix applied to the moorew fork during initial setup. If the SD card is ever reflashed, re-apply these patches in order.

## 1. Web UI: TemplateResponse API mismatch

**Symptom:** `http://<pi>:8080/` returns 500 Internal Server Error. Server log shows:
```
TypeError: unhashable type: 'dict'
File ".../web_app.py", line 85, in read_root
    return templates.TemplateResponse("index.html", {"request": request})
```

**Cause:** Newer Starlette versions changed the `TemplateResponse` signature. The fork was written against the old API.

**Fix:**
```bash
cd ~/be-more-agent
sed -i 's|TemplateResponse("index.html", {"request": request})|TemplateResponse(request, "index.html")|' web_app.py
```

## 2. VLM warmup leaking NPU file descriptors

**Symptom:** When `agent_hailo.py` runs alongside the `bmo-ollama` systemd service, the LLM call returns `500 Internal Server Error: Failed to create VDevice` or `RemoteDisconnected` after the first prompt or two. The LLM service crashes and restarts repeatedly.

**Cause:** The agent calls `_warmup_vlm()` at startup, which tries to claim `/dev/hailo0` for the vision model. This fails (because hailo-ollama owns the NPU), but the failed `VDevice()` handles aren't cleanly garbage collected. Two file descriptors stay open against `/dev/hailo0`, blocking hailo-ollama from acquiring the device for inference.

**Fix:** Disable the VLM warmup in `agent_hailo.py`:
```bash
cd ~/be-more-agent
sed -i 's|threading.Thread(target=_warmup_vlm, daemon=True).start()|# DISABLED: warmup leaks /dev/hailo0 FDs and blocks hailo-ollama. # threading.Thread(target=_warmup_vlm, daemon=True).start()|' agent_hailo.py
```

**Side effect:** Vision/photo features (`Hey BMO, take a photo`) won't work while bmo-ollama is running. BMO gracefully says "I tried to look but my eyes aren't working" instead of crashing.

## 3. Wake word threshold too sensitive (default never triggers reliably)

**Symptom:** Saying "Hey BMO" rarely or never wakes the agent. Tap-to-wake works fine, but the wake word listener seems dead.

**Cause:** Default threshold of `0.35` is set by the original developer's voice/mic/room. Real-world detection scores typically range 0.20–0.50; many valid wake words score below 0.35.

**Fix:** Lower the threshold to 0.25 in `core/config.py`:
```bash
cd ~/be-more-agent
sed -i 's/WAKE_WORD_THRESHOLD = 0.35/WAKE_WORD_THRESHOLD = 0.25/' core/config.py
```

If false wakes become a problem (random TV noise triggers BMO), bump back up to 0.30.

## 4. The big one: speak() skips audio pipeline when Piper is pre-warm

**Symptom:** BMO appears to work end-to-end — wake word fires, whisper transcribes, the LLM responds, the log shows `[TTS] Final: '<reply text>'` — but no audio is ever heard from the USB speaker.

**Cause:** This is a real bug in the fork's gapless-TTS implementation:

- The agent pre-warms Piper during STT to hide model-load latency (`_warmup_piper`).
- When `speak()` is called, it checks if Piper is alive:
  ```python
  if self._piper_proc is None or self._piper_proc.poll() is not None:
      self._start_tts_turn()
  ```
- If Piper IS alive (warm), the condition is false and `_start_tts_turn()` is **skipped entirely**.
- But `_start_tts_turn()` is the function that spawns aplay AND starts the reader thread that pumps Piper's stdout into aplay's stdin.
- Result: text is written into Piper, Piper produces audio bytes — but nothing is reading them. They sit in Piper's stdout buffer forever. No audio reaches the speaker.

**Fix:** The condition needs to also check whether aplay is running, not just Piper:
```bash
cd ~/be-more-agent
sed -i 's|if self._piper_proc is None or self._piper_proc.poll() is not None:|if self._piper_proc is None or self._piper_proc.poll() is not None or self._tts_aplay is None:|' agent_hailo.py
```

This makes `_start_tts_turn()` run any time aplay isn't already wired up — which forces the reader thread + aplay spawn even when Piper is warm.

## 5. aplay subprocess interrupted by Tkinter signals

**Symptom:** Audio plays but is choppy. Log shows:
```
aplay: pcm_write:2178: write error: Interrupted system call
```

**Cause:** Tkinter and Python's threading internals deliver signals to the agent process, which propagate to the aplay subprocess and interrupt its `write()` syscalls (EINTR).

**Fix:** Spawn aplay in its own session group so it's isolated from parent signals:
```bash
cd ~/be-more-agent
sed -i 's|self._tts_aplay = subprocess.Popen(aplay_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)|self._tts_aplay = subprocess.Popen(aplay_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)|' agent_hailo.py
```

## 6. Last word of TTS clipped by short drain timeout

**Symptom:** Audio plays cleanly, but the final word of every BMO response gets cut off mid-syllable.

**Cause:** `_end_tts_turn(drain=True)` closes aplay's stdin and then waits up to 2 seconds for aplay to drain its hardware buffer. With a 500ms–1000ms ALSA buffer plus system load, 2 seconds isn't always enough. After the timeout, aplay gets `terminate()`d and any audio still in the buffer is lost.

**Fix:** Bump the drain timeout from 2 to 10 seconds:
```bash
cd ~/be-more-agent
sed -i 's|self._tts_aplay.wait(timeout=2.0)|self._tts_aplay.wait(timeout=10.0)|' agent_hailo.py
```

This only affects the end-of-turn drain, where waiting for real audio to finish is exactly the right behavior.

## Configuration Choices

### Service management

`setup_services.sh` installs both `bmo-ollama` and `bmo-web` as auto-starting systemd services. The on-device agent (`./start_agent.sh`) is launched manually.

**Important:** Running the on-device agent and `bmo-web` simultaneously causes intermittent ALSA contention over the USB speaker. Recommended: keep `bmo-ollama` running (it's the LLM brain), but **disable `bmo-web`**:

```bash
sudo systemctl stop bmo-web
sudo systemctl disable bmo-web
```

### Hardware confirmed

| Component | Detected as |
|---|---|
| Hailo-10H NPU | `lspci`: `0001:01:00.0 Co-processor: Hailo Technologies Ltd. Hailo-10H AI Processor` |
| USB speaker (Adafruit) | ALSA card 3, `plughw:UACDemoV10,0` |
| USB mic (Adafruit) | ALSA card 2, `USB PnP Sound Device` (sounddevice index varies 0–1 by enumeration) |
| Pi Camera v2 | IMX219 sensor on `/base/axi/pcie@1000120000/rp1/i2c@88000/imx219@10` |
| FREENOVE 5" LCD | DSI display on Pi 5 (works after re-seating both display + camera FPC cables; HDMI also works as second display) |

### Mic device index

`MIC_DEVICE_INDEX` in `core/config.py` is now resolved dynamically by `find_audio_devices()`. After USB re-enumeration the index can be 0 or 1 — the code handles either correctly.

### What does NOT auto-start on boot

- The on-device GUI agent (`./start_agent.sh`) — must be launched manually after each reboot. Future improvement: add a `bmo-gui` systemd unit or `~/.config/autostart/` entry.

## Daily run sequence

After every reboot:

```bash
ssh saweephd@<pi-ip>
sudo systemctl is-active bmo-ollama          # should say "active"
sudo systemctl is-active bmo-web             # should say "inactive"
cd ~/be-more-agent
source venv/bin/activate
./start_agent.sh
```

Then say "Hey BMO" or tap the LCD body to start a conversation.

## Known limitations of this build

- **Vision (`take a photo`) requires NPU swap.** Currently disabled. The agent prints a graceful "my eyes aren't working" instead of crashing. To re-enable vision, would need to either stop bmo-ollama temporarily or implement Option B from the build guide (hot-swap LLM ↔ VLM on demand).
- **Web UI and on-device GUI fight over the USB speaker.** Pick one mode at a time. `bmo-web` is currently disabled to avoid this.
- **LLM speed is ~5–6 tokens/sec** with qwen2.5-instruct:1.5b on the Hailo-10H. Long responses take 8–12 seconds. Could swap to qwen2.5-instruct:0.5b for ~2× speed at the cost of intelligence.
- **Wake word still requires clear, close speech.** Even at threshold 0.25, distance-from-mic and ambient noise affect detection. Tap-to-wake on the LCD always works.

## Files modified by these patches

| File | Patches applied |
|---|---|
| `core/config.py` | Wake word threshold (#3) |
| `agent_hailo.py` | VLM warmup disable (#2), warm-piper-needs-aplay condition (#4), aplay session isolation (#5), drain timeout (#6) |
| `web_app.py` | TemplateResponse signature (#1) |
| `/etc/systemd/system/bmo-ollama.service` | Created by `setup_services.sh` |
| `/etc/systemd/system/bmo-web.service` | Created by `setup_services.sh`, then `disabled` |

## Backup files in project root (left intentionally for reference)

- `agent_hailo.py.bak` — pre-debug-print state
- `agent_hailo.py.bak2` — after VLM/wake-word/web fixes, before TTS audio fixes
- `agent_hailo.py.working` — final clean working state (after debug prints stripped)

If a future bisect is needed, these are the labeled checkpoints.

## Upstream contribution

These five fixes (#1, #2, #4, #5, #6) are real bugs in the moorew fork. Worth opening a PR or issue against [github.com/moorew/be-more-hailo](https://github.com/moorew/be-more-hailo) so other builders don't hit the same wall. Patch #3 (wake word threshold) is more of a per-deployment tuning choice and not a fix per se.
