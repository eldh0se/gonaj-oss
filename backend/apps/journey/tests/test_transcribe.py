"""Transcribe endpoint tests (US3, T018).

Stubbed voice model (no network, no key, no audio retained).
Written first; FAILS before T020.
"""
from types import SimpleNamespace

from django.core.files.uploadedfile import SimpleUploadedFile
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


class TranscribeTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self._real = provider.transcribe_audio

    def tearDown(self):
        provider.transcribe_audio = self._real

    def post_audio(self, content=b"fake-audio-bytes", name="q.webm"):
        return self.client.post(
            "/api/v1/journey/transcribe/",
            {"audio": SimpleUploadedFile(name, content)},
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
        self.assertTrue(stub.kwargs[0]["audio_bytes"].startswith(b"fake-audio"))

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
