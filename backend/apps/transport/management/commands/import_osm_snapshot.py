"""Offline OSM snapshot import (contracts/cli-import.md)."""
import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.transport.importer import policy, report

logger = logging.getLogger(__name__)


def _short(value, limit=30):
    """Minimize operator-supplied text for INFO-and-above records (G-5)."""
    text = value if isinstance(value, str) else str(value)
    return text[:limit]


class Command(BaseCommand):
    help = "Import a retained OSM snapshot directory. No network I/O."

    def add_arguments(self, parser):
        parser.add_argument(
            "--snapshot-dir",
            required=True,
            help="Retained snapshot directory holding the input files",
        )
        parser.add_argument(
            "--report-path",
            default="./osm-import-report.json",
            help="Where to write the machine-readable import report",
        )
        parser.add_argument(
            "--snapshot-label",
            default=None,
            help="Human name for the snapshot (defaults to directory base name)",
        )

    def handle(self, *args, **options):
        snapshot_dir = Path(options["snapshot_dir"])
        label = options["snapshot_label"] or snapshot_dir.name
        logger.debug(
            "import start snapshot=%r snapshot_dir=%s", label, snapshot_dir
        )
        result = policy.run_import(snapshot_dir=snapshot_dir, label=label)
        self._write_report(options["report_path"], result.report)
        counts = result.report["counts"]
        logger.info(
            "import outcome=%s snapshot=%r stops=%d routes=%d",
            result.report["run"]["outcome"],
            _short(label),
            counts["stop"]["inserted"],
            counts["route"]["inserted"],
        )
        self.stdout.write(report.console_summary(result.report))
        if result.outcome != "succeeded":
            fatal = next(
                (
                    anomaly
                    for anomaly in result.report["anomalies"]
                    if anomaly["severity"] == "fatal"
                ),
                None,
            )
            logger.error(
                "import outcome=%s snapshot=%r fatal=%s report=%s",
                "aborted",
                _short(label),
                fatal["code"] if fatal is not None else "unknown",
                options["report_path"],
            )
            raise CommandError(
                f"import aborted; see {options['report_path']} for the "
                "fatal anomaly"
            )

    def _write_report(self, path, payload):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
