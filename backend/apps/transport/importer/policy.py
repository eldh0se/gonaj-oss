"""Import policy: plan, then write. No network I/O in this module.

Two phases keep reruns byte-identical: a pure planning pass derives
every field value up front, and the write pass only persists. Nothing
here silently repairs source deviations: every deviation is recorded,
quarantined, or blocking.
"""
from collections import Counter
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from apps.transport.importer import parse
from apps.transport.importer import report as report_mod
from apps.transport.models import (
    ImportAnomaly,
    ImportRun,
    OsmSnapshot,
    Route,
    RouteMaster,
    RouteMasterMembership,
    RouteStopMembership,
    Stop,
)

RECIPE_REF = "data/osm/gcda/osm-extraction.md"

# Stable anomaly codes (closed set).
REQUIRED_FILE_MISSING = "REQUIRED_FILE_MISSING"
INVALID_JSON = "INVALID_JSON"
DUPLICATE_OSM_ID = "DUPLICATE_OSM_ID"
CHILD_REF_MISSING = "CHILD_REF_MISSING"
NO_PLATFORM_SEQUENCE = "NO_PLATFORM_SEQUENCE"
DUPLICATE_PLATFORM = "DUPLICATE_PLATFORM"
STRAY_MEMBER = "STRAY_MEMBER"
ASYMMETRIC_FROM_TO = "ASYMMETRIC_FROM_TO"
ORPHAN_ROUTE = "ORPHAN_ROUTE"
OPTIONAL_FILE_MISSING = "OPTIONAL_FILE_MISSING"
DUPLICATE_MASTER_NAME = "DUPLICATE_MASTER_NAME"


class ImportResult:
    def __init__(self, outcome, report):
        self.outcome = outcome
        self.report = report


def _upsert(model, lookup, values, counters, key, run=None):
    """Natural-key upsert that only writes on change.

    Fresh rows record their creating run; the comparison excludes
    import_run, so a new run never counts as a change. Returns
    "inserted", "updated", or "unchanged" and tallies it, so a rerun
    over identical data reports zero writes.
    """
    try:
        obj = model.objects.get(**lookup)
    except model.DoesNotExist:
        create_kwargs = dict(values)
        if run is not None:
            create_kwargs["import_run"] = run
        model.objects.create(**lookup, **create_kwargs)
        counters[key]["inserted"] += 1
        return "inserted"
    changed = any(getattr(obj, field) != value for field, value in values.items())
    if changed:
        for field, value in values.items():
            setattr(obj, field, value)
        obj.save()
        counters[key]["updated"] += 1
        return "updated"
    counters[key]["unchanged"] += 1
    return "unchanged"


def _sync_memberships(related_manager, child_field, desired, counters, key, run):
    """Rebuild an ordered membership set only when it differs.

    desired: list of dicts mapping the child FK field to an id, plus
    position and source_index. Rebuild keeps position contiguous by
    construction; identical sets are left untouched so reruns report
    zero writes.
    """
    existing = list(
        related_manager.order_by("position").values_list(
            child_field, "position", "source_index"
        )
    )
    wanted = [
        (item[child_field], item["position"], item["source_index"])
        for item in desired
    ]
    if existing == wanted:
        counters[key]["unchanged"] += len(wanted)
        return
    related_manager.all().delete()
    parent_field = related_manager.field.name
    parent_obj = related_manager.instance
    membership_model = related_manager.model
    membership_model.objects.bulk_create(
        [
            membership_model(
                **{
                    parent_field: parent_obj,
                    f"{child_field}_id": item[child_field],
                    "position": item["position"],
                    "source_index": item["source_index"],
                    "import_run": run,
                }
            )
            for item in desired
        ]
    )
    counters[key]["inserted"] += len(wanted)


def _empty_counters():
    return {
        "stop": {"inserted": 0, "updated": 0, "unchanged": 0},
        "route": {"inserted": 0, "updated": 0, "unchanged": 0},
        "route_master": {"inserted": 0, "updated": 0, "unchanged": 0},
        "route_stop_membership": {"inserted": 0, "updated": 0, "unchanged": 0},
        "route_master_membership": {
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
        },
    }


