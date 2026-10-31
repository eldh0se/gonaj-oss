"""Mode-dependent thresholds, redaction, and resilience (007).

T003: console/root thresholds follow the running mode and every entry
carries a timezone-aware, sortable timestamp (FR-003, FR-004).
T004: secrets, credentials, and private content never reach log output
in any mode (FR-006, FR-007).
T007: a failing log handler never changes request/command outcomes
(FR-008).
"""
import io
import json
import logging
import os
import re

from django.conf import settings as django_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


class ThresholdTests(SimpleTestCase):
    def test_debug_mode_is_verbose(self):
        from config.settings import build_logging_config

        config = build_logging_config(True)
        self.assertEqual(config["handlers"]["console"]["level"], "DEBUG")
        self.assertEqual(config["root"]["level"], "DEBUG")

    def test_production_mode_is_restrained(self):
        from config.settings import build_logging_config

        config = build_logging_config(False)
        self.assertEqual(config["handlers"]["console"]["level"], "INFO")
        self.assertEqual(config["root"]["level"], "INFO")

    def test_active_config_matches_running_mode(self):
        from config.settings import build_logging_config

        # LOGGING is built once at startup from the environment; the
        # test runner may flip settings.DEBUG afterwards, so compare
        # against the startup mode, not the runtime flag.
        startup_debug = os.environ.get("DJANGO_DEBUG", "1") == "1"
        self.assertEqual(
            django_settings.LOGGING,
            build_logging_config(startup_debug),
        )

    def test_entries_carry_sortable_timestamps(self):
        formatter_cfg = django_settings.LOGGING["formatters"]["triage"]
        formatter = logging.Formatter(
            fmt=formatter_cfg["format"],
            datefmt=formatter_cfg["datefmt"],
            style=formatter_cfg["style"],
        )
        record = logging.LogRecord(
            "test", logging.INFO, __file__, 1, "hello", None, None
        )
        self.assertRegex(formatter.format(record), TIMESTAMP_RE)


class RedactionTests(SimpleTestCase):
    def _capture(self, message, args):
        from apps.core.redaction import RedactionFilter

        stream = io.StringIO()
        logger = logging.getLogger("test.redaction.007")
        handler = logging.StreamHandler(stream=stream)
        handler.addFilter(RedactionFilter())
        logger.addHandler(handler)
        try:
            logger.info(message, args)
        finally:
            logger.removeHandler(handler)
        return stream.getvalue()

    def test_secret_values_are_scrubbed(self):
        output = self._capture(
            "loaded %(SECRET_KEY)r db %(PASSWORD)r",
            {"SECRET_KEY": "dev-only-insecure-key", "PASSWORD": "gonaj"},
        )
        self.assertNotIn("dev-only-insecure-key", output)
        self.assertNotIn("gonaj", output)
        self.assertIn("***", output)

    def test_tokens_and_private_content_are_scrubbed(self):
        output = self._capture(
            "call %(token)r %(question)r %(transcript)r",
            {
                "token": "m3t4-t0k3n",
                "question": "how do I get home?",
                "transcript": "spoken words",
            },
        )
        for leaked in ("m3t4-t0k3n", "how do I get home?", "spoken words"):
            self.assertNotIn(leaked, output)

    def test_safe_values_pass_through(self):
        output = self._capture(
            "journey model=%(model)r provider=%(provider)r latency_ms=%(latency_ms)r",
            {"model": "muse-spark-1.3", "provider": "meta", "latency_ms": 812},
        )
        self.assertIn("muse-spark-1.3", output)
        self.assertIn("meta", output)
        self.assertIn("812", output)


class BrokenStream(io.StringIO):
    def write(self, s):
        raise OSError("disk full")


class ResilienceTests(SimpleTestCase):
    def test_broken_handler_does_not_break_flow(self):
        logger = logging.getLogger("test.resilience.007")
        logger.addHandler(logging.StreamHandler(stream=BrokenStream()))
        try:
            logger.info("routine entry")
            try:
                raise RuntimeError("boom")
            except RuntimeError:
                logger.exception("failure entry")
            continued = True
        finally:
            logger.handlers.clear()
        self.assertTrue(continued)


class JourneySweepTests(TestCase):
    QUESTION = "sweep-marker-question-xyzzy"
    AUDIO_MARKER = b"sweep-marker-audio-xyzzy"

    def test_journey_paths_emit_no_private_content(self):
        with override_settings(MODEL_API_KEY=""):
            with self.assertLogs(level="DEBUG") as captured:
                ask = self.client.post(
                    "/api/v1/journey/",
                    json.dumps({"question": self.QUESTION}),
                    content_type="application/json",
                )
                self.assertEqual(ask.status_code, 200)
                self.assertEqual(ask.json()["status"], "refuse")
                audio = SimpleUploadedFile(
                    "q.webm", self.AUDIO_MARKER, content_type="audio/webm"
                )
                tx = self.client.post(
                    "/api/v1/journey/transcribe/", {"audio": audio}
                )
                self.assertEqual(tx.status_code, 400)
        output = "\n".join(captured.output)
        self.assertNotIn(self.QUESTION, output)
        self.assertNotIn(self.AUDIO_MARKER.decode(), output)
        self.assertNotIn("cannot answer right now", output)
        self.assertNotIn("We could not transcribe that audio", output)
