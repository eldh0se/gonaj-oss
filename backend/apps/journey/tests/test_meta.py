"""Meta, logging, and labelling tests (US4, T022).

Every journey and transcribe response carries model, provider, and
latency; the server log mirrors them with the ordered tools_used;
and no prompt, answer, transcript, or audio ever reaches the logs.
Written first; the meta emission already exists (T010/T020), so
these lock it in.
"""
import json

from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from apps.journey.providers import meta as provider
from apps.transport.tests.factories import ApiTestCase
from apps.journey.tests.test_journey import StubModel, _Message, _Response, _ToolCall


class JourneyMetaTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self._real = provider.complete_with_tools

    def tearDown(self):
        provider.complete_with_tools = self._real

    def test_answer_meta_matches_configured_model(self):
        stub = StubModel(
            script=[_Response(_Message(content="No direct service known."))]
        )
        provider.complete_with_tools = stub
        body = self.client.post(
            "/api/v1/journey/", {"question": "Anything?"}, format="json"
        ).json()
        self.assertEqual(body["meta"]["model"], settings.JOURNEY_MODEL)
        self.assertEqual(
            body["meta"]["provider"], settings.JOURNEY_MODEL_PROVIDER
        )
        self.assertIsInstance(body["meta"]["latency_ms"], int)
        self.assertGreaterEqual(body["meta"]["latency_ms"], 0)

    def test_fallback_meta_uses_local_fallback(self):
        stub = StubModel(error=Exception("boom"))
        provider.complete_with_tools = stub
        body = self.client.post(
            "/api/v1/journey/", {"question": "Anything?"}, format="json"
        ).json()
        self.assertEqual(body["meta"]["model"], "none")
        self.assertEqual(body["meta"]["provider"], "local-fallback")
        self.assertIsInstance(body["meta"]["latency_ms"], int)

    def test_server_log_carries_meta_and_tools_but_no_content(self):
        marker = "zebra-personal-marker-3948"
        stub = StubModel(
            script=[_Response(_Message(content="No direct service known."))]
        )
        provider.complete_with_tools = stub
        with self.assertLogs("apps.journey.agent", level="INFO") as logs:
            self.client.post(
                "/api/v1/journey/",
                {"question": f"Take me {marker} home?"},
                format="json",
            )
        output = "\n".join(logs.output)
        self.assertIn(settings.JOURNEY_MODEL, output)
        self.assertIn(settings.JOURNEY_MODEL_PROVIDER, output)
        self.assertIn("latency_ms=", output)
        self.assertIn("tools_used=", output)
        self.assertNotIn(marker, output)
        self.assertNotIn("No direct service known", output)


class TranscribeMetaTests(TestCase):
    def test_transcribe_meta_matches_configured_voice_model(self):
        from types import SimpleNamespace
        from django.core.files.uploadedfile import SimpleUploadedFile

        real = provider.transcribe_audio
        provider.transcribe_audio = lambda **kwargs: SimpleNamespace(
            text="Hello"
        )
        try:
            response = APIClient().post(
                "/api/v1/journey/transcribe/",
                {"audio": SimpleUploadedFile("q.webm", b"bytes")},
                format="multipart",
            )
        finally:
            provider.transcribe_audio = real
        body = response.json()
        self.assertEqual(body["meta"]["model"], settings.TRANSCRIBE_MODEL)
        self.assertEqual(
            body["meta"]["provider"], settings.JOURNEY_MODEL_PROVIDER
        )
        self.assertIsInstance(body["meta"]["latency_ms"], int)

    def test_transcribe_log_carries_no_audio_or_transcript(self):
        from types import SimpleNamespace
        from django.core.files.uploadedfile import SimpleUploadedFile

        real = provider.transcribe_audio
        provider.transcribe_audio = lambda **kwargs: SimpleNamespace(
            text="secret-transcript-marker-7712"
        )
        try:
            with self.assertLogs("apps.journey.views", level="INFO") as logs:
                APIClient().post(
                    "/api/v1/journey/transcribe/",
                    {"audio": SimpleUploadedFile("q.webm", b"bytes")},
                    format="multipart",
                )
        finally:
            provider.transcribe_audio = real
        output = "\n".join(logs.output)
        self.assertIn(settings.TRANSCRIBE_MODEL, output)
        self.assertNotIn("secret-transcript-marker-7712", output)
