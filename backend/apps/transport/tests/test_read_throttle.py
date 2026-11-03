"""Per-IP throttling tests (T035, FR-021–FR-024).

Uses test-lowered rates. Verifies the shared budget, the 429 with
`Retry-After`, per-client isolation, hashed counter keys with no raw
IP material, and spoof-proof identity unless a proxy is configured.
"""
from django.core.cache import caches
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from apps.journey.providers import meta as provider
from apps.journey.tests.test_transcribe import StubVoice, wav_file_bytes

from . import factories as f
from .factories import ApiTestCase

LOW_RATES = {
    "EXCEPTION_HANDLER":
        "apps.transport.api.errors.plain_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "transport_minute": "3/min",
        "transport_day": "1000/day",
    },
}
LOCMEM_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}


@override_settings(REST_FRAMEWORK=LOW_RATES)
class ThrottleTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-throttle")
        cls.master = f.make_master(cls.import_run, 51, "M")
        cls.a = f.make_stop(cls.import_run, 501, "A", 10.0, 76.3)
        cls.b = f.make_stop(cls.import_run, 502, "B", 10.01, 76.31)
        cls.route = f.make_route(
            cls.import_run, 501, "A-B", from_text="A", to_text="B")
        f.link_master(cls.import_run, cls.master, cls.route, 1)
        f.link_stop(cls.import_run, cls.route, cls.a, 1)
        f.link_stop(cls.import_run, cls.route, cls.b, 2)
        cls.paths = [
            ("/api/v1/routes/", {}),
            ("/api/v1/stops/", {"search": "A"}),
            # Real id, not a literal: Postgres sequences are not
            # reset by rolled-back tests, so pk 1 is not guaranteed
            # (SQLite reuses it, which is why this only failed in CI).
            (f"/api/v1/routes/{cls.route.id}/", {}),
        ]

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_budget_is_shared_across_endpoints(self):
        for path, params in self.paths:
            response = self.client.get(path, params,
                                       REMOTE_ADDR="10.0.0.1")
            self.assertEqual(response.status_code, 200, path)
        response = self.client.get("/api/v1/stops/", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(response.status_code, 429)

    def test_over_limit_returns_plain_429_with_retry_after(self):
        for _ in range(3):
            self.client.get("/api/v1/routes/", REMOTE_ADDR="10.0.0.2")
        response = self.client.get("/api/v1/routes/",
                                   REMOTE_ADDR="10.0.0.2")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {
            "detail": "Too many requests. "
                      "Please wait a moment and try again.",
        })
        self.assertIn("Retry-After", response)

    def test_other_client_is_unaffected(self):
        for _ in range(3):
            self.client.get("/api/v1/routes/", REMOTE_ADDR="10.0.0.3")
        response = self.client.get("/api/v1/routes/",
                                   REMOTE_ADDR="10.0.0.4")
        self.assertEqual(response.status_code, 200)

    def test_counter_keys_carry_no_raw_ip(self):
        self.client.get("/api/v1/routes/", REMOTE_ADDR="10.9.8.7")
        cache = caches["default"]
        keys = list(cache._cache.keys())
        self.assertTrue(keys)
        for key in keys:
            self.assertNotIn("10.9.8.7", key)
            self.assertIn("throttle_transport_", key)

    def test_spoofed_forwarded_for_ignored_without_proxy(self):
        for _ in range(3):
            self.client.get("/api/v1/routes/", REMOTE_ADDR="10.0.0.5")
        response = self.client.get(
            "/api/v1/routes/", REMOTE_ADDR="10.0.0.5",
            HTTP_X_FORWARDED_FOR="9.9.9.9, 8.8.8.8")
        self.assertEqual(response.status_code, 429)

    @override_settings(TRANSPORT_TRUSTED_PROXY="proxy.internal")
    def test_forwarded_for_honoured_with_trusted_proxy(self):
        for _ in range(3):
            response = self.client.get(
                "/api/v1/routes/", REMOTE_ADDR="proxy.internal",
                HTTP_X_FORWARDED_FOR="9.9.9.9")
            self.assertEqual(response.status_code, 200)
        response = self.client.get(
            "/api/v1/routes/", REMOTE_ADDR="proxy.internal",
            HTTP_X_FORWARDED_FOR="9.9.9.9")
        self.assertEqual(response.status_code, 429)
        other = self.client.get(
            "/api/v1/routes/", REMOTE_ADDR="proxy.internal",
            HTTP_X_FORWARDED_FOR="1.1.1.1")
        self.assertEqual(other.status_code, 200)


JOURNEY_RATES = {
    "EXCEPTION_HANDLER": "apps.transport.api.errors.plain_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "transport_minute": "3/min",
        "transport_day": "1000/day",
        "journey_min": "1000/min",
        "journey_day": "10000/day",
        "transcribe_min": "1000/min",
        "transcribe_day": "10000/day",
    },
}


class _BoomModel:
    """Model stub that always fails fast (outage fallback, one call)."""

    def __call__(self, **kwargs):
        raise Exception("boom")


