"""Read-only agent tools over the application-owned dataset.

The model may call exactly three functions. Each carries an
explicit JSON schema (MCP-compatible; no MCP server is stood up) and
returns plain JSON-serializable dicts. Nothing here writes: tools
read the canonical tables through the shared 003 query helpers
(``servable_routes``, ``order_routes``, ``routes_with_master_fields``)
plus the 006 endpoint-name annotations. Failures return
``{"ok": False, ...}`` to the loop, never an exception.

``search_places`` and ``find_routes_matrix`` are deterministic
place-grouping helpers for direct use (no model registration).
"""
import math
import re

from django.db.models import Q

from apps.transport.api.views import (
    MAX_BBOX_SPAN_DEGREES,
    order_routes,
    routes_with_endpoint_names,
    routes_with_master_fields,
    servable_routes,
)
from apps.transport.models import Route, RouteStopMembership, Stop

TOOL_SCHEMAS = {
    "search_stops": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Name fragment (case-insensitive containment over name/name_ml)",
            },
            "bbox": {
                "type": "string",
                "description": "Closed bounds as min_lon,min_lat,max_lon,max_lat. Never combined with query.",
            },
        },
        "required": [],
        "additionalProperties": False,
    },
    "find_routes": {
        "type": "object",
        "properties": {
            "from_stop_id": {
                "type": "integer",
                "description": "Boarding stop id",
            },
            "to_stop_id": {
                "type": "integer",
                "description": "Alighting stop id (must differ)",
            },
        },
        "required": ["from_stop_id", "to_stop_id"],
        "additionalProperties": False,
    },
    "get_route_detail": {
        "type": "object",
        "properties": {
            "route_id": {
                "type": "integer",
                "description": "Servable route id",
            },
        },
        "required": ["route_id"],
        "additionalProperties": False,
    },
    "search_places": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Place-name fragment; one end of the journey question.",
            },
            "bbox": {
                "type": "string",
                "description": "Closed bounds min_lon,min_lat,max_lon,max_lat for a map-derived end. Never combined with query.",
            },
        },
        "required": [],
        "additionalProperties": False,
    },
    "find_routes_matrix": {
        "type": "object",
        "properties": {
            "from_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Origin member stop ids (group members, nearest-end first).",
            },
            "to_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Destination member stop ids.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum pairs tested, nearest first. Defaults to the pair cap.",
            },
        },
        "required": ["from_ids", "to_ids"],
        "additionalProperties": False,
    },
    "distance_m": {
        "type": "object",
        "properties": {
            "lat1": {"type": "number"},
            "lon1": {"type": "number"},
            "lat2": {"type": "number"},
            "lon2": {"type": "number"},
        },
        "required": ["lat1", "lon1", "lat2", "lon2"],
        "additionalProperties": False,
    },
    "nearby_stops": {
        "type": "object",
        "properties": {
            "lat": {"type": "number"},
            "lon": {"type": "number"},
            "radius_m": {
                "type": "number",
                "description": "Search radius, default 500, maximum 2000.",
            },
        },
        "required": ["lat", "lon"],
        "additionalProperties": False,
    },
}

RESULT_LIMIT = 100


def to_openai_tools():
    """TOOL_SCHEMAS in the SDK function-calling shape."""
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": _TOOL_DESCRIPTIONS[name],
                "parameters": schema,
            },
        }
        for name, schema in TOOL_SCHEMAS.items()
    ]


_TOOL_DESCRIPTIONS = {
    "search_stops": "Find stops by name fragment or map area.",
    "find_routes": "Direct routes serving both stops in travelling order.",
    "get_route_detail": "One route with its ordered stops and evidence fields.",
    "search_places": "Group same-named stops into places with members and route hints.",
    "find_routes_matrix": "Direct routes for every origin/destination member pair.",
    "distance_m": "Haversine meters between two points.",
    "nearby_stops": "Stops around a point, nearest first.",
}


def _stop_row(stop):
    return {
        "id": stop.id,
        "name": stop.name,
        "name_ml": stop.name_ml,
        "lat": stop.lat,
        "lon": stop.lon,
    }


_TOKEN_SPLIT = re.compile(r"[^0-9a-z]+")


def _query_tokens(text):
    """Lowercase alphanumeric tokens of a search string."""
    return [
        token
        for token in _TOKEN_SPLIT.split(str(text or "").lower())
        if token
    ]