def _snapshot_for(label, loaded, snapshot_dir):
    """Reuse the snapshot row for identical input; else append."""
    timestamps = loaded["source_timestamps"]
    try:
        return OsmSnapshot.objects.get(label=label, source_timestamps=timestamps), False
    except OsmSnapshot.DoesNotExist:
        pass
    files = [name for name in loaded["hashes"] if (snapshot_dir / name).exists()]
    newest_mtime = max((snapshot_dir / name).stat().st_mtime for name in files)
    retrieved_at = timezone.datetime.fromtimestamp(
        newest_mtime, tz=timezone.get_current_timezone()
    )
    snapshot = OsmSnapshot.objects.create(
        label=label,
        recipe_ref=RECIPE_REF,
        source_timestamps=timestamps,
        retrieved_at=retrieved_at,
        imported_at=timezone.now(),
    )
    return snapshot, True


def _note(anomalies, severity, code, detail, osm_type=None, osm_id=None):
    anomalies.append(
        {
            "severity": severity,
            "code": code,
            "detail": detail,
            "osm_type": osm_type,
            "osm_id": osm_id,
        }
    )


def _platform_refs(route_raw):
    """Ordered (source_index, stop ref) for role=platform node members."""
    return [
        (member["source_index"], member["ref"])
        for member in route_raw.get("members", [])
        if member.get("type") == "node" and (member.get("role") or "") == "platform"
    ]


def _plan(route_elements_list, master_elements):
    """Pure planning pass: derive every field value before any write.

    Returns (route_plans, master_plans, anomalies) where each plan
    holds final field values, so the write pass never revisits a row.
    """
    route_elements = {raw["osm_id"]: raw for raw in route_elements_list}
    anomalies = []

    # Master membership first: directions and blocking are master-level
    # facts that routes must already carry at upsert time.
    master_children = {}
    blocked_masters = set()
    route_directions = {}
    master_warnings = {}
    for raw in master_elements:
        osm_id = raw["osm_id"]
        children = [
            (member["source_index"], member["ref"])
            for member in raw.get("members", [])
            if member.get("type") == "relation"
        ]
        for member in raw.get("members", []):
            if member.get("type") != "relation":
                _note(
                    anomalies, "warning", STRAY_MEMBER,
                    f"non-relation member {member.get('type')} "
                    f"{member.get('ref')} inside master {osm_id}; ignored",
                    member.get("type"), member.get("ref"),
                )
                master_warnings.setdefault(osm_id, []).append("stray_member")
        missing = [ref for _, ref in children if ref not in route_elements]
        if missing:
            _note(
                anomalies, "fatal", CHILD_REF_MISSING,
                f"master {osm_id} references missing child route(s) "
                f"{missing}; master blocked",
                raw["osm_type"], osm_id,
            )
            blocked_masters.add(osm_id)
            continue
        master_children[osm_id] = children
        if len(children) == 2:
            for direction, (_, ref) in enumerate(children):
                route_directions[ref] = direction
        else:
            _note(
                anomalies, "warning", ASYMMETRIC_FROM_TO,
                f"master {osm_id} has {len(children)} children, not a "
                "clean directional pair; directions left unset",
                raw["osm_type"], osm_id,
            )

    # Duplicate master names across all (unblocked) masters.
    names = Counter(
        raw.get("tags", {}).get("name")
        for raw in master_elements
        if raw["osm_id"] not in blocked_masters
    )
    dup_names = {name for name, count in names.items() if count > 1 and name is not None}
    for raw in master_elements:
        osm_id = raw["osm_id"]
        if osm_id in blocked_masters:
            continue
        if raw.get("tags", {}).get("name") in dup_names:
            _note(
                anomalies, "warning", DUPLICATE_MASTER_NAME,
                f"master name {raw['tags']['name']!r} is shared; "
                "identity stays the OSM ID, never merged",
                raw["osm_type"], osm_id,
            )
            master_warnings.setdefault(osm_id, []).append("duplicate_master_name")

    route_plans = {}
    for osm_id, raw in route_elements.items():
        tags = raw.get("tags", {})
        platforms = _platform_refs(raw)
        quarantined = not platforms
        warned = quarantined
        if quarantined:
            _note(
                anomalies, "warning", NO_PLATFORM_SEQUENCE,
                f"route {osm_id} has no platform members; quarantined, "
                "not served",
                raw["osm_type"], osm_id,
            )
        seen = set()
        for _, ref in platforms:
            if ref in seen:
                warned = True
        route_plans[osm_id] = {
            "raw": raw,
            "fields": {
                "name": tags.get("name"),
                "from_text": tags.get("from"),
                "to_text": tags.get("to"),
                "direction": route_directions.get(osm_id),
                "verdict": "VALID_WITH_WARNING" if warned else "VALID",
                "quarantined": quarantined,
            },
        }

    master_plans = {}
    for raw in master_elements:
        osm_id = raw["osm_id"]
        if osm_id in blocked_masters:
            continue
        tags = raw.get("tags", {})
        warnings = master_warnings.get(osm_id, [])
        master_plans[osm_id] = {
            "raw": raw,
            "fields": {
                "name": tags.get("name"),
                "operator": tags.get("operator"),
                "network": tags.get("network"),
                "verdict": "VALID_WITH_WARNING" if warnings else "VALID",
                "warnings": warnings,
            },
            "children": master_children[osm_id],
        }

    # Duplicate platforms are stop-level facts needing the stop index;
    # they are detected at write time and appended there.
    return route_plans, master_plans, anomalies


