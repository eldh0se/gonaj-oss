"""Machine-readable JSON report plus console summary."""
from collections import Counter

ENTITY_ORDER = (
    "stop",
    "route",
    "route_master",
    "route_stop_membership",
    "route_master_membership",
)


def build_report(snapshot, run, counts, anomalies):
    """Assemble the report payload per contracts/import-report.md."""
    serialised = []
    for anomaly in anomalies:
        serialised.append(
            {
                "severity": anomaly.severity,
                "code": anomaly.code,
                "entity": (
                    {
                        "osm_type": anomaly.entity_osm_type,
                        "osm_id": anomaly.entity_osm_id,
                    }
                    if anomaly.entity_osm_id is not None
                    else None
                ),
                "detail": anomaly.detail,
            }
        )
    return {
        "label": snapshot.label,
        "recipe_ref": snapshot.recipe_ref,
        "snapshot": {
            "label": snapshot.label,
            "source_timestamps": snapshot.source_timestamps,
            "retrieved_at": snapshot.retrieved_at.isoformat(),
            "imported_at": snapshot.imported_at.isoformat(),
        },
        "run": {
            "started_at": run.started_at.isoformat(),
            "finished_at": (
                run.finished_at.isoformat() if run.finished_at else None
            ),
            "outcome": run.outcome,
        },
        "counts": {
            entity: {
                "inserted": counts.get(entity, {}).get("inserted", 0),
                "updated": counts.get(entity, {}).get("updated", 0),
                "unchanged": counts.get(entity, {}).get("unchanged", 0),
            }
            for entity in ENTITY_ORDER
        },
        "anomalies": serialised,
    }


def console_summary(report):
    """One human-readable block: counts plus anomaly totals."""
    lines = [
        f"snapshot {report['label']} → {report['run']['outcome']}",
    ]
    for entity in ENTITY_ORDER:
        bucket = report["counts"][entity]
        lines.append(
            f"  {entity}: +{bucket['inserted']} "
            f"~{bucket['updated']} ={bucket['unchanged']}"
        )
    by_severity = Counter(a["severity"] for a in report["anomalies"])
    lines.append(
        "anomalies: "
        + ", ".join(
            f"{severity}={by_severity.get(severity, 0)}"
            for severity in ("fatal", "warning", "info")
        )
    )
    return "\n".join(lines)