def _token_overlap_rows(text):
    """Stage-2 fallback: token-overlap rank over an icontains prefilter.

    Runs only when Stage-1 icontains finds nothing. Prefilters stops
    matching any query token (name or name_ml), ranks in Python by shared
    token count desc then name, id, and caps at ``RESULT_LIMIT``.
    SQLite-portable, no new dependencies.
    """
    wanted = set(_query_tokens(text))
    if not wanted:
        return []
    token_filter = Q()
    for token in wanted:
        token_filter |= Q(name__icontains=token) | Q(
            name_ml__icontains=token
        )
    scored = []
    for stop in Stop.objects.filter(token_filter).order_by("name", "id"):
        candidate = set(_query_tokens(stop.name)) | set(
            _query_tokens(stop.name_ml)
        )
        shared = len(wanted & candidate)
        if shared:
            scored.append((shared, stop.name or "", stop.id, stop))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [_stop_row(item[3]) for item in scored[:RESULT_LIMIT]]


def _parse_bbox(bbox):
    """Shared closed-bounds semantics with the 003 stops list."""
    try:
        parts = [v.strip() for v in str(bbox).split(",")]
        if len(parts) != 4 or any(not p for p in parts):
            raise ValueError
        min_lon, min_lat, max_lon, max_lat = (float(p) for p in parts)
    except (TypeError, ValueError, AttributeError):
        return None
    if (
        not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180)
        or not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90)
        or min_lon > max_lon
        or min_lat > max_lat
    ):
        return None
    return (min_lon, min_lat, max_lon, max_lat)


def search_stops(query=None, bbox=None):
    """Matching stops by name fragment or map area (read-only)."""
    has_query = query is not None and str(query).strip() != ""
    has_bbox = bbox is not None and str(bbox).strip() != ""
    if has_query and has_bbox:
        return {
            "ok": False,
            "error": "Search by stop name or by map area, not both at once.",
        }
    if has_bbox:
        bounds = _parse_bbox(bbox)
        if bounds is None:
            return {
                "ok": False,
                "error": "That map area does not look right. "
                "Give four coordinates as "
                "min_lon,min_lat,max_lon,max_lat.",
            }
        min_lon, min_lat, max_lon, max_lat = bounds
        if (
            max_lon - min_lon > MAX_BBOX_SPAN_DEGREES
            or max_lat - min_lat > MAX_BBOX_SPAN_DEGREES
        ):
            return {
                "ok": True,
                "status": "zoom_in",
                "stops": [],
                "detail": "That area is too large to list stops for. "
                "Please zoom in and try again.",
            }
        matches = (
            Stop.objects.filter(
                lon__gte=min_lon,
                lon__lte=max_lon,
                lat__gte=min_lat,
                lat__lte=max_lat,
            )
            .order_by("name", "id")[:RESULT_LIMIT]
        )
        rows = [_stop_row(s) for s in matches]
        if not rows:
            return {"ok": True, "status": "empty", "stops": []}
        return {"ok": True, "status": "ok", "stops": rows}
    if not has_query:
        return {
            "ok": False,
            "error": "Give a stop name fragment or a map area to search.",
        }
    text = str(query).strip()
    matches = (
        Stop.objects.filter(
            Q(name__icontains=text) | Q(name_ml__icontains=text)
        )
        .order_by("name", "id")[:RESULT_LIMIT]
    )
    rows = [_stop_row(s) for s in matches]
    if not rows:
        rows = _token_overlap_rows(text)
    if not rows:
        return {"ok": True, "status": "empty", "stops": []}
    return {"ok": True, "status": "ok", "stops": rows}


def find_routes(from_stop_id, to_stop_id):
    """Direct routes serving both stops in travelling order."""
    try:
        from_id = int(from_stop_id)
        to_id = int(to_stop_id)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "error": "Give two stop ids to check for a direct service.",
        }
    if from_id < 1 or to_id < 1 or from_id == to_id:
        return {
            "ok": False,
            "error": "Please choose two different stops to check. "
            "Pick an origin stop and a destination stop.",
        }
    if not Stop.objects.filter(pk=from_id).exists() or not Stop.objects.filter(
        pk=to_id
    ).exists():
        return {
            "ok": False,
            "error": "I could not find one of those stops. "
            "Please check the names and try again.",
        }
    routes = list(
        order_routes(
            routes_with_endpoint_names(
                routes_with_master_fields(servable_routes())
            .filter(stop_memberships__stop_id=from_id)
            .filter(stop_memberships__stop_id=to_id)
            )
        ).distinct()
    )
    if not routes:
        return {"ok": True, "routes": []}
    positions = {}
    for row in RouteStopMembership.objects.filter(
        route__in=[r.pk for r in routes],
        stop_id__in=(from_id, to_id),
    ).values("route_id", "stop_id", "position"):
        positions[(row["route_id"], row["stop_id"])] = row["position"]
    direct = []
    for route in routes:
        from_pos = positions.get((route.pk, from_id))
        to_pos = positions.get((route.pk, to_id))
        if from_pos is not None and to_pos is not None and from_pos < to_pos:
            direct.append(
                {
                    "id": route.id,
                    "name": route.name,
                    "origin": route.resolved_origin,
                    "destination": route.resolved_destination,
                    "operator": route.operator,
                    "network": route.network,
                    "evidence": f"/routes/{route.id}",
                }
            )
    return {"ok": True, "routes": direct}


