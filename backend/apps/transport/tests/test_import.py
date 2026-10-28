"""Sample import, idempotent rerun, and abort paths (US1).

Uses the tracked sample fixtures. The full snapshot is exercised via
the manual quickstart path.
"""
import hashlib
import json
import shutil
import socket
from pathlib import Path

from django.core.management import CommandError, call_command
from django.test import TestCase

from apps.transport.models import (
    ImportAnomaly,
    ImportRun,
    OsmSnapshot,
    Route,
    RouteMaster,
    RouteStopMembership,
    Stop,
)

FIXTURES = Path(__file__).parent / "fixtures" / "osm"


def _fixture_counts(name, osm_type):
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return sum(1 for e in payload["elements"] if e.get("type") == osm_type)


def _run_import(snapshot_dir, report_path):
    call_command(
        "import_osm_snapshot",
        snapshot_dir=str(snapshot_dir),
        report_path=str(report_path),
        snapshot_label="test-sample",
    )
    return json.loads(Path(report_path).read_text(encoding="utf-8"))


def _tmp_dir():
    tmp = Path("/tmp") / "gonaj-test-import"
    tmp.mkdir(exist_ok=True)
    return tmp


def _report_path(name):
    return _tmp_dir() / f"{name}.json"


class SampleImportTests(TestCase):
    def test_counts_match_fixture_contents(self):
        report = _run_import(FIXTURES, _report_path("one"))
        self.assertEqual(report["run"]["outcome"], "succeeded")
        self.assertEqual(
            Stop.objects.count(),
            _fixture_counts("osm_gcda_bus_stops.json", "node"),
        )
        self.assertEqual(
            Route.objects.count(),
            _fixture_counts("osm_gcda_routes.json", "relation"),
        )
        self.assertEqual(report["counts"]["stop"]["inserted"], Stop.objects.count())

    def test_rerun_reports_zero_changes(self):
        _run_import(FIXTURES, _report_path("one"))
        report = _run_import(FIXTURES, _report_path("two"))
        for entity, bucket in report["counts"].items():
            self.assertEqual(
                (bucket["inserted"], bucket["updated"]),
                (0, 0),
                f"{entity} changed on rerun",
            )
        self.assertEqual(OsmSnapshot.objects.count(), 1)
        self.assertEqual(ImportRun.objects.count(), 2)

    def test_report_matches_contract_schema(self):
        report = _run_import(FIXTURES, _report_path("schema"))
        for key in ("label", "recipe_ref", "snapshot", "run", "counts", "anomalies"):
            self.assertIn(key, report)
        for key in (
            "label", "source_timestamps", "retrieved_at", "imported_at"
        ):
            self.assertIn(key, report["snapshot"])
        for anomaly in report["anomalies"]:
            self.assertIn(anomaly["severity"], ("fatal", "warning", "info"))
            self.assertTrue(anomaly["code"])

    def test_positions_contiguous_and_source_index_kept(self):
        _run_import(FIXTURES, _report_path("positions"))
        for route in Route.objects.all():
            positions = list(
                route.stop_memberships.order_by("position").values_list(
                    "position", flat=True
                )
            )
            self.assertEqual(positions, list(range(1, len(positions) + 1)))
        membership = RouteStopMembership.objects.order_by("position").first()
        self.assertIsNotNone(membership.source_index)

class OfflineTests(TestCase):
    def test_import_with_only_localhost_network(self):
        real_socket = socket.socket

        def guarded_socket(family, type_, *args, **kwargs):
            sock = real_socket(family, type_, *args, **kwargs)
            orig_connect = sock.connect

            def connect(address):
                host = address[0] if isinstance(address, tuple) else address
                if host in ("127.0.0.1", "localhost", "::1"):
                    return orig_connect(address)
                raise OSError(f"network disabled for test: {address}")

            sock.connect = connect
            return sock

        socket.socket = guarded_socket
        try:
            report = _run_import(FIXTURES, _report_path("offline"))
        finally:
            socket.socket = real_socket
        self.assertEqual(report["run"]["outcome"], "succeeded")
        self.assertGreater(
            report["counts"]["stop"]["inserted"]
            + report["counts"]["stop"]["unchanged"],
            0,
        )

    def test_fixture_files_unmodified_by_import(self):
        before = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(FIXTURES.glob("*.json"))
        }
        _run_import(FIXTURES, _report_path("readonly"))
        after = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(FIXTURES.glob("*.json"))
        }
        self.assertEqual(before, after)


class AbortPathTests(TestCase):
    def test_missing_required_file_aborts_with_no_partial_state(self):
        empty = Path("/tmp") / "gonaj-test-empty"
        empty.mkdir(exist_ok=True)
        for child in empty.iterdir():
            if child.is_file():
                child.unlink()
        report_path = empty / "report.json"
        with self.assertRaises(CommandError):
            call_command(
                "import_osm_snapshot",
                snapshot_dir=str(empty),
                report_path=str(report_path),
            )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["run"]["outcome"], "aborted")
        codes = {a["code"] for a in report["anomalies"]}
        self.assertIn("REQUIRED_FILE_MISSING", codes)
        self.assertEqual(Stop.objects.count(), 0)
        self.assertEqual(Route.objects.count(), 0)
        self.assertEqual(RouteMaster.objects.count(), 0)

    def test_invalid_json_aborts(self):
        broken = Path("/tmp") / "gonaj-test-broken"
        if broken.exists():
            shutil.rmtree(broken)
        shutil.copytree(FIXTURES, broken)
        (broken / "osm_gcda_routes.json").write_text(
            "{not json", encoding="utf-8"
        )
        report_path = broken / "report.json"
        with self.assertRaises(CommandError):
            call_command(
                "import_osm_snapshot",
                snapshot_dir=str(broken),
                report_path=str(report_path),
            )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        codes = {a["code"] for a in report["anomalies"]}
        self.assertIn("INVALID_JSON", codes)

    def test_duplicate_osm_id_blocks_run(self):
        duped = Path("/tmp") / "gonaj-test-duped"
        if duped.exists():
            shutil.rmtree(duped)
        shutil.copytree(FIXTURES, duped)
        stops_path = duped / "osm_gcda_bus_stops.json"
        payload = json.loads(stops_path.read_text(encoding="utf-8"))
        payload["elements"].append(dict(payload["elements"][0]))
        stops_path.write_text(json.dumps(payload), encoding="utf-8")
        report_path = duped / "report.json"
        with self.assertRaises(CommandError):
            call_command(
                "import_osm_snapshot",
                snapshot_dir=str(duped),
                report_path=str(report_path),
            )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        codes = {a["code"] for a in report["anomalies"]}
        self.assertIn("DUPLICATE_OSM_ID", codes)
        self.assertEqual(Stop.objects.count(), 0)


class OptionalFileTests(TestCase):
    def test_missing_optional_files_recorded_as_info(self):
        slim = Path("/tmp") / "gonaj-test-slim"
        if slim.exists():
            shutil.rmtree(slim)
        shutil.copytree(FIXTURES, slim)
        for name in (
            "osm_gcda_bus_stations.json",
            "osm_gcda_route_members.json",
        ):
            (slim / name).unlink()
        report = _run_import(slim, slim / "report.json")
        self.assertEqual(report["run"]["outcome"], "succeeded")
        infos = [
            a
            for a in report["anomalies"]
            if a["severity"] == "info"
            and a["code"] == "OPTIONAL_FILE_MISSING"
        ]
        self.assertEqual(len(infos), 2)
        self.assertGreater(Stop.objects.count(), 0)
