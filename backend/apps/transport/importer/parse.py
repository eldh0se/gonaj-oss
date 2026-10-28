"""Order-preserving Overpass JSON parsing.

Reads a retained snapshot directory only. This module performs no
network I/O by construction (no socket imports anywhere in the
importer package).
"""
import hashlib
import json
from pathlib import Path

REQUIRED_FILES = (
    "osm_gcda_routes.json",
    "osm_gcda_bus_stops.json",
    "osm_gcda_route_masters.json",
)
OPTIONAL_FILES = (
    "osm_gcda_bus_stations.json",
    "osm_gcda_route_members.json",
)

REQUIRED_FILE_MISSING = "REQUIRED_FILE_MISSING"
INVALID_JSON = "INVALID_JSON"
DUPLICATE_OSM_ID = "DUPLICATE_OSM_ID"


class SnapshotError(Exception):
    """File-level fatal: carries a stable code, detail, and whatever
    partial load state was salvageable."""

    def __init__(self, code, detail, partial=None):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.partial = partial or {}


def _read_elements(path, required):
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if required:
            raise SnapshotError(
                REQUIRED_FILE_MISSING,
                f"required snapshot file missing: {path.name}",
            )
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SnapshotError(
            INVALID_JSON, f"{path.name} is not valid JSON: {exc}"
        )
    elements = payload.get("elements", [])
    seen = set()
    for element in elements:
        key = (element.get("type"), element.get("id"))
        if key in seen:
            raise SnapshotError(
                DUPLICATE_OSM_ID,
                f"duplicate {(key[0], key[1])} inside {path.name}: "
                "extract is corrupt, refusing to merge",
            )
        seen.add(key)
    osm_base = (payload.get("osm3s") or {}).get("timestamp_osm_base")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "elements": [_normalize(raw) for raw in elements],
        "osm_base": osm_base,
        "sha256": digest,
    }


def _normalize(raw):
    item = {
        "osm_type": raw.get("type"),
        "osm_id": raw.get("id"),
        "tags": raw.get("tags") or {},
    }
    if raw.get("type") == "node":
        item["lat"] = raw.get("lat")
        item["lon"] = raw.get("lon")
    if raw.get("type") == "relation":
        item["members"] = [
            {
                "type": member.get("type"),
                "ref": member.get("ref"),
                "role": member.get("role") or "",
                "source_index": index,
            }
            for index, member in enumerate(raw.get("members") or [])
        ]
    return item


def load_snapshot(snapshot_dir):
    """Parse every snapshot file, preserving member order.

    Returns element records plus per-file hashes and source-state
    timestamps. Raises SnapshotError on any file-level fatal.
    """
    snapshot_dir = Path(snapshot_dir)
    elements = {}
    hashes = {}
    timestamps = {}
    missing_optional = []
    for filename in REQUIRED_FILES:
        parsed = _read_elements(snapshot_dir / filename, required=True)
        elements[filename] = parsed["elements"]
        hashes[filename] = parsed["sha256"]
        timestamps[filename] = parsed["osm_base"]
    for filename in OPTIONAL_FILES:
        parsed = _read_elements(snapshot_dir / filename, required=False)
        if parsed is None:
            missing_optional.append(filename)
            continue
        elements[filename] = parsed["elements"]
        hashes[filename] = parsed["sha256"]
        timestamps[filename] = parsed["osm_base"]
    return {
        "elements": elements,
        "hashes": hashes,
        "source_timestamps": timestamps,
        "missing_optional": missing_optional,
    }