def get_route_detail(route_id):
    """One servable route with ordered stops and evidence fields."""
    try:
        wanted = int(route_id)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "error": "Give a route id to look up.",
        }
    try:
        route = (
            routes_with_endpoint_names(
                routes_with_master_fields(servable_routes())
            )
            .distinct()
            .get(pk=wanted)
        )
    except (Route.DoesNotExist, Route.MultipleObjectsReturned, ValueError):
        return {
            "ok": False,
            "error": "I could not find that route. "
            "Please check the link and try again.",
        }
    memberships = (
        RouteStopMembership.objects.filter(route=route)
        .select_related("stop")
        .order_by("position")
    )
    positions = [m.position for m in memberships]
    first, last = (min(positions), max(positions)) if positions else (None, None)
    return {
        "ok": True,
        "route": {
            "id": route.id,
            "name": route.name,
            "origin": route.resolved_origin,
            "destination": route.resolved_destination,
            "operator": route.operator,
            "network": route.network,
            "evidence": f"/routes/{route.id}",
            "stops": [
                {
                    "stop": _stop_row(m.stop),
                    "position": m.position,
                    "is_origin": m.position == first,
                    "is_terminus": m.position == last,
                }
                for m in memberships
            ],
        },
    }


EARTH_RADIUS_M = 6371000.0
CLUSTER_RADIUS_M = 150.0
GROUP_ROUTES_CAP = 10


def _haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in meters (SQLite-portable, no PostGIS)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    inner = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(max(0.0, min(1.0, inner))))


def _normalized_place_name(name):
    return (name or "").strip().casefold()


def _cluster_rows(rows, radius_m=CLUSTER_RADIUS_M):
    """Single-linkage clusters preserving input order. Returns lists of rows."""
    remaining = list(rows)
    clusters = []
    while remaining:
        cluster = [remaining.pop(0)]
        changed = True
        while changed:
            changed = False
            rest = []
            for row in remaining:
                if any(
                    _haversine_m(
                        row["lat"], row["lon"], member["lat"], member["lon"]
                    )
                    <= radius_m
                    for member in cluster
                ):
                    cluster.append(row)
                    changed = True
                else:
                    rest.append(row)
            remaining = rest
        clusters.append(cluster)
    return clusters


def _group_routes(stop_ids):
    """Distinct servable routes serving any of the stops, ordered by (name, id)."""
    if not stop_ids:
        return []
    routes = list(
        order_routes(
            routes_with_endpoint_names(
                routes_with_master_fields(servable_routes()).filter(
                    stop_memberships__stop_id__in=list(stop_ids)
                )
            )
        ).distinct()
    )
    routes.sort(key=lambda route: (route.name or "", route.pk))
    return routes


def _place_group(normalized, index, members):
    lats = [m["lat"] for m in members]
    lons = [m["lon"] for m in members]
    spread = 0.0
    for left in range(len(members)):
        for right in range(left + 1, len(members)):
            distance = _haversine_m(
                members[left]["lat"],
                members[left]["lon"],
                members[right]["lat"],
                members[right]["lon"],
            )
            if distance > spread:
                spread = distance
    routes = _group_routes([m["id"] for m in members])
    return {
        "key": f"{normalized}#{index}",
        "label": members[0]["name"],
        "center": {
            "lat": sum(lats) / len(lats),
            "lon": sum(lons) / len(lons),
        },
        "bbox": {
            "min_lat": min(lats),
            "min_lon": min(lons),
            "max_lat": max(lats),
            "max_lon": max(lons),
        },
        "spread_m": spread,
        "members": [
            {
                "id": m["id"],
                "name": m["name"],
                "lat": m["lat"],
                "lon": m["lon"],
            }
            for m in members
        ],
        "route_count": len(routes),
        "routes": [
            {"id": route.id, "name": route.name}
            for route in routes[:GROUP_ROUTES_CAP]
        ],
    }


