"""Anomaly-code and disposition tests on synthetic fixtures (US2)."""
import json
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from apps.transport.models import (
    ImportAnomaly,
    Route,
    RouteMaster,
    RouteStopMembership,
)

FIXTURES = Path(__file__).parent / "fixtures" / "osm"


def _run_case(name):
    report_path = Path("/tmp") / f"gonaj-test-{name}.json"
    call_command(
        "import_osm_snapshot",
        snapshot_dir=str(FIXTURES / name),
        report_path=str(report_path),
        snapshot_label=f"test-{name}",
    )
    return json.loads(report_path.read_text(encoding="utf-8"))


def _codes():
    return {
        (a.severity, a.code) for a in ImportAnomaly.objects.all()
    }


class MissingChildTests(TestCase):
    def test_blocked_master_and_orphan_route(self):
        _run_case("case_missing_child")
        self.assertFalse(
            RouteMaster.objects.filter(osm_id=20).exists(),
            "master with a missing child must be blocked, not partial",
        )
        self.assertIn(("fatal", "CHILD_REF_MISSING"), _codes())
        self.assertTrue(Route.objects.filter(osm_id=10).exists())
        self.assertIn(("warning", "ORPHAN_ROUTE"), _codes())


class QuirkTests(TestCase):
    def test_quarantine_duplicate_stray_asymmetric_and_names(self):
        _run_case("case_quirks")
        codes = _codes()
        self.assertIn(("warning", "NO_PLATFORM_SEQUENCE"), codes)
        self.assertIn(("warning", "DUPLICATE_PLATFORM"), codes)
        self.assertIn(("warning", "STRAY_MEMBER"), codes)
        self.assertIn(("warning", "ASYMMETRIC_FROM_TO"), codes)
        self.assertIn(("warning", "DUPLICATE_MASTER_NAME"), codes)

        quarantined = Route.objects.get(osm_id=12)
        self.assertTrue(quarantined.quarantined)

        dup_route = Route.objects.get(osm_id=11)
        refs = list(
            dup_route.stop_memberships.order_by("position").values_list(
                "stop__osm_id", flat=True
            )
        )
        self.assertEqual(
            refs, [1, 2, 1], "duplicate platforms keep order, never dedupe"
        )

        both = RouteMaster.objects.filter(name="Twin").order_by("osm_id")
        self.assertEqual([m.osm_id for m in both], [21, 22])
