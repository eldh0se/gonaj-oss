"""Transcribe endpoint tests (US3, T018).

Stubbed voice model (no network, no key, no audio retained).
Written first; FAILS before T020.
"""
from types import SimpleNamespace

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from apps.journey.providers import meta as provider
from apps.transport.tests.factories import ApiTestCase


class StubVoice:
    def __init__(self, text="How do I get there?", error=None):
        self.text = text
        self.error = error
        self.calls = 0
        self.kwargs = []

    def __call__(self, **kwargs):
        self.calls += 1
        self.kwargs.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(text=self.text)


def wav_file_bytes(sample_rate=24000, channels=1, bits=16, marker=b"\x00\x00"):
    """Minimal mono PCM WAV body for upload tests (013)."""
    import struct

    data = marker * 8000
    block_align = channels * bits // 8
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(data),
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate,
        sample_rate * block_align,
        block_align,
        bits,
        b"data",
        len(data),
    ) + data


class TranscribeTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self._real = provider.transcribe_audio

    def tearDown(self):
        provider.transcribe_audio = self._real

    def post_audio(
        self,
        content=None,
        name="question.wav",
        content_type="audio/wav",
    ):
        if content is None:
            content = wav_file_bytes()
        return self.client.post(
            "/api/v1/journey/transcribe/",
            {"audio": SimpleUploadedFile(name, content, content_type)},
            format="multipart",
        )

    def test_audio_returns_editable_transcript_with_voice_meta(self):
        stub = StubVoice(text="How do I get to Fort Kochi?")
        provider.transcribe_audio = stub
        response = self.post_audio()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["transcript"], "How do I get to Fort Kochi?")
        self.assertEqual(body["meta"]["model"], "muse-voice-transcribe-1.0")
        self.assertEqual(body["meta"]["provider"], "meta")
        self.assertIsInstance(body["meta"]["latency_ms"], int)
        self.assertEqual(stub.calls, 1)
        self.assertTrue(
            stub.kwargs[0]["audio_bytes"].startswith(b"RIFF")
        )

    def test_success_sends_no_keywords_key(self):
        # Regression: a stop name ("Aarow Global Business Solutions")
        # made the endpoint 400 the whole transcription, so no
        # vocabulary bias is sent at all.
        stub = StubVoice(text="How do I get to Fort Kochi?")
        provider.transcribe_audio = stub
        response = self.post_audio()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(stub.calls, 1)
        self.assertNotIn("keywords", stub.kwargs[0])

    def test_filename_normalized_to_wav(self):
        stub = StubVoice(text="hello")
        provider.transcribe_audio = stub
        response = self.post_audio(name="MyRec.WAV")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(stub.calls, 1)
        self.assertTrue(stub.kwargs[0]["filename"].endswith(".wav"))
        self.assertNotIn("WAV", stub.kwargs[0]["filename"])

    def test_non_wav_extension_rejected_before_model_call(self):
        stub = StubVoice()
        provider.transcribe_audio = stub
        response = self.post_audio(
            name="q.webm", content_type="audio/webm"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(stub.calls, 0)

    def test_wrong_mime_rejected_before_model_call(self):
        stub = StubVoice()
        provider.transcribe_audio = stub
        response = self.post_audio(content_type="audio/webm")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(stub.calls, 0)

    def test_corrupt_wav_header_rejected(self):
        stub = StubVoice()
        provider.transcribe_audio = stub
        response = self.post_audio(content=b"RIFF" + b"\x00" * 40)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(stub.calls, 0)

    def test_unsupported_sample_rate_rejected(self):
        stub = StubVoice()
        provider.transcribe_audio = stub
        response = self.post_audio(content=wav_file_bytes(sample_rate=8000))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(stub.calls, 0)

    def test_stereo_rejected(self):
        stub = StubVoice()
        provider.transcribe_audio = stub
        response = self.post_audio(content=wav_file_bytes(channels=2))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(stub.calls, 0)

    def test_missing_audio_is_plain_400_without_guess(self):
        response = self.client.post(
            "/api/v1/journey/transcribe/", {}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_oversized_audio_is_rejected(self):
        stub = StubVoice()
        provider.transcribe_audio = stub
        response = self.post_audio(content=b"x" * (5 * 1024 * 1024 + 1))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(stub.calls, 0)

    def test_empty_transcript_is_never_guessed(self):
        stub = StubVoice(text="   ")
        provider.transcribe_audio = stub
        response = self.post_audio()
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_model_outage_is_plain_cannot_transcribe(self):
        stub = StubVoice(error=Exception("boom"))
        provider.transcribe_audio = stub
        response = self.post_audio()
        self.assertEqual(response.status_code, 400)
        self.assertIn("transcrib", response.json()["detail"].lower())

    def test_get_is_plain_405(self):
        response = self.client.get("/api/v1/journey/transcribe/")
        self.assertEqual(response.status_code, 405)
        self.assertIn("detail", response.json())

    @override_settings(
        REST_FRAMEWORK={
            "EXCEPTION_HANDLER": (
                "apps.transport.api.errors.plain_exception_handler"
            ),
            "DEFAULT_THROTTLE_RATES": {
                "transport_minute": "180/min",
                "transport_day": "5000/day",
                "journey_min": "60/min",
                "journey_day": "1500/day",
                "transcribe_min": "1/min",
                "transcribe_day": "1000/day",
            },
        }
    )
    def test_denied_upload_makes_no_transcribe_call(self):
        stub = StubVoice(text="How do I get there?")
        provider.transcribe_audio = stub
        first = self.post_audio()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(stub.calls, 1)
        denied = self.post_audio()
        self.assertEqual(denied.status_code, 429)
        self.assertIn("Retry-After", denied)
        self.assertEqual(stub.calls, 1)