def _write_stops(elements, run, counters):
    index = {}
    for raw in elements:
        tags = raw.get("tags", {})
        _upsert(
            Stop,
            {"osm_type": raw["osm_type"], "osm_id": raw["osm_id"]},
            {
                "name": tags.get("name"),
                "name_ml": tags.get("name:ml"),
                "lat": raw.get("lat"),
                "lon": raw.get("lon"),
                "tags": tags,
            },
            counters,
            "stop",
            run=run,
        )
        index[(raw["osm_type"], raw["osm_id"])] = Stop.objects.get(
            osm_type=raw["osm_type"], osm_id=raw["osm_id"]
        ).pk
    return index


def run_import(snapshot_dir, label):
    """Execute one import. Returns ImportResult(outcome, report dict).

    Outcome is "succeeded" or "aborted". File-level fatals abort
    before any write, so an aborted run leaves zero partial state.
    """
    snapshot_dir = Path(snapshot_dir)
    try:
        loaded = parse.load_snapshot(snapshot_dir)
    except parse.SnapshotError as exc:
        snapshot = OsmSnapshot.objects.create(
            label=label,
            recipe_ref=RECIPE_REF,
            source_timestamps=exc.partial.get("source_timestamps", {}),
            retrieved_at=timezone.now(),
            imported_at=timezone.now(),
        )
        run = ImportRun.objects.create(
            snapshot=snapshot,
            outcome=ImportRun.OUTCOME_ABORTED,
            finished_at=timezone.now(),
        )
        code = {
            parse.REQUIRED_FILE_MISSING: REQUIRED_FILE_MISSING,
            parse.INVALID_JSON: INVALID_JSON,
            parse.DUPLICATE_OSM_ID: DUPLICATE_OSM_ID,
        }[exc.code]
        ImportAnomaly.objects.create(
            run=run, severity="fatal", code=code, detail=exc.detail
        )
        payload = report_mod.build_report(
            snapshot, run, _empty_counters(), run.anomalies.all()
        )
        return ImportResult("aborted", payload)

    snapshot, _ = _snapshot_for(label, loaded, snapshot_dir)
    run = ImportRun.objects.create(snapshot=snapshot)
    for filename in loaded["missing_optional"]:
        ImportAnomaly.objects.create(
            run=run,
            severity="info",
            code=OPTIONAL_FILE_MISSING,
            detail=f"optional snapshot file absent: {filename}; continuing without it",
        )
    counters = _empty_counters()
    with transaction.atomic():
        # Each file carries exactly one citizen record type. Member
        # geometry shipped alongside (nodes/ways inside the routes
        # file) is expected payload, not data: it is skipped here,
        # never recorded, never flagged.
        stop_elements = [
            raw
            for raw in loaded["elements"]["osm_gcda_bus_stops.json"]
            if raw.get("osm_type") == "node"
        ]
        route_elements = [
            raw
            for raw in loaded["elements"]["osm_gcda_routes.json"]
            if raw.get("osm_type") == "relation"
        ]
        master_elements = [
            raw
            for raw in loaded["elements"]["osm_gcda_route_masters.json"]
            if raw.get("osm_type") == "relation"
        ]
        stop_index = _write_stops(stop_elements, run, counters)
        route_plans, master_plans, planned = _plan(
            route_elements, master_elements
        )

        route_rows = {}
        for osm_id, plan in route_plans.items():
            raw = plan["raw"]
            _upsert(
                Route,
                {"osm_type": raw["osm_type"], "osm_id": raw["osm_id"]},
                plan["fields"],
                counters,
                "route",
                run=run,
            )
            route = Route.objects.get(
                osm_type=raw["osm_type"], osm_id=raw["osm_id"]
            )
            route_rows[osm_id] = route
            desired = []
            seen_refs = set()
            position = 0
            for source_index, ref in _platform_refs(raw):
                stop_pk = stop_index.get(("node", ref))
                if stop_pk is None:
                    ImportAnomaly.objects.create(
                        run=run,
                        severity="fatal",
                        code=CHILD_REF_MISSING,
                        entity_osm_type="node",
                        entity_osm_id=ref,
                        detail=f"platform node {ref} of route {osm_id} "
                        "absent from the stop file; event excluded",
                    )
                    continue
                if ref in seen_refs:
                    ImportAnomaly.objects.create(
                        run=run,
                        severity="warning",
                        code=DUPLICATE_PLATFORM,
                        entity_osm_type=raw["osm_type"],
                        entity_osm_id=osm_id,
                        detail=f"platform node {ref} repeats in route "
                        f"{osm_id}; order kept, nothing deduped",
                    )
                seen_refs.add(ref)
                position += 1
                desired.append(
                    {
                        "stop": stop_pk,
                        "position": position,
                        "source_index": source_index,
                    }
                )
            _sync_memberships(
                route.stop_memberships,
                "stop",
                desired,
                counters,
                "route_stop_membership",
                run,
            )

        for anomaly in planned:
            ImportAnomaly.objects.create(
                run=run,
                severity=anomaly["severity"],
                code=anomaly["code"],
                entity_osm_type=anomaly["osm_type"],
                entity_osm_id=anomaly["osm_id"],
                detail=anomaly["detail"],
            )

        for osm_id, plan in master_plans.items():
            raw = plan["raw"]
            _upsert(
                RouteMaster,
                {"osm_type": raw["osm_type"], "osm_id": raw["osm_id"]},
                plan["fields"],
                counters,
                "route_master",
                run=run,
            )
            master = RouteMaster.objects.get(
                osm_type=raw["osm_type"], osm_id=raw["osm_id"]
            )
            desired = [
                {
                    "route": route_rows[ref].pk,
                    "position": position,
                    "source_index": source_index,
                }
                for position, (source_index, ref) in enumerate(
                    plan["children"], start=1
                )
            ]
            _sync_memberships(
                master.child_memberships,
                "route",
                desired,
                counters,
                "route_master_membership",
                run,
            )

        for osm_id, route in route_rows.items():
            if not route.master_memberships.exists():
                ImportAnomaly.objects.create(
                    run=run,
                    severity="warning",
                    code=ORPHAN_ROUTE,
                    entity_osm_type=route.osm_type,
                    entity_osm_id=osm_id,
                    detail=f"route {osm_id} is not referenced by any "
                    "master; kept out of the master-driven dataset",
                )

    run.outcome = ImportRun.OUTCOME_SUCCEEDED
    run.finished_at = timezone.now()
    run.save()
    payload = report_mod.build_report(
        snapshot, run, counters, run.anomalies.all()
    )
    return ImportResult("succeeded", payload)