def search_places(query=None, bbox=None):
    """Group matching stops into places (read-only).

    Same exactly-one-of ``query``/``bbox`` and ``zoom_in``/``empty``
    semantics as :func:`search_stops`; at most ``RESULT_LIMIT`` stops
    enter grouping.
    """
    has_query = query is not None and str(query).strip() != ""
    has_bbox = bbox is not None and str(bbox).strip() != ""
    if has_query and has_bbox:
        return {
            "ok": False,
            "error": "Search by stop name or by map area, not both at once.",
        }
    if has_bbox:
        bounds = _parse_bbox(bbox)
        if bounds is None:
            return {
                "ok": False,
                "error": "That map area does not look right. "
                "Give four coordinates as "
                "min_lon,min_lat,max_lon,max_lat.",
            }
        min_lon, min_lat, max_lon, max_lat = bounds
        if (
            max_lon - min_lon > MAX_BBOX_SPAN_DEGREES
            or max_lat - min_lat > MAX_BBOX_SPAN_DEGREES
        ):
            return {
                "ok": True,
                "status": "zoom_in",
                "groups": [],
                "detail": "That area is too large to list stops for. "
                "Please zoom in and try again.",
            }
        matches = (
            Stop.objects.filter(
                lon__gte=min_lon,
                lon__lte=max_lon,
                lat__gte=min_lat,
                lat__lte=max_lat,
            )
            .order_by("name", "id")[:RESULT_LIMIT]
        )
    elif has_query:
        text = str(query).strip()
        matches = (
            Stop.objects.filter(
                Q(name__icontains=text) | Q(name_ml__icontains=text)
            )
            .exclude(name__isnull=True)
            .exclude(name__exact="")
            .order_by("name", "id")[:RESULT_LIMIT]
        )
    else:
        return {
            "ok": False,
            "error": "Give a stop name fragment or a map area to search.",
        }
    rows = [_stop_row(stop) for stop in matches]
    if not rows and has_query:
        rows = _token_overlap_rows(text)
    if not rows:
        return {"ok": True, "status": "empty", "groups": []}
    buckets = {}
    for row in rows:
        buckets.setdefault(_normalized_place_name(row["name"]), []).append(row)
    groups = []
    for normalized in sorted(buckets):
        for index, cluster in enumerate(
            _cluster_rows(buckets[normalized]), start=1
        ):
            groups.append(_place_group(normalized, index, cluster))
    return {"ok": True, "status": "ok", "groups": groups}


def _direct_pair_routes(from_stop_id, to_stop_id):
    """Direct servable routes for one ordered pair (shared pair logic)."""
    routes = list(
        order_routes(
            routes_with_endpoint_names(
                routes_with_master_fields(servable_routes())
            )
            .filter(stop_memberships__stop_id=from_stop_id)
            .filter(stop_memberships__stop_id=to_stop_id)
        ).distinct()
    )
    if not routes:
        return []
    positions = {}
    for row in RouteStopMembership.objects.filter(
        route__in=[route.pk for route in routes],
        stop_id__in=(from_stop_id, to_stop_id),
    ).values("route_id", "stop_id", "position"):
        positions[(row["route_id"], row["stop_id"])] = row["position"]
    direct = []
    for route in routes:
        from_pos = positions.get((route.pk, from_stop_id))
        to_pos = positions.get((route.pk, to_stop_id))
        if (
            from_pos is not None
            and to_pos is not None
            and from_pos < to_pos
        ):
            direct.append(
                {
                    "id": route.id,
                    "name": route.name,
                    "evidence": f"/routes/{route.id}",
                }
            )
    return direct


MATRIX_PAIR_CAP = 200


