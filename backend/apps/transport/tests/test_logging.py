"""Debug-mode trace records for transport reads and imports (US1).

T009: failing lookups and successful searches emit DEBUG entries
naming the component and operation (FR-001).
T010: import runs emit phase entries plus an INFO outcome with the
snapshot label and counts (FR-001, FR-002).
"""
import tempfile
from pathlib import Path
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import Client, TestCase

from apps.transport.tests.test_import import FIXTURES


class DebugTraceTests(TestCase):
    def test_failing_lookup_logs_debug_trace(self):
        with self.assertLogs(
            "apps.transport.api.views", level="DEBUG"
        ) as captured:
            response = self.client.get("/api/v1/routes/999999/")
        self.assertEqual(response.status_code, 404)
        output = "\n".join(captured.output)
        self.assertIn("route_detail", output)
        self.assertIn("id=999999", output)
        self.assertIn("found=False", output)
        self.assertIn("method=GET", output)
        self.assertIn("path=/api/v1/routes/999999/", output)

    def test_successful_search_logs_debug_trace(self):
        with self.assertLogs(
            "apps.transport.api.views", level="DEBUG"
        ) as captured:
            response = self.client.get("/api/v1/routes/", {"search": "kochi"})
        self.assertEqual(response.status_code, 200)
        output = "\n".join(captured.output)
        self.assertIn("route_list", output)
        self.assertIn("kochi", output)
        self.assertIn("count=", output)
        self.assertIn("method=GET", output)


class ImportPhaseTests(TestCase):
    def test_import_run_logs_phases_and_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_path = str(Path(tmp) / "report.json")
            with self.assertLogs(
                "apps.transport.management.commands.import_osm_snapshot",
                level="DEBUG",
            ) as captured:
                call_command(
                    "import_osm_snapshot",
                    snapshot_dir=str(FIXTURES),
                    report_path=report_path,
                    snapshot_label="test-sample",
                )
        output = "\n".join(captured.output)
        self.assertIn("import start", output)
        self.assertIn("test-sample", output)
        self.assertIn("outcome=succeeded", output)
        self.assertIn("stops=", output)
        self.assertIn("routes=", output)


class ErrorBoundaryTests(TestCase):
    def test_client_error_logs_warning_without_traceback(self):
        with self.assertLogs(
            "apps.transport.api.errors", level="WARNING"
        ) as captured:
            response = self.client.get("/api/v1/routes/999999/")
        self.assertEqual(response.status_code, 404)
        output = "\n".join(captured.output)
        self.assertIn("status=404", output)
        self.assertIn("method=GET", output)
        self.assertIn("path=/api/v1/routes/999999/", output)
        self.assertNotIn("Traceback", output)

    def test_server_error_logs_error_with_traceback(self):
        client = Client(raise_request_exception=False)
        with mock.patch(
            "apps.transport.api.views.servable_routes",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertLogs(
                "apps.core.error_signals", level="ERROR"
            ) as captured:
                response = client.get("/api/v1/routes/")
        self.assertEqual(response.status_code, 500)
        output = "\n".join(captured.output)
        self.assertIn("status=500", output)
        self.assertIn("method=GET", output)
        self.assertIn("path=/api/v1/routes/", output)
        self.assertIn("RuntimeError", output)


class ImportFailureTests(TestCase):
    def test_aborted_import_logs_error(self):
        empty = Path("/tmp") / "gonaj-test-logging-empty"
        empty.mkdir(exist_ok=True)
        for child in empty.iterdir():
            if child.is_file():
                child.unlink()
        report_path = str(empty / "report.json")
        with self.assertLogs(
            "apps.transport.management.commands.import_osm_snapshot",
            level="ERROR",
        ) as captured:
            with self.assertRaises(CommandError):
                call_command(
                    "import_osm_snapshot",
                    snapshot_dir=str(empty),
                    report_path=report_path,
                    snapshot_label="test-sample",
                )
        output = "\n".join(captured.output)
        self.assertIn("outcome=aborted", output)
        self.assertIn("test-sample", output)
        self.assertIn("REQUIRED_FILE_MISSING", output)
        self.assertIn("report=", output)
