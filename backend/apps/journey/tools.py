"""Read-only agent tools over the application-owned dataset.

The model may call exactly these three functions. Each carries an
explicit JSON schema (MCP-compatible; no MCP server is stood up) and
returns plain JSON-serializable dicts. Nothing here writes: tools
read the canonical tables through the shared 003 query helpers
(``servable_routes``, ``order_routes``, ``routes_with_master_fields``)
plus the 006 endpoint-name annotations. Failures return
``{"ok": False, ...}`` to the loop, never an exception.
"""
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
}


def _stop_row(stop):
    return {
        "id": stop.id,
        "name": stop.name,
        "name_ml": stop.name_ml,
        "lat": stop.lat,
        "lon": stop.lon,
    }


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
