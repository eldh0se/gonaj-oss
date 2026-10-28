"""Provenance chain tests: record → run → snapshot → recipe (US3)."""
import json
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from apps.transport.models import ImportRun, Stop

FIXTURES = Path(__file__).parent / "fixtures" / "osm"


class ProvenanceTests(TestCase):
    def test_every_record_resolves_to_recipe(self):
        report_path = Path("/tmp") / "gonaj-test-provenance.json"
        call_command(
            "import_osm_snapshot",
            snapshot_dir=str(FIXTURES),
            report_path=str(report_path),
            snapshot_label="test-provenance",
        )
        stop = Stop.objects.order_by("osm_id").first()
        self.assertIsNotNone(stop)
        run = stop.import_run
        self.assertIsInstance(run, ImportRun)
        snapshot = run.snapshot
        for field in (
            "label",
            "recipe_ref",
            "source_timestamps",
            "retrieved_at",
            "imported_at",
        ):
            self.assertTrue(
                getattr(snapshot, field),
                f"OsmSnapshot.{field} must be present",
            )
        self.assertIn("osm_gcda_bus_stops.json", snapshot.source_timestamps)
        self.assertEqual(
            stop.import_run.snapshot.recipe_ref, snapshot.recipe_ref
        )