class EnvDefaultTests(ApiTestCase):
    """Compiled defaults apply when env tuning is absent (015, T011)."""

    def test_missing_and_empty_env_fall_back_to_compiled_defaults(self):
        import os
        from unittest import mock

        from config import settings as settings_module

        scrubbed = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("JOURNEY_", "TRANSCRIBE_"))
        }
        with mock.patch.dict(os.environ, scrubbed, clear=True):
            self.assertEqual(
                settings_module._env_rate("JOURNEY_THROTTLE_MINUTE", "60/min"),
                "60/min",
            )
            self.assertEqual(
                settings_module._env_int("JOURNEY_MAX_QUESTION_CHARS", 500),
                500,
            )
        with mock.patch.dict(
            os.environ,
            {"JOURNEY_THROTTLE_MINUTE": "", "JOURNEY_MAX_QUESTION_CHARS": ""},
        ):
            self.assertEqual(
                settings_module._env_rate("JOURNEY_THROTTLE_MINUTE", "60/min"),
                "60/min",
            )
            self.assertEqual(
                settings_module._env_int("JOURNEY_MAX_QUESTION_CHARS", 500),
                500,
            )

    def test_set_env_values_flow_through(self):
        import os
        from unittest import mock

        from config import settings as settings_module

        with mock.patch.dict(
            os.environ,
            {
                "JOURNEY_THROTTLE_MINUTE": "7/min",
                "JOURNEY_MAX_QUESTION_CHARS": "42",
            },
        ):
            self.assertEqual(
                settings_module._env_rate("JOURNEY_THROTTLE_MINUTE", "60/min"),
                "7/min",
            )
            self.assertEqual(
                settings_module._env_int("JOURNEY_MAX_QUESTION_CHARS", 500),
                42,
            )


@override_settings(REST_FRAMEWORK=JOURNEY_RATES)
class JourneyBudgetTests(ApiTestCase):
    """Journey asks run under their own budget (015, FR-001)."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self._real = provider.complete_with_tools
        provider.complete_with_tools = _BoomModel()

    def tearDown(self):
        provider.complete_with_tools = self._real

    def ask(self, addr):
        return self.client.post(
            "/api/v1/journey/",
            {"question": "How do I get from South to Fort?"},
            format="json",
            REMOTE_ADDR=addr,
        )

    def test_journey_flood_does_not_consume_shared_reads(self):
        for _ in range(3):
            self.ask("10.2.0.1")
        response = self.client.get("/api/v1/stops/", REMOTE_ADDR="10.2.0.1")
        self.assertEqual(response.status_code, 200)

    def test_journey_flood_leaves_transcribe_untouched(self):
        for _ in range(3):
            self.ask("10.2.0.2")
        response = self.client.post(
            "/api/v1/journey/transcribe/", {}, format="multipart",
            REMOTE_ADDR="10.2.0.2",
        )
        self.assertNotEqual(response.status_code, 429)


TRANSCRIBE_RATES = {
    "EXCEPTION_HANDLER": "apps.transport.api.errors.plain_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "transport_minute": "3/min",
        "transport_day": "1000/day",
        "journey_min": "1000/min",
        "journey_day": "10000/day",
        "transcribe_min": "2/min",
        "transcribe_day": "1000/day",
    },
}


@override_settings(REST_FRAMEWORK=TRANSCRIBE_RATES)
class TranscribeBudgetTests(ApiTestCase):
    """Transcribe uploads run under their own budget (015, FR-002)."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self._real_voice = provider.transcribe_audio
        self._real_tools = provider.complete_with_tools
        provider.transcribe_audio = StubVoice(text="How do I get there?")
        provider.complete_with_tools = _BoomModel()

    def tearDown(self):
        provider.transcribe_audio = self._real_voice
        provider.complete_with_tools = self._real_tools

    def post_audio(self, addr):
        return self.client.post(
            "/api/v1/journey/transcribe/",
            {
                "audio": SimpleUploadedFile(
                    "question.wav", wav_file_bytes(), "audio/wav"
                )
            },
            format="multipart",
            REMOTE_ADDR=addr,
        )

    def test_transcribe_denied_over_own_minute_budget(self):
        self.assertEqual(self.post_audio("10.3.0.1").status_code, 200)
        self.assertEqual(self.post_audio("10.3.0.1").status_code, 200)
        denied = self.post_audio("10.3.0.1")
        self.assertEqual(denied.status_code, 429)
        self.assertEqual(
            denied.json()["detail"],
            "Too many requests. Please wait a moment and try again.",
        )
        self.assertIn("Retry-After", denied)

    def test_transcribe_flood_leaves_journey_unaffected(self):
        for _ in range(3):
            self.post_audio("10.3.0.2")
        response = self.client.post(
            "/api/v1/journey/",
            {"question": "How do I get from South to Fort?"},
            format="json",
            REMOTE_ADDR="10.3.0.2",
        )
        self.assertNotEqual(response.status_code, 429)
