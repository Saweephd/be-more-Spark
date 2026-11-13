"""Speech to text over the network, using the Wyoming protocol.

BMO sends the recorded request to a faster-whisper service on the home network
(the one on CIOspark2 that also serves the Jarvis voice device) and gets the
text back.  That is quicker than running whisper.cpp on the Pi, and the larger
model hears better.  If the service cannot be reached, the caller falls back to
the Pi's own Whisper, so BMO keeps working with the Spark off.

The Wyoming protocol is small enough to speak directly, so this needs no extra
Python package: each event is one JSON header line, optionally followed by a
JSON data block and a binary payload whose lengths the header gives.

Changelog
  1.0.0  2026-11-12  First version (pack 2: quicker speech to text).
"""

from __future__ import annotations

import json
import socket
import wave

CHUNK_BYTES = 8192


def encode_event(event_type: str, data: dict | None = None, payload: bytes = b"") -> bytes:
    """Serialise one Wyoming event."""
    data_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else b""
    header = {"type": event_type, "version": "1.5.4"}
    if data_bytes:
        header["data_length"] = len(data_bytes)
    if payload:
        header["payload_length"] = len(payload)
    return json.dumps(header).encode("utf-8") + b"\n" + data_bytes + payload


def read_event(stream) -> tuple[str, dict, bytes] | None:
    """Read one event from a binary file-like object.  None at end of stream."""
    line = stream.readline()
    if not line:
        return None
    header = json.loads(line.decode("utf-8"))
    data = dict(header.get("data") or {})
    data_length = int(header.get("data_length") or 0)
    if data_length:
        data.update(json.loads(_read_exact(stream, data_length).decode("utf-8")))
    payload_length = int(header.get("payload_length") or 0)
    payload = _read_exact(stream, payload_length) if payload_length else b""
    return header.get("type", ""), data, payload


def _read_exact(stream, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        part = stream.read(n - len(buf))
        if not part:
            raise ConnectionError("connection closed in the middle of an event")
        buf += part
    return buf


def parse_address(address: str) -> tuple[str, int]:
    host, _, port = address.strip().rpartition(":")
    if not host or not port.isdigit():
        raise ValueError(f"expected host:port, got {address!r}")
    return host, int(port)


def transcribe_pcm(pcm: bytes, rate: int, address: str, language: str = "en",
                   connect_timeout: float = 1.5, timeout: float = 12.0) -> str:
    """Send 16-bit mono PCM to a Wyoming speech to text service; return the text.

    Raises OSError (which includes timeouts and refused connections) or
    ConnectionError when the service cannot be used, so the caller can fall back."""
    host, port = parse_address(address)
    fmt = {"rate": rate, "width": 2, "channels": 1}
    with socket.create_connection((host, port), timeout=connect_timeout) as sock:
        sock.settimeout(timeout)
        out = bytearray()
        out += encode_event("transcribe", {"language": language})
        out += encode_event("audio-start", fmt)
        for i in range(0, len(pcm), CHUNK_BYTES):
            out += encode_event("audio-chunk", fmt, pcm[i:i + CHUNK_BYTES])
        out += encode_event("audio-stop")
        sock.sendall(bytes(out))
        with sock.makefile("rb") as stream:
            while True:
                event = read_event(stream)
                if event is None:
                    raise ConnectionError("service closed the connection without a transcript")
                event_type, data, _payload = event
                if event_type == "transcript":
                    return str(data.get("text", "")).strip()
                if event_type == "error":
                    raise ConnectionError(f"service error: {data.get('text', data)}")


def transcribe_wav(path: str, address: str, **kwargs) -> str:
    """Transcribe a 16-bit mono WAV file through the remote service."""
    with wave.open(path, "rb") as wav:
        if wav.getsampwidth() != 2 or wav.getnchannels() != 1:
            raise ValueError("expected 16-bit mono audio")
        rate = wav.getframerate()
        pcm = wav.readframes(wav.getnframes())
    return transcribe_pcm(pcm, rate, address, **kwargs)
