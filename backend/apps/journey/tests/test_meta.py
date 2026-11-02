"""Meta, logging, and labelling tests (US4, T022).

Every journey and transcribe response carries model, provider, and
latency; the server log mirrors them with the ordered tools_used;
and no prompt, answer, transcript, or audio ever reaches the logs.
Written first; the meta emission already exists (T010/T020), so
these lock it in.
"""
import json

from django.conf import settings
from django.test import TestCase, override_settings
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


class FakeASRResponse:
    """Minimal httpx response double for the Meta ASR wire shape."""

    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


def _wav_bytes(data=None):
    import struct

    if data is None:
        data = b"\x00\x00" * 8000
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(data),
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        24000,
        48000,
        2,
        16,
        b"data",
        len(data),
    )
    return header + data


@override_settings(MODEL_API_KEY="test-key-not-a-secret")
class TranscribeWireTests(TestCase):
    """Direct httpx POST to the Meta ASR endpoint (013, T002).

    Written first; FAILS while transcribe_audio still uses the
    OpenAI-SDK shape.
    """

    def test_posts_request_json_plus_wav_audio_part(self):
        import json as jsonlib
        from unittest import mock

        import httpx

        body = _wav_bytes()
        with mock.patch.object(
            httpx,
            "post",
            return_value=FakeASRResponse(
                {"TranscribeResponse": {"transcript": "hello"}}
            ),
        ) as post:
            text = provider.transcribe_audio(
                filename="question.wav",
                audio_bytes=body,
                keywords=["Aluva", "Kaloor"],
            )
        self.assertEqual(text, "hello")
        self.assertEqual(post.call_count, 1)
        positional, kwargs = post.call_args
        self.assertTrue(positional[0].endswith("/asr/transcribe"))
        request_part = kwargs["files"]["request"]
        self.assertEqual(request_part[2], "application/json")
        metadata = jsonlib.loads(request_part[1])
        self.assertEqual(metadata["model"], "muse-voice-transcribe-1.0")
        self.assertEqual(metadata["audioEncoding"], "WAV")
        self.assertEqual(metadata["mode"], "PUSH_TO_TALK")
        self.assertEqual(metadata["languageBias"], ["English"])
        self.assertEqual(metadata["keywords"], ["Aluva", "Kaloor"])
        audio_part = kwargs["files"]["audio"]
        self.assertEqual(audio_part[0], "question.wav")
        self.assertEqual(audio_part[1], body)
        # Reference client sends the mimetypes guess (`audio/x-wav`).
        self.assertEqual(audio_part[2], "audio/x-wav")
        self.assertEqual(
            kwargs["headers"]["Accept"], "application/json"
        )
        self.assertTrue(
            kwargs["headers"]["Authorization"].startswith("Bearer ")
        )

    def test_accepts_top_level_transcript_shape(self):
        from unittest import mock

        import httpx

        with mock.patch.object(
            httpx,
            "post",
            return_value=FakeASRResponse({"transcript": "hi"}),
        ):
            self.assertEqual(
                provider.transcribe_audio(
                    filename="question.wav",
                    audio_bytes=_wav_bytes(),
                    keywords=[],
                ),
                "hi",
            )

    def test_empty_transcript_returns_empty(self):
        from unittest import mock

        import httpx

        with mock.patch.object(
            httpx,
            "post",
            return_value=FakeASRResponse(
                {"TranscribeResponse": {"transcript": "   "}}
            ),
        ):
            self.assertEqual(
                provider.transcribe_audio(
                    filename="question.wav",
                    audio_bytes=_wav_bytes(),
                    keywords=[],
                ),
                "",
            )

    def test_timeout_retries_once_then_raises(self):
        from unittest import mock

        import httpx

        with mock.patch.object(
            httpx,
            "post",
            side_effect=httpx.TimeoutException("timed out"),
        ) as post:
            with self.assertRaises(Exception):
                provider.transcribe_audio(
                    filename="question.wav",
                    audio_bytes=_wav_bytes(),
                    keywords=[],
                )
        self.assertEqual(post.call_count, 2)

    def test_connection_error_retries_then_succeeds(self):
        from unittest import mock

        import httpx

        request = httpx.Request("POST", "https://api.meta.ai/v1/x")
        with mock.patch.object(
            httpx,
            "post",
            side_effect=[
                httpx.ConnectError("down", request=request),
                FakeASRResponse(
                    {"TranscribeResponse": {"transcript": "ok"}}
                ),
            ],
        ) as post:
            self.assertEqual(
                provider.transcribe_audio(
                    filename="question.wav",
                    audio_bytes=_wav_bytes(),
                    keywords=[],
                ),
                "ok",
            )
        self.assertEqual(post.call_count, 2)

    def test_non_200_raises_without_retry(self):
        from unittest import mock

        import httpx

        with mock.patch.object(
            httpx,
            "post",
            return_value=FakeASRResponse({}, status_code=503),
        ) as post:
            with self.assertRaises(Exception):
                provider.transcribe_audio(
                    filename="question.wav",
                    audio_bytes=_wav_bytes(),
                    keywords=[],
                )
        self.assertEqual(post.call_count, 1)


