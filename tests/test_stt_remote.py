"""Tests for core/stt_remote.py against a small fake Wyoming service.

Run: python -m unittest tests.test_stt_remote
"""
import io
import socket
import socketserver
import threading
import unittest

from core.stt_remote import encode_event, parse_address, read_event, transcribe_pcm


class FakeWhisper(socketserver.StreamRequestHandler):
    reply_text = "what time is it"
    received = {}

    def handle(self):
        audio = b""
        types = []
        while True:
            event = read_event(self.rfile)
            if event is None:
                return
            event_type, data, payload = event
            types.append(event_type)
            if event_type == "audio-start":
                FakeWhisper.received["rate"] = data.get("rate")
            if event_type == "audio-chunk":
                audio += payload
            if event_type == "audio-stop":
                FakeWhisper.received["audio"] = audio
                FakeWhisper.received["types"] = types
                self.wfile.write(encode_event("transcript", {"text": " " + self.reply_text + " "}))
                self.wfile.flush()
                return


class WireFormatTests(unittest.TestCase):
    def test_round_trip_with_data_and_payload(self):
        raw = encode_event("audio-chunk", {"rate": 16000, "width": 2, "channels": 1}, b"\x01\x02\x03\x04")
        event_type, data, payload = read_event(io.BytesIO(raw))
        self.assertEqual(event_type, "audio-chunk")
        self.assertEqual(data["rate"], 16000)
        self.assertEqual(payload, b"\x01\x02\x03\x04")

    def test_event_without_data(self):
        event_type, data, payload = read_event(io.BytesIO(encode_event("audio-stop")))
        self.assertEqual((event_type, data, payload), ("audio-stop", {}, b""))

    def test_inline_data_from_older_services(self):
        raw = b'{"type": "transcript", "data": {"text": "hello"}}\n'
        self.assertEqual(read_event(io.BytesIO(raw))[1]["text"], "hello")

    def test_two_events_back_to_back(self):
        stream = io.BytesIO(encode_event("a", {"x": 1}) + encode_event("b", None, b"zz"))
        self.assertEqual(read_event(stream)[0], "a")
        self.assertEqual(read_event(stream)[2], b"zz")
        self.assertIsNone(read_event(stream))

    def test_truncated_payload_is_an_error(self):
        raw = encode_event("audio-chunk", None, b"12345678")[:-3]
        with self.assertRaises(ConnectionError):
            read_event(io.BytesIO(raw))

    def test_parse_address(self):
        self.assertEqual(parse_address("192.168.1.30:10300"), ("192.168.1.30", 10300))
        for bad in ("192.168.1.30", "host:port", ":10300", ""):
            with self.assertRaises(ValueError):
                parse_address(bad)


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), FakeWhisper)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.address = f"127.0.0.1:{self.server.server_address[1]}"
        FakeWhisper.received = {}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_transcribes_and_sends_all_audio(self):
        pcm = bytes(range(256)) * 200            # 51,200 bytes: several chunks
        text = transcribe_pcm(pcm, 16000, self.address)
        self.assertEqual(text, "what time is it")
        self.assertEqual(FakeWhisper.received["audio"], pcm)
        self.assertEqual(FakeWhisper.received["rate"], 16000)
        self.assertEqual(FakeWhisper.received["types"][:2], ["transcribe", "audio-start"])
        self.assertEqual(FakeWhisper.received["types"][-1], "audio-stop")

    def test_unreachable_service_raises_quickly(self):
        closed = socket.socket()
        closed.bind(("127.0.0.1", 0))
        port = closed.getsockname()[1]
        closed.close()
        with self.assertRaises(OSError):
            transcribe_pcm(b"\x00\x00" * 100, 16000, f"127.0.0.1:{port}", connect_timeout=0.5)


class FallbackTests(unittest.TestCase):
    def test_falls_back_to_local_when_remote_fails(self):
        import tempfile
        import wave
        from unittest import mock
        import core.stt as stt

        path = tempfile.mktemp(suffix=".wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
            w.writeframes(b"\x00\x00" * 1600)
        with mock.patch.object(stt, "STT_REMOTE", "127.0.0.1:1"), \
             mock.patch.object(stt, "transcribe_local", return_value="local answer") as local:
            stt._remote_retry_at = 0.0
            self.assertEqual(stt.transcribe_audio(path), "local answer")
            local.assert_called_once()
            # The failure is remembered: the next request skips the network
            # service instead of waiting for it to time out again.
            self.assertGreater(stt._remote_retry_at, 0)
            with mock.patch("core.stt_remote.transcribe_wav") as remote:
                self.assertEqual(stt.transcribe_audio(path), "local answer")
                remote.assert_not_called()
        stt._remote_retry_at = 0.0

    def test_remote_text_is_cleaned(self):
        import core.stt as stt
        self.assertEqual(stt.clean_transcript("hey beemo [BLANK_AUDIO]"), "hey BMO")
        self.assertEqual(stt.clean_transcript("(eerie music)"), "")
        self.assertEqual(stt.clean_transcript("Thank you."), "")

    def test_missing_file_returns_empty(self):
        import core.stt as stt
        self.assertEqual(stt.transcribe_audio(None), "")
        self.assertEqual(stt.transcribe_audio("/nonexistent.wav"), "")


if __name__ == "__main__":
    unittest.main()