def find_routes_matrix(from_ids, to_ids, limit=MATRIX_PAIR_CAP):
    """Direct routes for ordered pairs, nearest first (read-only).

    Equal-id pairs are skipped; unknown ids error like
    :func:`find_routes`. Only pairs with at least one travelling-order
    direct route appear, so opposite-direction pairs drop out. Pairs are
    tested in ascending minimum member-to-member haversine order and at
    most ``limit`` pairs are tested; ``truncated`` reports whether pairs
    went untested, with their destination ids in ``untested_to_ids``.
    """
    try:
        sources = [int(value) for value in (from_ids or [])]
        targets = [int(value) for value in (to_ids or [])]
    except (TypeError, ValueError):
        return {
            "ok": False,
            "error": "Give stop id lists to check for direct services.",
        }
    if any(value < 1 for value in sources + targets):
        return {
            "ok": False,
            "error": "Stop ids must be positive integers.",
        }
    try:
        cap = int(limit)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "error": "Give a positive pair limit.",
        }
    if cap < 1:
        return {
            "ok": False,
            "error": "Give a positive pair limit.",
        }
    known = {
        row["id"]: (row["lat"], row["lon"])
        for row in Stop.objects.filter(
            pk__in=set(sources) | set(targets)
        ).values("id", "lat", "lon")
    }
    if len(known) != len(set(sources) | set(targets)):
        return {
            "ok": False,
            "error": "I could not find one of those stops. "
            "Please check the names and try again.",
        }
    ordered = []
    for from_id in sources:
        for to_id in targets:
            if from_id == to_id:
                continue
            from_lat, from_lon = known[from_id]
            to_lat, to_lon = known[to_id]
            coords = (from_lat, from_lon, to_lat, to_lon)
            if any(value is None for value in coords):
                gap = float("inf")
            else:
                gap = _haversine_m(from_lat, from_lon, to_lat, to_lon)
            ordered.append((gap, from_id, to_id))
    ordered.sort(key=lambda item: (item[0], item[1], item[2]))
    tested = ordered[:cap]
    untested = ordered[cap:]
    pairs = []
    for _, from_id, to_id in tested:
        routes = _direct_pair_routes(from_id, to_id)
        if routes:
            pairs.append(
                {
                    "from_stop_id": from_id,
                    "to_stop_id": to_id,
                    "routes": routes,
                }
            )
    untested_from_ids = []
    untested_to_ids = []
    for _, from_id, to_id in untested:
        if from_id not in untested_from_ids:
            untested_from_ids.append(from_id)
        if to_id not in untested_to_ids:
            untested_to_ids.append(to_id)
    return {
        "ok": True,
        "pairs": pairs,
        "truncated": bool(untested),
        "untested_from_ids": untested_from_ids,
        "untested_to_ids": untested_to_ids,
    }


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def distance_m(lat1, lon1, lat2, lon2):
    """Haversine meters between two points (read-only, SQLite-portable)."""
    coords = (lat1, lon1, lat2, lon2)
    if not all(_is_finite_number(value) for value in coords):
        return {
            "ok": False,
            "error": "Give four numbers as lat1, lon1, lat2, lon2.",
        }
    if not (
        -90 <= lat1 <= 90
        and -90 <= lat2 <= 90
        and -180 <= lon1 <= 180
        and -180 <= lon2 <= 180
    ):
        return {
            "ok": False,
            "error": "Latitudes stay within -90 to 90, "
            "longitudes within -180 to 180.",
        }
    return {
        "ok": True,
        "distance_m": _haversine_m(
            float(lat1), float(lon1), float(lat2), float(lon2)
        ),
    }


NEARBY_STOPS_DEFAULT_RADIUS_M = 500.0
NEARBY_STOPS_MAX_RADIUS_M = 2000.0


def nearby_stops(lat, lon, radius_m=NEARBY_STOPS_DEFAULT_RADIUS_M):
    """Stops around a point, nearest first (read-only, SQLite-portable).

    DB bbox prefilter plus pure-Python haversine filtering; at most
    ``RESULT_LIMIT`` stops, ordered by ascending ``distance_m``.
    """
    if not _is_finite_number(lat) or not _is_finite_number(lon):
        return {
            "ok": False,
            "error": "Give numbers for lat and lon.",
        }
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return {
            "ok": False,
            "error": "Latitudes stay within -90 to 90, "
            "longitudes within -180 to 180.",
        }
    if not _is_finite_number(radius_m) or not (
        0 < radius_m <= NEARBY_STOPS_MAX_RADIUS_M
    ):
        return {
            "ok": False,
            "error": "Search within 0 to 2000 meters of the point.",
        }
    half_lat = radius_m / 111320.0
    half_lon = radius_m / (
        111320.0 * max(math.cos(math.radians(lat)), 1e-6)
    )
    rows = [
        _stop_row(stop)
        for stop in Stop.objects.filter(
            lat__gte=lat - half_lat,
            lat__lte=lat + half_lat,
            lon__gte=lon - half_lon,
            lon__lte=lon + half_lon,
        ).order_by("name", "id")
    ]
    measured = []
    for row in rows:
        gap = _haversine_m(lat, lon, row["lat"], row["lon"])
        if gap <= radius_m:
            measured.append((gap, row))
    measured.sort(key=lambda item: (item[0], item[1]["id"]))
    return {
        "ok": True,
        "stops": [
            {
                "id": row["id"],
                "name": row["name"],
                "lat": row["lat"],
                "lon": row["lon"],
                "distance_m": gap,
            }
            for gap, row in measured[:RESULT_LIMIT]
        ],
    }