@override_settings(MODEL_API_KEY="outage-key-marker-4417")
class TranscribeOutageTests(TestCase):
    """Upstream outage plus privacy at the httpx boundary (013, T009).

    Written first; FAILS if an outage retries more than once, leaks
    key or audio material into logs or the response, or returns
    anything but the plain cannot-transcribe message.
    """

    def _post_wav(self, data=None):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return APIClient().post(
            "/api/v1/journey/transcribe/",
            {
                "audio": SimpleUploadedFile(
                    "question.wav", _wav_bytes(data), "audio/wav"
                )
            },
            format="multipart",
        )

    def test_timeout_retries_once_then_plain_400(self):
        from unittest import mock

        import httpx

        with mock.patch.object(
            httpx,
            "post",
            side_effect=httpx.TimeoutException("down"),
        ) as post:
            response = self._post_wav()
        self.assertEqual(post.call_count, 2)
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("could not transcribe", body["detail"].lower())
        self.assertNotIn("transcript", body)

    def test_connection_error_retries_once_then_plain_400(self):
        from unittest import mock

        import httpx

        request = httpx.Request("POST", "https://api.meta.ai/v1/x")
        with mock.patch.object(
            httpx,
            "post",
            side_effect=[
                httpx.ConnectError("down", request=request),
                httpx.ConnectError("down", request=request),
            ],
        ) as post:
            response = self._post_wav()
        self.assertEqual(post.call_count, 2)
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("could not transcribe", body["detail"].lower())
        self.assertNotIn("transcript", body)

    def test_outage_keeps_key_and_audio_out_of_logs_and_body(self):
        from unittest import mock

        import httpx

        audio_marker = "sweep-audio-marker-4417"
        with (
            self.assertLogs(
                "apps.journey.views", level="DEBUG"
            ) as views_logs,
            self.assertLogs(
                "apps.journey.providers.meta", level="DEBUG"
            ) as meta_logs,
            mock.patch.object(
                httpx,
                "post",
                side_effect=httpx.TimeoutException("down"),
            ),
        ):
            response = self._post_wav(
                (audio_marker.encode() * 700)[:16000]
            )
        self.assertEqual(response.status_code, 400)
        output = "\n".join(views_logs.output + meta_logs.output)
        self.assertNotIn("outage-key-marker-4417", output)
        self.assertNotIn(audio_marker, output)
        raw = response.content.decode()
        self.assertNotIn("outage-key-marker-4417", raw)
        self.assertNotIn(audio_marker, raw)


def _wav_upload(name="question.wav"):
    from django.core.files.uploadedfile import SimpleUploadedFile

    return {
        "audio": SimpleUploadedFile(
            name,
            (
                b"RIFF"
                + (36 + 16000).to_bytes(4, "little")
                + b"WAVEfmt "
                + (16).to_bytes(4, "little")
                + (1).to_bytes(2, "little")
                + (1).to_bytes(2, "little")
                + (24000).to_bytes(4, "little")
                + (48000).to_bytes(4, "little")
                + (2).to_bytes(2, "little")
                + (16).to_bytes(2, "little")
                + b"data"
                + (16000).to_bytes(4, "little")
                + b"\x00\x00" * 8000
            ),
            "audio/wav",
        )
    }


class TranscribeMetaTests(TestCase):
    def test_transcribe_meta_matches_configured_voice_model(self):
        from types import SimpleNamespace

        real = provider.transcribe_audio
        provider.transcribe_audio = lambda **kwargs: SimpleNamespace(
            text="Hello"
        )
        try:
            response = APIClient().post(
                "/api/v1/journey/transcribe/",
                _wav_upload(),
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

        real = provider.transcribe_audio
        provider.transcribe_audio = lambda **kwargs: SimpleNamespace(
            text="secret-transcript-marker-7712"
        )
        try:
            with self.assertLogs("apps.journey.views", level="INFO") as logs:
                APIClient().post(
                    "/api/v1/journey/transcribe/",
                    _wav_upload(),
                    format="multipart",
                )
        finally:
            provider.transcribe_audio = real
        output = "\n".join(logs.output)
        self.assertIn(settings.TRANSCRIBE_MODEL, output)
        self.assertNotIn("secret-transcript-marker-7712", output)
