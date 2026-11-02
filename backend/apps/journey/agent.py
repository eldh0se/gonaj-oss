"""Tool loop, server-side verifier, refusal/disambiguation, fallback.

The model is the eloquence layer, never the source of truth: every
cited route is re-checked against the dataset (servable route, both
resolved stops in travelling order) before anything reaches the
passenger, and any time-, duration-, frequency-, or transfer-shaped
content fails verification with one repair attempt and then refusal.
"""
import json
import logging
import re
import time

from django.conf import settings

from apps.journey import tools
from apps.journey.providers import meta as provider
from apps.transport.models import Stop

logger = logging.getLogger(__name__)

MAX_TOOL_TURNS = 4
MAX_RESOLVE_ATTEMPTS = 3


def _short(text, limit=1000):
    """Truncate model content for debug logs without losing the decision."""
    text = text or ""
    if len(text) > limit:
        return text[:limit] + f"...[truncated {len(text) - limit} chars]"
    return text


_JOURNEY_LOG_LOGGERS = ("apps.journey.agent", "apps.journey.tools")

_active_request_log_buffer = None


class _RequestLogBuffer(logging.Handler):
    """Per-request log buffer: replay all on failure, audit only on success.

    Held for the duration of one run_journey call while journey-logger
    propagation is muted, so the console stays quiet on the success path
    (the matrix / walk-mate fan-out can reach tens of thousands of lines)
    while refuse and disambiguation paths replay the full trace for
    diagnosis. INFO and above (the audit line, exceptions) always replay;
    DEBUG replays only when the outcome is kept.
    """

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)


def _attach_request_log_buffer():
    """Mute journey loggers for one request; returns state for release.

    Also drops a stale buffer left by an earlier request that never
    reached its funnel, so logging can never wedge silent.
    """
    global _active_request_log_buffer
    if _active_request_log_buffer is not None:
        _release_request_log_buffer(keep=False)
    state = []
    for name in _JOURNEY_LOG_LOGGERS:
        journey_logger = logging.getLogger(name)
        buffer = _RequestLogBuffer()
        journey_logger.addHandler(buffer)
        state.append((journey_logger, buffer, journey_logger.propagate))
        journey_logger.propagate = False
    _active_request_log_buffer = state
    return state


def _release_request_log_buffer(keep):
    """Detach request buffers and replay them.

    INFO and above (the audit line, exceptions) always replay; DEBUG
    replays only when keep is True (refuse / disambiguate outcomes).
    """
    global _active_request_log_buffer
    state, _active_request_log_buffer = _active_request_log_buffer, None
    if not state:
        return
    for journey_logger, buffer, saved_propagate in state:
        try:
            journey_logger.removeHandler(buffer)
        except ValueError:
            pass
        journey_logger.propagate = saved_propagate
    root_logger = logging.getLogger()
    for _, buffer, _ in state:
        for record in buffer.records:
            if keep or record.levelno >= logging.INFO:
                root_logger.handle(record)

SYSTEM_PROMPT = (
    "You are the Gonaj journey helper. Answer in everyday language "
    "about direct bus services only, using the read-only tools. "
    "Resolve both ends to place groups with search_places first, then "
    "test member pairs with find_routes_matrix, and cite every route "
    "from a get_route_detail result as /routes/:id with a walk-distance "
    "note. A route counts only when the boarding stop comes before the "
    "alighting stop on it. Same names do not mean the same stop; nearby "
    "stops within walking distance count as reachable — state the exact "
    "stop plus nearby stops with walk distances. "
    "Never mention schedules, departure or arrival times, durations, "
    "frequencies, or transfers. If no direct service is known, or a "
    "place cannot be found, say so plainly and invent nothing."
)

REPAIR_NUDGE = (
    "Your draft could not be verified: it cited an unknown route or "
    "contained times, durations, or transfer instructions. Answer "
    "again using only verified direct connections from the tool "
    "results, citing each route as /routes/:id, with no times, "
    "durations, frequencies, or transfers — or say plainly that no "
    "direct service is known."
)

_ROUTE_REF = re.compile(r"/routes/(\d+)")
_FORBIDDEN_SHAPED = re.compile(
    r"\b\d{1,2}:\d{2}\b"  # clock times
    r"|\b\d+\s*(minutes?|mins?|hours?|hrs?|seconds?)\b"  # durations
    r"|\b\d+\s*(am|pm)\b|\bo'?clock\b"  # dayparts
    r"|\b(duration|frequency|frequencies|timetable|schedule|scheduled|platform)\b"
    r"|\b(transfer|transfers|interchange|layover|connecting)\b"
    r"|\bchange\s+(at|to|trains|buses|onto)\b",
    re.IGNORECASE,
)

_TOOL_FUNCTIONS = {
    "search_stops": tools.search_stops,
    "find_routes": tools.find_routes,
    "get_route_detail": tools.get_route_detail,
    "search_places": tools.search_places,
    "find_routes_matrix": tools.find_routes_matrix,
    "distance_m": tools.distance_m,
    "nearby_stops": tools.nearby_stops,
}

_ASK_AGAIN = (
    "Please ask me a journey question, for example "
    "'How do I get from Ernakulam South to Fort Kochi?'"
)
_CANNOT_ANSWER = (
    "The journey helper cannot answer right now. "
    "Please try again in a little while, or browse the routes directly."
)
_NO_DIRECT = (
    "I could not find a direct service between those stops."
)
_UNKNOWN_PLACE = (
    "I could not find that place. "
    "Please check the spelling or pick a stop from the map."
)
_UNVERIFIABLE = (
    "I cannot verify a direct service for that question, "
    "so I cannot answer it. "
    "Please try asking with the two stop names, or browse the map."
)


_UNMATCHED_PICK = (
    "I could not match that choice to the stops I listed. "
    "Please choose one of the listed stops, or rephrase your "
    "journey question with the two stop names."
)

_ORDINAL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
}

_FRESH_QUESTION = re.compile(
    r"\b(how|what|where|which|from|to|route|routes|bus|buses|"
    r"get|going|reach|take|find|there)\b|\?",
    re.IGNORECASE,
)

_FROM_TO = re.compile(r"from\s+(.+?)\s+to\s+(.+?)(?:[?.!]|$)", re.IGNORECASE)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _candidate_detail_from_row(row):
    if row.get("name_ml"):
        return row["name_ml"]
    try:
        return f"{float(row.get('lat')):.4f},{float(row.get('lon')):.4f}"
    except (TypeError, ValueError):
        return ""


def _candidate_detail(stop):
    if getattr(stop, "name_ml", None):
        return stop.name_ml
    try:
        return f"{stop.lat:.4f},{stop.lon:.4f}"
    except (TypeError, ValueError, AttributeError):
        return ""


def _candidate_entry(stop_id, name, detail, lat=None, lon=None):
    entry = {"id": stop_id, "name": name}
    if detail:
        entry["detail"] = detail
    if lat is not None and lon is not None:
        entry["lat"] = lat
        entry["lon"] = lon
    return entry


def _match_selection_text(question, stops_by_id):
    """Map typed text to one offered candidate.

    Returns ("id", stop_id) for an unambiguous pick (case-insensitive
    exact name/name_ml match, or a 1-based position/ordinal matching
    exactly one slot entry), ("multi",) when the text matches several
    candidates, or ("zero",) when it matches none.
    """
    text = (question or "").strip().lower().rstrip("?.!. ")
    ids = list(stops_by_id)
    if not text:
        return ("zero",)
    if text.isdigit():
        index = int(text) - 1
        if 0 <= index < len(ids):
            return ("id", ids[index])
        return ("zero",)
    if text in _ORDINAL_WORDS:
        index = _ORDINAL_WORDS[text] - 1
        if 0 <= index < len(ids):
            return ("id", ids[index])
        return ("zero",)
    matches = [
        sid
        for sid, stop in stops_by_id.items()
        if (stop.name or "").lower() == text
        or (getattr(stop, "name_ml", None) or "").lower() == text
    ]
    if len(matches) == 1:
        return ("id", matches[0])
    return ("multi",) if matches else ("zero",)


def _resolve_selection(context, question):
    """Classify a follow-up carrying selection state (no model needed).

    Returns one of:
    ("none",) — no selection keys; run the legacy model loop.
    ("invalid",) — selection keys present but unusable; refuse safely.
    ("fresh",) — a new journey question; drop stale context, run legacy loop.
    ("full", from_id, to_id) — both ends known; answer directly.
    ("partial", known_slot, known_id, remaining_slot, remaining_ids, slots)
      — one end picked; prompt the remaining end. remaining_ids may be []
      when undiscoverable (the caller derives them from the question).
    """
    if not isinstance(context, dict):
        return ("none",)
    cands = [
        c for c in (context.get("candidate_stop_ids") or []) if _is_int(c)
    ]
    selected = context.get("selected_stop_id")
    slot = context.get("slot")
    resolved = context.get("resolved")
    slots = context.get("slots")
    has_keys = (
        bool(cands)
        or selected is not None
        or slot is not None
        or isinstance(resolved, dict)
        or isinstance(slots, dict)
    )
    if not has_keys:
        return ("none",)
    if not cands:
        return ("invalid",)
    by_id = Stop.objects.filter(pk__in=cands).in_bulk()
    ordered = {cid: by_id[cid] for cid in cands if cid in by_id}
    if selected is not None:
        if selected not in ordered:
            return ("invalid",)
    elif slot not in ("from", "to"):
        # Legacy shape ({candidate_stop_ids} only, no slot): the model
        # loop stays compatible when the reply names exactly one offered
        # candidate; otherwise the reply matches nothing and refuses safely.
        if _match_selection_text(question, ordered)[0] != "id":
            return ("invalid",)
        return ("none",)
    else:
        outcome = _match_selection_text(question, ordered)
        if outcome[0] != "id":
            if _FRESH_QUESTION.search(question or ""):
                return ("fresh",)
            return ("invalid",)
        selected = outcome[1]
    if slot not in ("from", "to"):
        return ("invalid",)
    if isinstance(resolved, dict):
        resolved_id = resolved.get("id")
        if not _is_int(resolved_id):
            return ("invalid",)
        if slot == "from":
            return ("full", selected, resolved_id)
        return ("full", resolved_id, selected)
    remaining = "to" if slot == "from" else "from"
    remaining_ids = []
    if isinstance(slots, dict):
        remaining_ids = [
            c for c in (slots.get(remaining + "_ids") or []) if _is_int(c)
        ]
    return ("partial", slot, selected, remaining, remaining_ids, slots)


def _selection_meta(latency_ms):
    """Local-selection meta: outage fallback shape plus a resolution key."""
    meta = _meta(latency_ms, fallback=True)
    meta["resolution"] = "selection"
    return meta


UNKNOWN_OPERATOR = "Other services"


def _rank_pairs(pairs, operators=None, names=None):
    """Group verified pairs by operator; order (stop_count, route id).

    Pure ranking over verified route pairs (no model): each pair is
    ``{"route_id", "from_id", "to_id"}``. Returns
    ``(groups, by_id)`` where ``by_id`` maps route ids to their
    verified ``(route, from_id, to_id, from_name, to_name)`` tuples.
    Unknown routes are skipped; ``operators``/``names`` override the
    annotated values (used by tests).
    """
    operators = operators or {}
    names = names or {}
    grouped = {}
    order = []
    by_id = {}
    for pair in pairs or []:
        route_id = (pair or {}).get("route_id")
        from_id = (pair or {}).get("from_id")
        to_id = (pair or {}).get("to_id")
        detail = tools.get_route_detail(route_id)
        if not detail.get("ok"):
            continue
        route = detail["route"]
        if route_id in operators:
            operator = operators[route_id]
        else:
            operator = route.get("operator")
        group = operator or UNKNOWN_OPERATOR
        from_name = names.get(
            from_id, _stop_name(from_id) if from_id is not None else None
        ) or ""
        to_name = names.get(
            to_id, _stop_name(to_id) if to_id is not None else None
        ) or ""
        stops = route.get("stops") or []
        option = {
            "route": {
                "id": route["id"],
                "name": route["name"],
                "evidence": f"/routes/{route['id']}",
            },
            "boarding_stop": {"id": from_id, "name": from_name},
            "alighting_stop": {"id": to_id, "name": to_name},
            "stop_count": len(stops),
            "also_nearby_boarding": (pair or {}).get("mates_from") or [],
            "also_nearby": (pair or {}).get("mates_to") or [],
            "overflow_nearby_boarding": (pair or {}).get("overflow_from")
            or 0,
            "overflow_nearby": (pair or {}).get("overflow_to") or 0,
        }
        origin = route.get("origin") or ""
        if from_name:
            hint = f"Board at {from_name}"
            if origin and origin != from_name:
                hint = f"{hint} ({origin})"
            option["boarding_hint"] = hint
        if group not in grouped:
            grouped[group] = []
            order.append(group)
        grouped[group].append(option)
        by_id[route_id] = (route, from_id, to_id, from_name, to_name)
    groups = []
    for group in sorted(order, key=lambda g: (g == UNKNOWN_OPERATOR, g)):
        options = sorted(
            grouped[group],
            key=lambda o: (o["stop_count"], o["route"]["id"]),
        )
        groups.append({"operator": group, "options": options})
    return groups, by_id


def rank_pairs(pairs, operators=None, names=None, destinations=None):
    """Rank verified pairs into operator groups with answer prose.

    ``destinations`` is a precomputed reachable-member list of
    ``{"stop", "evidence"}`` entries; only the first five are returned,
    with overflow counted in the prose. Pure function (no model).
    """
    groups, _by_id = _rank_pairs(pairs, operators, names)
    shown = list(destinations or [])[:5]
    extra = len(destinations or []) - len(shown)
    if len(groups) == 1 and len(groups[0]["options"]) == 1 and extra <= 0:
        option = groups[0]["options"][0] if groups else None
        if option is None:
            answer = ""
        else:
            answer = (
                f"Take the {option['route']['name'] or 'direct'} service "
                f"from {option['boarding_stop']['name']} "
                f"to {option['alighting_stop']['name']}."
            ) + _walk_note(
                option["boarding_stop"]["name"],
                option["also_nearby_boarding"],
                option["overflow_nearby_boarding"],
            ) + _walk_note(
                option["alighting_stop"]["name"],
                option["also_nearby"],
                option["overflow_nearby"],
            )
    else:
        sentences = []
        for group in groups:
            for option in group["options"]:
                sentences.append(
                    f"{group['operator']}: Take the "
                    f"{option['route']['name'] or 'direct'} service "
                    f"from {option['boarding_stop']['name']} "
                    f"to {option['alighting_stop']['name']}, "
                    f"see {option['route']['evidence']}."
                    + _walk_note(
                        option["boarding_stop"]["name"],
                        option["also_nearby_boarding"],
                        option["overflow_nearby_boarding"],
                    )
                    + _walk_note(
                        option["alighting_stop"]["name"],
                        option["also_nearby"],
                        option["overflow_nearby"],
                    )
                )
        answer = " ".join(sentences)
    if extra > 0:
        answer = (
            f"{answer} Plus {extra} more drop-off options "
            "at this place.".strip()
        )
    return {
        "groups": groups,
        "destinations": shown,
        "answer": answer,
    }


def _disambiguation_context(question, searches):
    """Enriched prompt metadata from tool searches; None when undeterminable.

    Assigns each search to a journey end via the from/to question shape:
    one ambiguous end plus a resolved other end returns a single-end
    payload with slot/resolved/offered_ids/detail; two ambiguous ends
    return slots/surviving_context with the origin side prompted first.
    """
    groups = []
    for args, result in searches:
        if not isinstance(args, dict) or not result.get("ok"):
            continue
        stops = result.get("stops") or []
        if stops:
            groups.append(((args.get("query") or ""), stops))
    if not groups:
        return None
    match = _FROM_TO.search(question or "")
    if not match:
        return None
    parts = {"from": match.group(1).lower(), "to": match.group(2).lower()}
    ambiguous = {}
    resolved = {}
    for query, stops in groups:
        query_text = query.lower()
        end = None
        for candidate in ("from", "to"):
            if query_text and query_text in parts[candidate]:
                end = candidate
                break
        if end is None:
            return None
        if len(stops) == 1:
            resolved.setdefault(end, stops[0])
        else:
            ambiguous.setdefault(end, stops)
    if not ambiguous:
        return None
    if len(ambiguous) == 1:
        slot = next(iter(ambiguous))
        stops = ambiguous[slot]
        payload = {
            "status": "disambiguate",
            "message": "I found more than one stop with that "
            "name. Which one did you mean?",
            "candidates": [
                _candidate_entry(
                    stop["id"],
                    stop["name"],
                    _candidate_detail_from_row(stop),
                    stop.get("lat"),
                    stop.get("lon"),
                )
                for stop in stops
            ],
            "slot": slot,
            "offered_ids": [stop["id"] for stop in stops],
        }
        other = "to" if slot == "from" else "from"
        if other in resolved:
            payload["resolved"] = {
                "id": resolved[other]["id"],
                "name": resolved[other]["name"],
            }
        return payload
    first, second = "from", "to"
    if first not in ambiguous:
        first, second = second, first
    stops = ambiguous[first]
    return {
        "status": "disambiguate",
        "message": "I found more than one stop at each end. "
        "First, which origin did you mean?",
        "candidates": [
            _candidate_entry(
                stop["id"],
                stop["name"],
                _candidate_detail_from_row(stop),
                stop.get("lat"),
                stop.get("lon"),
            )
            for stop in stops
        ],
        "slot": first,
        "offered_ids": [stop["id"] for stop in stops],
        "slots": {
            "from_ids": [stop["id"] for stop in ambiguous.get("from", [])],
            "to_ids": [stop["id"] for stop in ambiguous.get("to", [])],
        },
        "surviving_context": {
            "other_end": second,
            "other_end_ids": [
                stop["id"] for stop in ambiguous.get(second, [])
            ],
        },
    }


def _meta(latency_ms, fallback=False):
    if fallback:
        return {
            "model": "none",
            "provider": "local-fallback",
            "latency_ms": latency_ms,
        }
    return {
        "model": getattr(settings, "JOURNEY_MODEL", "muse-spark-1.3"),
        "provider": getattr(
            settings, "JOURNEY_MODEL_PROVIDER", "meta"
        ),
        "latency_ms": latency_ms,
    }


def _log(model, provider_name, latency_ms, tools_used):
    logger.info(
        "journey model=%s provider=%s latency_ms=%d tools_used=%s",
        model,
        provider_name,
        latency_ms,
        ",".join(tools_used),
    )


def _clean_history(history):
    turns = []
    for turn in history or []:
        if not isinstance(turn, dict):
            continue
        if turn.get("role") not in ("user", "assistant"):
            continue
        content = turn.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        turns.append({"role": turn["role"], "content": content})
    return turns[-6:]


def _validate_tool_args(name, args):
    """Reject arguments outside the tool schema (never executed)."""
    if not isinstance(args, dict):
        return None
    schema = tools.TOOL_SCHEMAS[name]
    allowed = set(schema["properties"])
    if any(key not in allowed for key in args):
        return None
    for key in schema.get("required", []):
        if key not in args:
            return None
    if name in ("search_stops", "search_places"):
        for key in ("query", "bbox"):
            if key in args and not isinstance(args[key], str):
                return None
        if "exclude_ids" in args:
            ids = args["exclude_ids"]
            if not isinstance(ids, list) or any(
                not _is_int(value) or value < 1 for value in ids
            ):
                return None
    elif name == "find_routes_matrix":
        for key in ("from_ids", "to_ids"):
            ids = args.get(key)
            if (
                not isinstance(ids, list)
                or not ids
                or any(not _is_int(value) or value < 1 for value in ids)
            ):
                return None
        if "limit" in args:
            limit = args["limit"]
            if not _is_int(limit) or limit < 1:
                return None
    elif name in ("distance_m", "nearby_stops"):
        numeric_keys = (
            ("lat1", "lon1", "lat2", "lon2")
            if name == "distance_m"
            else ("lat", "lon")
        )
        for key in numeric_keys:
            value = args.get(key)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
            ):
                return None
        if name == "distance_m":
            lats = (args["lat1"], args["lat2"])
            lons = (args["lon1"], args["lon2"])
        else:
            lats = (args["lat"],)
            lons = (args["lon"],)
            if "radius_m" in args:
                radius = args["radius_m"]
                if (
                    not isinstance(radius, (int, float))
                    or isinstance(radius, bool)
                    or not (
                        0
                        < radius
                        <= tools.NEARBY_STOPS_MAX_RADIUS_M
                    )
                ):
                    return None
        if any(abs(v) > 90 for v in lats) or any(abs(v) > 180 for v in lons):
            return None
    else:
        for key in ("from_stop_id", "to_stop_id", "route_id"):
            if key in args and (
                not isinstance(args[key], int) or isinstance(args[key], bool)
            ):
                return None
    return args


def execute_tool(name, args, tracker):
    """Run one model-requested tool call, recording it for the audit log."""
    tracker["tools_used"].append(name)
    logger.debug("journey agent model requested tool %s args=%r", name, args)
    validated = _validate_tool_args(name, args) if name in _TOOL_FUNCTIONS else None
    if validated is None:
        logger.debug("journey agent tool %s rejected by validator", name)
        return {
            "ok": False,
            "error": "That tool call did not look right, so it was not run.",
        }
    try:
        result = _TOOL_FUNCTIONS[name](**validated)
    except Exception:
        logger.exception("journey tool %s failed", name)
        return {
            "ok": False,
            "error": "That lookup failed. Please carry on without it.",
        }
    tracker["calls"].append((name, validated, result))
    if name == "find_routes" and result.get("ok"):
        pair = (validated["from_stop_id"], validated["to_stop_id"])
        for row in result.get("routes", []):
            tracker["findings"][row["id"]] = pair
    if name == "find_routes_matrix" and result.get("ok"):
        for pair in result.get("pairs", []):
            found = (pair["from_stop_id"], pair["to_stop_id"])
            for row in pair.get("routes", []):
                tracker["findings"][row["id"]] = found
    if name == "search_stops" and result.get("ok"):
        tracker["searches"].append((validated, result))
    return result


def _assistant_entry(message):
    calls = []
    for call in getattr(message, "tool_calls", None) or []:
        function = getattr(call, "function", None)
        calls.append(
            {
                "id": getattr(call, "id", ""),
                "type": "function",
                "function": {
                    "name": getattr(function, "name", ""),
                    "arguments": getattr(function, "arguments", "{}"),
                },
            }
        )
    return {
        "role": "assistant",
        "content": getattr(message, "content", None),
        "tool_calls": calls,
    }


def _model_turn(messages):
    response = provider.complete_with_tools(
        model=getattr(settings, "JOURNEY_MODEL", "muse-spark-1.3"),
        messages=messages,
        tools=tools.to_openai_tools(),
    )
    message = response.choices[0].message
    calls = [
        getattr(getattr(call, "function", None), "name", "?")
        for call in getattr(message, "tool_calls", None) or []
    ]
    logger.debug(
        "journey agent model thinking=%r tool_calls=%s",
        _short(getattr(message, "content", None)),
        calls,
    )
    return message


def _verify_route(route_id, from_id, to_id, tracker):
    """Independent DB check: servable route holds both stops in order."""
    detail = _direct_tool("get_route_detail", {"route_id": route_id}, tracker)
    if not detail.get("ok"):
        logger.debug(
            "journey agent verify route=%r from=%r to=%r decision=missing-detail",
            route_id,
            from_id,
            to_id,
        )
        return None
    positions = {}
    for step in detail["route"]["stops"]:
        if step["stop"]["id"] in (from_id, to_id):
            positions[step["stop"]["id"]] = step["position"]
    if (
        from_id in positions
        and to_id in positions
        and positions[from_id] < positions[to_id]
    ):
        logger.debug(
            "journey agent verify route=%r from=%r(pos %s) to=%r(pos %s) decision=verified",
            route_id,
            from_id,
            positions[from_id],
            to_id,
            positions[to_id],
        )
        return detail["route"]
    logger.debug(
        "journey agent verify route=%r from=%r to=%r positions=%r decision=rejected",
        route_id,
        from_id,
        to_id,
        positions,
    )
    return None


def _forbidden(text):
    return bool(_FORBIDDEN_SHAPED.search(text or ""))


def _stop_name(stop_id):
    try:
        return Stop.objects.get(pk=stop_id).name
    except (Stop.DoesNotExist, ValueError):
        return None


def _answer_payload(route, from_id, to_id, draft, meta):
    boarding = _stop_name(from_id) or ""
    alighting = _stop_name(to_id) or ""
    answer = (draft or "").strip() or (
        f"Take the {route['name'] or 'direct'} service "
        f"from {boarding} to {alighting}."
    )
    return (
        {
            "status": "ok",
            "answer": answer,
            "boarding_stop": {"id": from_id, "name": boarding},
            "alighting_stop": {"id": to_id, "name": alighting},
            "routes": [
                {
                    "id": route["id"],
                    "name": route["name"],
                    "evidence": f"/routes/{route['id']}",
                }
            ],
            "meta": meta,
        },
        "answer",
    )


WALK_MATE_LIMIT = 3
WALK_MATE_RADIUS_M = 150.0


def _direct_tool(name, args, tracker):
    """Call a tool outside the model loop, still recording audit trail."""
    logger.debug("journey agent direct tool %s args=%r", name, args)
    tracker["tools_used"].append(name)
    try:
        result = _TOOL_FUNCTIONS[name](**args)
    except Exception:
        logger.exception("journey tool %s failed", name)
        result = {
            "ok": False,
            "error": "That lookup failed. Please carry on without it.",
        }
    tracker["calls"].append((name, args, result))
    return result


def _member_ids(groups):
    ids = []
    for group in groups or []:
        for member in group.get("members", []):
            mid = member.get("id")
            if _is_int(mid) and mid not in ids:
                ids.append(mid)
    return ids


def _members_by_id(groups):
    by_id = {}
    for group in groups or []:
        for member in group.get("members", []):
            if _is_int(member.get("id")):
                by_id[member["id"]] = member
    return by_id


def _group_for_stop(stop_id, tracker):
    """Place group containing a stop id, via its name (group expansion)."""
    try:
        name = _stop_name(stop_id)
    except Exception:
        return None
    if not name:
        return None
    result = _direct_tool("search_places", {"query": name}, tracker)
    if not result.get("ok"):
        return None
    for group in result.get("groups", []):
        if any(
            member.get("id") == stop_id
            for member in group.get("members", [])
        ):
            return group
    return None


def _resolve_end(text, tracker, exclude_ids=None):
    """Resolve one end's text to groups. Returns (groups, problem, exact).

    problem is None on success, else ("empty",) or ("zoom_in", detail).
    exact mirrors the search_places exact flag: True on icontains hit,
    False on token-overlap fallback. ``exclude_ids`` skips rejected
    intent-check candidates.
    """
    args = {"query": text}
    if exclude_ids:
        args["exclude_ids"] = list(exclude_ids)
    logger.debug(
        "journey agent resolve end=%r excluded=%s", text, list(exclude_ids or [])
    )
    result = _direct_tool("search_places", args, tracker)
    if not result.get("ok"):
        logger.debug("journey agent resolve end=%r decision=error", text)
        return None, ("empty",), False
    if result.get("status") == "zoom_in":
        logger.debug("journey agent resolve end=%r decision=zoom_in", text)
        return None, ("zoom_in", result.get("detail") or ""), True
    groups = result.get("groups", [])
    exact = result.get("exact", True)
    if not groups:
        logger.debug(
            "journey agent resolve end=%r decision=empty exact=%s", text, exact
        )
        return None, ("empty",), exact
    logger.debug(
        "journey agent resolve end=%r decision=resolved exact=%s groups=%d labels=%s",
        text,
        exact,
        len(groups),
        [g.get("label") for g in groups[:5]],
    )
    return groups, None, exact


_INTENT_REJECT = re.compile(r"\bREJECT\b", re.IGNORECASE)
_INTENT_IDS = re.compile(r"\d+")


def _intent_check_groups(end_text, groups, tracker):
    """Model intent check for inexact (fallback) groups.

    Sends the top 5 groups with token scores to the model and asks it to
    reject on direction or name mismatch (for example North vs South, or
    a different station name). The model replies ``REJECT <ids...>`` with
    rejected member ids, or ``ACCEPT`` when the groups match the intent.
    Returns (accepted, rejected_ids).
    """
    top = list(groups or [])[:5]
    lines = []
    for group in top:
        members = ", ".join(
            f"{member.get('name')}#{member.get('id')}"
            for member in (group.get("members") or [])[:5]
        )
        lines.append(
            f"- {group.get('label')} score={group.get('score', 0)} "
            f"shared={group.get('shared', 0)} "
            f"phrase_bonus={group.get('phrase_bonus', group.get('exact_bonus', 0))} "
            f"extra={group.get('extra', 0)} members=[{members}]"
        )
    prompt = (
        f"The passenger asked for '{end_text}'. The place search was "
        "inexact (token overlap, exact=False). Top candidates with scores:\n"
        + "\n".join(lines)
        + "\nReply with ACCEPT when a candidate matches the passenger's "
        "intent, or REJECT <member ids> listing every candidate whose "
        "direction (North/South/East/West) or station name mismatches "
        "the request."
    )
    messages = [
        {
            "role": "system",
            "content": "You check place-search intent. Reject on direction "
            "or name mismatch. Reply ACCEPT or REJECT <member ids>.",
        },
        {"role": "user", "content": prompt},
    ]
    logger.debug(
        "journey agent intent-check end=%r top5=%s",
        end_text,
        [
            (g.get("label"), g.get("score"), g.get("shared"))
            for g in top
        ],
    )
    try:
        message = _model_turn(messages)
    except Exception:
        logger.debug(
            "journey agent intent-check end=%r decision=accept(model-error)",
            end_text,
        )
        return True, []
    content = getattr(message, "content", None) or ""
    if not _INTENT_REJECT.search(content):
        logger.debug(
            "journey agent intent-check end=%r reply=%r decision=accept",
            end_text,
            _short(content),
        )
        return True, []
    member_ids = set(_member_ids(top))
    rejected = [
        int(value)
        for value in _INTENT_IDS.findall(content)
        if int(value) in member_ids
    ]
    if not rejected:
        rejected = sorted(member_ids)
    logger.debug(
        "journey agent intent-check end=%r reply=%r decision=reject ids=%s",
        end_text,
        _short(content),
        rejected,
    )
    return False, rejected


def _resolve_with_retry(text, tracker, max_attempts=MAX_RESOLVE_ATTEMPTS):
    """Resolve one end, retrying inexact hits via model intent check.

    Exact (icontains) hits return immediately. Inexact fallback groups go
    to the model (top 5 with scores); on REJECT the named member ids join
    the excluded set and search_places retries with exclude_ids. Stops
    after max_attempts, an empty result, or an exact match. Returns
    (groups, problem, exact, excluded) where problem is None on usable
    groups, else ("empty",), ("zoom_in", detail), or ("rejected",).
    """
    excluded = []
    excluded_set = set()
    last_groups = None
    last_exact = False
    for attempt in range(1, max_attempts + 1):
        logger.debug(
            "journey agent retry end=%r attempt=%d/%d excluded=%s",
            text,
            attempt,
            max_attempts,
            excluded,
        )
        groups, problem, exact = _resolve_end(
            text, tracker, exclude_ids=excluded or None
        )
        if problem is not None:
            logger.debug(
                "journey agent retry end=%r attempt=%d decision=stop problem=%s",
                text,
                attempt,
                problem[0],
            )
            return groups, problem, exact, excluded
        if exact:
            logger.debug(
                "journey agent retry end=%r attempt=%d decision=exact-match",
                text,
                attempt,
            )
            return groups, None, True, excluded
        last_groups, last_exact = groups, exact
        accepted, rejected = _intent_check_groups(text, groups, tracker)
        if accepted:
            logger.debug(
                "journey agent retry end=%r attempt=%d decision=intent-accepted",
                text,
                attempt,
            )
            return groups, None, False, excluded
        fresh = [rid for rid in rejected if rid not in excluded_set]
        if not fresh:
            logger.debug(
                "journey agent retry end=%r attempt=%d decision=intent-rejected-no-new-ids stop",
                text,
                attempt,
            )
            return groups, ("rejected",), False, excluded
        excluded_set.update(fresh)
        excluded = sorted(excluded_set)
    if last_groups is None:
        return None, ("empty",), False, excluded
    logger.debug(
        "journey agent retry end=%r decision=attempts-exhausted excluded=%s",
        text,
        excluded,
    )
    return last_groups, ("rejected",), last_exact, excluded


def _mates_for(direct_id, direct, members, cache, tracker):
    """Walkable same-group mates of an exact stop (nearest first).

    Returns (shown_mates, overflow_count). Distances come from distance_m
    (haversine, inclusive at 150m); walk_m is whole meters, half up.
    """
    if direct_id in cache:
        return cache[direct_id]
    mates = []
    for member in members:
        mid = member.get("id")
        if mid == direct_id or not _is_int(mid):
            continue
        gap = _direct_tool(
            "distance_m",
            {
                "lat1": direct.get("lat"),
                "lon1": direct.get("lon"),
                "lat2": member.get("lat"),
                "lon2": member.get("lon"),
            },
            tracker,
        )
        if not gap.get("ok"):
            continue
        dist = gap["distance_m"]
        if dist <= WALK_MATE_RADIUS_M:
            mates.append(
                {
                    "id": mid,
                    "name": member.get("name") or "",
                    "walk_m": int(dist + 0.5),
                }
            )
    mates.sort(key=lambda mate: (mate["walk_m"], mate["id"]))
    shown = mates[:WALK_MATE_LIMIT]
    result = (shown, len(mates) - len(shown))
    cache[direct_id] = result
    return result


def _classify_pairs(viable, from_groups, to_groups, tracker):
    """Verify each viable pair and attach walkable mates per end."""
    from_by_id = _members_by_id(from_groups)
    to_by_id = _members_by_id(to_groups)
    from_members = list(from_by_id.values())
    to_members = list(to_by_id.values())
    from_cache = {}
    to_cache = {}
    classified = []
    for pair in viable or []:
        from_id = pair.get("from_stop_id")
        to_id = pair.get("to_stop_id")
        for row in pair.get("routes", []):
            route = _verify_route(
                row.get("id"), from_id, to_id, tracker
            )
            if route is None:
                continue
            mates_from, over_from = _mates_for(
                from_id,
                from_by_id.get(from_id, {}),
                from_members,
                from_cache,
                tracker,
            )
            mates_to, over_to = _mates_for(
                to_id,
                to_by_id.get(to_id, {}),
                to_members,
                to_cache,
                tracker,
            )
            classified.append(
                {
                    "route_id": route["id"],
                    "from_id": from_id,
                    "to_id": to_id,
                    "mates_from": mates_from,
                    "mates_to": mates_to,
                    "overflow_from": over_from,
                    "overflow_to": over_to,
                }
            )
    return classified


def _destinations_from_groups(ranked_groups):
    """Unique alighting stops in ranked order (rank_pairs caps at 5)."""
    seen = []
    for group in ranked_groups:
        for option in group.get("options", []):
            stop = option.get("alighting_stop") or {}
            if stop.get("id") not in [s["stop"]["id"] for s in seen]:
                seen.append(
                    {
                        "stop": {
                            "id": stop.get("id"),
                            "name": stop.get("name") or "",
                        },
                        "evidence": option["route"]["evidence"],
                    }
                )
    return seen


def _answer_from_classified(classified, tracker):
    """Ranked (payload, route, from, to) from classified pairs (no meta)."""
    pairs = [
        {
            "route_id": item["route_id"],
            "from_id": item["from_id"],
            "to_id": item["to_id"],
            "mates_from": item["mates_from"],
            "mates_to": item["mates_to"],
            "overflow_from": item["overflow_from"],
            "overflow_to": item["overflow_to"],
        }
        for item in classified
    ]
    groups, by_id = _rank_pairs(pairs)
    if not groups or not by_id:
        return None
    ranked = rank_pairs(
        pairs, destinations=_destinations_from_groups(groups)
    )
    first = classified[0]
    route = by_id[first["route_id"]][0]
    return ranked, route, first["from_id"], first["to_id"]


_TRUNCATED_MESSAGE = (
    "There are many possible stops; I checked the nearest ones first. "
    "Which destination did you mean?"
)
_FAMILIAR_SUGGEST = (
    " If you know both exact stops, you can also try direct "
    "from-to search."
)


def _matrix_answer(from_ids, to_ids, from_groups, to_groups, tracker):
    """Matrix test + classify + answer.

    Returns (answer_item_or_None, info) where info carries
    ``truncated``, ``untested_from_ids`` and ``untested_to_ids``.
    """
    logger.debug(
        "journey agent matrix from=%d to=%d cap=%d",
        len(list(from_ids)),
        len(list(to_ids)),
        tools.MATRIX_PAIR_CAP,
    )
    result = _direct_tool(
        "find_routes_matrix",
        {
            "from_ids": list(from_ids),
            "to_ids": list(to_ids),
            "limit": tools.MATRIX_PAIR_CAP,
        },
        tracker,
    )
    info = {
        "truncated": False,
        "untested_from_ids": [],
        "untested_to_ids": [],
    }
    if not result.get("ok"):
        logger.debug("journey agent matrix decision=tool-error")
        return None, info
    info = {
        "truncated": bool(result.get("truncated")),
        "untested_from_ids": list(result.get("untested_from_ids", [])),
        "untested_to_ids": list(result.get("untested_to_ids", [])),
    }
    logger.debug(
        "journey agent matrix candidate-pairs=%d truncated=%s",
        len(result.get("pairs", [])),
        info["truncated"],
    )
    classified = _classify_pairs(
        result.get("pairs", []), from_groups, to_groups, tracker
    )
    logger.debug(
        "journey agent matrix decision=%s verified=%d",
        "answer" if classified else "no-viable-pair",
        len(classified),
    )
    if not classified:
        return None, info
    return _answer_from_classified(classified, tracker), info


def _pick_payload(slot, offered_ids, resolved, message):
    """Map/list pick payload; the pick re-enters the matrix flow."""
    candidates = []
    if offered_ids:
        known = Stop.objects.filter(pk__in=list(offered_ids)).in_bulk()
        for sid in offered_ids:
            stop = known.get(sid)
            if stop is None:
                continue
            candidates.append(
                _candidate_entry(
                    sid,
                    stop.name or "",
                    _candidate_detail(stop),
                    stop.lat,
                    stop.lon,
                )
            )
    payload = {
        "status": "disambiguate",
        "message": message,
        "candidates": candidates,
        "slot": slot,
        "offered_ids": list(offered_ids),
    }
    if resolved is not None:
        payload["resolved"] = resolved
    return payload


def _expanded_singleton_answer(from_id, to_id, tracker):
    """FR-010: exact-id pair failed; expand each end to its group and retry."""
    group_f = _group_for_stop(from_id, tracker)
    group_t = _group_for_stop(to_id, tracker)
    from_ids = _member_ids([group_f]) if group_f else [from_id]
    to_ids = _member_ids([group_t]) if group_t else [to_id]
    if from_ids == [from_id] and to_ids == [to_id]:
        return None, {
            "truncated": False,
            "untested_from_ids": [],
            "untested_to_ids": [],
        }
    return _matrix_answer(
        from_ids,
        to_ids,
        [group_f] if group_f else None,
        [group_t] if group_t else None,
        tracker,
    )


def _remaining_from_groups(question, known_slot, known_id, tracker):
    """Derive the other end via search_places groups (replaces single-stop).

    Inexact hits go through the model intent check with exclude_ids
    retry (see _resolve_with_retry) instead of auto-answering. Returns
    (core, None) on answer, (None, "unknown") when unmatched,
    (None, "noviable") when groups resolve but no pair works (including
    intent-rejected ends), or None when the question carries no usable
    other end.
    """
    match = _FROM_TO.search(question or "")
    if not match:
        return None
    if known_slot == "from":
        other_text = match.group(2).strip()
    else:
        other_text = match.group(1).strip()
    if not other_text:
        return None
    groups, problem, _exact, _excluded = _resolve_with_retry(
        other_text, tracker
    )
    if groups is None or problem is not None:
        return None, "unknown"
    member_ids = _member_ids(groups)
    if not member_ids:
        return None, "unknown"
    remaining_slot = "to" if known_slot == "from" else "from"
    known_group = _group_for_stop(known_id, tracker)
    known_groups = [known_group] if known_group else None
    if known_slot == "from":
        item, info = _matrix_answer(
            [known_id], member_ids, known_groups, groups, tracker
        )
        untested = info["untested_to_ids"]
    else:
        item, info = _matrix_answer(
            member_ids, [known_id], groups, known_groups, tracker
        )
        untested = info["untested_from_ids"]
    if item is None:
        if info["truncated"]:
            return None, ("truncated", remaining_slot, untested)
        return None, ("noviable",)
    return item, None


def _fresh_matrix_answer(question, tracker):
    """Deterministic groups-first answer for from-to questions.

    Exact (icontains) ends resolve straight to the matrix flow. Inexact
    (fallback, exact False) ends never auto-answer: the top 5 groups with
    scores go to the model for a direction/name intent check, rejects
    join the excluded set, and search_places retries with exclude_ids
    (see _resolve_with_retry). Stops after MAX_RESOLVE_ATTEMPTS, an empty
    result, or an exact match, then refuses or picks per FR-007.

    Returns (core, None) on answer, (None, (problem, ...)) for empty /
    zoom_in / no-viable ends, or None when the question has no usable
    two ends (falls through to the model loop).
    """
    match = _FROM_TO.search(question or "")
    if not match:
        return None
    from_text = match.group(1).strip()
    to_text = match.group(2).strip()
    if not from_text or not to_text:
        return None
    from_groups, from_problem, _from_exact, _from_excluded = (
        _resolve_with_retry(from_text, tracker)
    )
    to_groups, to_problem, _to_exact, _to_excluded = _resolve_with_retry(
        to_text, tracker
    )
    if from_problem is not None or to_problem is not None:
        failed = "from" if from_problem is not None else "to"
        problem = from_problem or to_problem
        if problem[0] == "zoom_in":
            return None, ("zoom_in", problem[1])
        if problem[0] == "rejected":
            return None, ("noviable",)
        return None, ("unknown", failed)
    item, info = _matrix_answer(
        _member_ids(from_groups),
        _member_ids(to_groups),
        from_groups,
        to_groups,
        tracker,
    )
    if item is None:
        if info["truncated"]:
            return None, ("truncated", "from", info["untested_from_ids"])
        return None, ("noviable",)
    return item, None


def _walk_note(end_name, mates, overflow):
    if not mates and not overflow:
        return ""
    bits = ", ".join(
        f"{mate['name']} ({mate['walk_m']}m walk)" for mate in mates
    )
    extra = f" plus {overflow} more within 150m" if overflow else ""
    return f" Also near {end_name}: {bits}{extra}."


def run_journey(*, question, history=(), context=None):
    """Answer, disambiguate, or refuse one journey question.

    Returns ``(payload, tools_used)``; ``payload`` already carries its
    response ``meta``. Never raises for model, tool, or data problems:
    anything unverifiable becomes a refusal.
    """
    started = time.monotonic()
    context = context or {}
    candidate_ids = [
        c for c in (context.get("candidate_stop_ids") or []) if isinstance(c, int)
    ]
    if not isinstance(question, str) or not question.strip():
        meta = _meta(0)
        _log(meta["model"], meta["provider"], 0, [])
        return {"status": "refuse", "message": _ASK_AGAIN, "meta": meta}, []

    tracker = {"tools_used": [], "calls": [], "findings": {}, "searches": []}
    logger.debug(
        "journey agent question=%r history_turns=%d context_keys=%s candidate_ids=%s",
        question.strip()[:300],
        len(history or []),
        sorted(context.keys()),
        candidate_ids,
    )
    _attach_request_log_buffer()

    def selection_finish(payload):
        latency_ms = int((time.monotonic() - started) * 1000)
        meta = _selection_meta(latency_ms)
        payload["meta"] = meta
        _log(
            meta["model"], meta["provider"], latency_ms, tracker["tools_used"]
        )
        _release_request_log_buffer(keep=(payload.get("status") != "ok"))
        logger.debug(
            "journey agent decision=%s tools_used=%s",
            payload.get("status"),
            tracker["tools_used"],
        )
        return payload, tracker["tools_used"]

    def ranked_payload(ranked, first_route, from_id, to_id, draft):
        payload, _ = _answer_payload(first_route, from_id, to_id, "", None)
        single = (
            len(ranked["groups"]) == 1
            and len(ranked["groups"][0]["options"]) == 1
        )
        if draft and single and not _forbidden(draft):
            payload["answer"] = draft
        else:
            payload["answer"] = ranked["answer"]
        payload["option_groups"] = ranked["groups"]
        payload["destinations"] = ranked["destinations"]
        return payload

    def answer_direct(from_id, to_id):
        """Retained leaf verifier (012 FR-011): single-pair verification
        only, never an entry answer. All entries go via the matrix flow."""
        result = tools.find_routes(from_stop_id=from_id, to_stop_id=to_id)
        tracker["tools_used"].append("find_routes")
        tracker["calls"].append(
            (
                "find_routes",
                {"from_stop_id": from_id, "to_stop_id": to_id},
                result,
            )
        )
        verified = []
        if result.get("ok"):
            pair = (from_id, to_id)
            for row in result.get("routes", []):
                tracker["findings"][row["id"]] = pair
            for row in result.get("routes", []):
                route = _verify_route(row["id"], from_id, to_id, tracker)
                if route is not None:
                    verified.append((route, from_id, to_id))
        if not verified:
            return selection_finish(
                {"status": "refuse", "message": _NO_DIRECT}
            )
        pairs = [
            {"route_id": route["id"], "from_id": f, "to_id": t}
            for route, f, t in verified
        ]
        first_route = verified[0][0]
        ranked = rank_pairs(
            pairs,
            destinations=[
                {
                    "stop": {"id": to_id, "name": _stop_name(to_id) or ""},
                    "evidence": f"/routes/{first_route['id']}",
                }
            ],
        )
        return selection_finish(
            ranked_payload(ranked, first_route, from_id, to_id, "")
        )

    selection = _resolve_selection(context, question)
    logger.debug("journey agent selection=%s", selection[0])
    if selection[0] == "invalid":
        logger.debug("journey agent decision=refuse reason=unmatched-pick")
        return selection_finish(
            {"status": "refuse", "message": _UNMATCHED_PICK}
        )
    if selection[0] == "full":
        _, from_id, to_id = selection
        item, info = _matrix_answer(
            [from_id], [to_id], None, None, tracker
        )
        if item is None and not info["truncated"]:
            item, info = _expanded_singleton_answer(from_id, to_id, tracker)
        if item is None:
            if info["truncated"]:
                return selection_finish(
                    _pick_payload(
                        "to",
                        info["untested_to_ids"],
                        None,
                        _TRUNCATED_MESSAGE,
                    )
                )
            return selection_finish(
                {
                    "status": "refuse",
                    "message": _NO_DIRECT + _FAMILIAR_SUGGEST,
                }
            )
        ranked, route, from_id, to_id = item
        payload = ranked_payload(ranked, route, from_id, to_id, "")
        return selection_finish(payload)
    if selection[0] == "partial":
        _, known_slot, known_id, remaining_slot, remaining_ids, slots = (
            selection
        )
        if not remaining_ids:
            derived = _remaining_from_groups(
                question, known_slot, known_id, tracker
            )
            if derived is not None:
                item, fail = derived
                if item is not None:
                    ranked, route, from_id, to_id = item
                    payload = ranked_payload(
                        ranked, route, from_id, to_id, ""
                    )
                    return selection_finish(payload)
                resolved = {
                    "id": known_id,
                    "name": _stop_name(known_id) or "",
                }
                if fail[0] == "unknown":
                    return selection_finish(
                        _pick_payload(
                            remaining_slot, [], resolved, _UNKNOWN_PLACE
                        )
                    )
                if fail[0] == "truncated":
                    _, slot, ids = fail
                    return selection_finish(
                        _pick_payload(
                            slot, ids, resolved, _TRUNCATED_MESSAGE
                        )
                    )
                return selection_finish(
                    {"status": "refuse", "message": _NO_DIRECT}
                )
            return selection_finish(
                {"status": "refuse", "message": _UNMATCHED_PICK}
            )
        known_name = _stop_name(known_id) or ""
        stops = Stop.objects.filter(pk__in=remaining_ids).in_bulk()
        candidates = [
            _candidate_entry(
                sid,
                (stops[sid].name or ""),
                _candidate_detail(stops[sid]),
                stops[sid].lat,
                stops[sid].lon,
            )
            for sid in remaining_ids
            if sid in stops
        ]
        if not candidates:
            return selection_finish(
                {"status": "refuse", "message": _UNKNOWN_PLACE}
            )
        payload = {
            "status": "disambiguate",
            "message": (
                f"Thanks — keeping {known_name}. Which one did you mean "
                "for the "
                f"{'destination' if remaining_slot == 'to' else 'origin'}?"
            ),
            "candidates": candidates,
            "slot": remaining_slot,
            "resolved": {"id": known_id, "name": known_name},
            "offered_ids": remaining_ids,
        }
        if isinstance(slots, dict):
            payload["slots"] = {
                "from_ids": [
                    c for c in (slots.get("from_ids") or []) if _is_int(c)
                ],
                "to_ids": [
                    c for c in (slots.get("to_ids") or []) if _is_int(c)
                ],
            }
            payload["surviving_context"] = {
                "other_end": known_slot,
                "other_end_ids": [known_id],
            }
        return selection_finish(payload)
    if selection[0] == "fresh":
        context = {}
    candidate_ids = [
        c for c in (context.get("candidate_stop_ids") or []) if isinstance(c, int)
    ]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if candidate_ids:
        messages.append(
            {
                "role": "system",
                "content": "Follow-up: the passenger is choosing between "
                f"stop ids {candidate_ids}. Resolve their reply to one "
                "of these ids.",
            }
        )
    messages.extend(_clean_history(history))
    messages.append({"role": "user", "content": question.strip()})

    def finish(payload, fallback=False):
        latency_ms = int((time.monotonic() - started) * 1000)
        meta = _meta(latency_ms, fallback=fallback)
        payload["meta"] = meta
        _log(meta["model"], meta["provider"], latency_ms, tracker["tools_used"])
        _release_request_log_buffer(keep=(payload.get("status") != "ok"))
        logger.debug(
            "journey agent decision=%s fallback=%s tools_used=%s",
            payload.get("status"),
            fallback,
            tracker["tools_used"],
        )
        return payload, tracker["tools_used"]

    def fallback():
        for route_id, (from_id, to_id) in tracker["findings"].items():
            route = _verify_route(route_id, from_id, to_id, tracker)
            if route is not None:
                logger.debug(
                    "journey agent fallback decision=answer route=%r",
                    route_id,
                )
                payload, _ = _answer_payload(
                    route, from_id, to_id, "", _meta(0, fallback=True)
                )
                return finish(payload, fallback=True)
        logger.debug("journey agent fallback decision=refuse reason=cannot-answer")
        return finish({"status": "refuse", "message": _CANNOT_ANSWER}, fallback=True)

    if selection[0] in ("none", "fresh"):
        fresh = _fresh_matrix_answer(question, tracker)
        if fresh is not None:
            item, problem = fresh
            if item is not None:
                ranked, route, from_id, to_id = item
                logger.debug(
                    "journey agent fresh-matrix decision=answer route=%r from=%r to=%r",
                    route["id"],
                    from_id,
                    to_id,
                )
                payload = ranked_payload(
                    ranked, route, from_id, to_id, ""
                )
                return finish(payload)
            logger.debug(
                "journey agent fresh-matrix decision=%s problem=%s",
                "pick" if problem[0] in ("unknown", "truncated") else "refuse",
                problem[0],
            )
            if problem[0] == "unknown":
                _, slot = problem
                return finish(
                    _pick_payload(slot, [], None, _UNKNOWN_PLACE)
                )
            if problem[0] == "truncated":
                _, slot, ids = problem
                return finish(
                    _pick_payload(slot, ids, None, _TRUNCATED_MESSAGE)
                )
            if problem[0] == "zoom_in":
                return finish(
                    {
                        "status": "refuse",
                        "message": problem[1] or _UNKNOWN_PLACE,
                    }
                )
            return finish({"status": "refuse", "message": _NO_DIRECT})

    try:
        draft = ""
        for turn in range(1, MAX_TOOL_TURNS + 1):
            message = _model_turn(messages)
            entry = _assistant_entry(message)
            if not entry["tool_calls"]:
                draft = entry["content"] or ""
                logger.debug(
                    "journey agent model-loop turn=%d decision=draft draft=%r",
                    turn,
                    _short(draft),
                )
                break
            logger.debug(
                "journey agent model-loop turn=%d tool_calls=%d",
                turn,
                len(entry["tool_calls"]),
            )
            messages.append(entry)
            for call in entry["tool_calls"]:
                try:
                    args = json.loads(call["function"]["arguments"] or "{}")
                except (TypeError, ValueError):
                    args = None
                result = execute_tool(
                    call["function"]["name"], args, tracker
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(result),
                    }
                )
        else:
            logger.debug(
                "journey agent model-loop decision=refuse reason=max-tool-turns"
            )
            return finish({"status": "refuse", "message": _UNVERIFIABLE})

        cited = []
        for raw in _ROUTE_REF.findall(draft):
            rid = int(raw)
            if rid not in cited:
                cited.append(rid)

        def verified_answer(text):
            if _forbidden(text):
                logger.debug(
                    "journey agent verified-answer decision=reject reason=forbidden-shaped draft=%r",
                    _short(text),
                )
                return None
            verified = []
            for rid in cited:
                pair = tracker["findings"].get(rid)
                if pair is None:
                    logger.debug(
                        "journey agent verified-answer decision=reject reason=uncited-route route=%r",
                        rid,
                    )
                    return None
                route = _verify_route(rid, pair[0], pair[1], tracker)
                if route is None:
                    logger.debug(
                        "journey agent verified-answer decision=reject reason=unverifiable-pair route=%r",
                        rid,
                    )
                    return None
                verified.append((route, pair[0], pair[1]))
            if not verified:
                logger.debug(
                    "journey agent verified-answer decision=reject reason=no-verified-routes"
                )
                return None
            pairs = [
                {"route_id": route["id"], "from_id": f, "to_id": t}
                for route, f, t in verified
            ]
            first_route, first_from, first_to = verified[0]
            ranked = rank_pairs(
                pairs,
                destinations=[
                    {
                        "stop": {
                            "id": first_to,
                            "name": _stop_name(first_to) or "",
                        },
                        "evidence": f"/routes/{first_route['id']}",
                    }
                ],
            )
            return ranked_payload(
                ranked, first_route, first_from, first_to, text
            )

        answer = verified_answer(draft) if cited else None
        if answer is None and cited:
            logger.debug("journey agent model-loop decision=repair-retry")
            messages.append({"role": "user", "content": REPAIR_NUDGE})
            try:
                repair = _model_turn(messages)
                draft = getattr(repair, "content", None) or ""
                logger.debug(
                    "journey agent model-loop repair draft=%r", _short(draft)
                )
            except Exception:
                return fallback()
            cited = []
            for raw in _ROUTE_REF.findall(draft):
                rid = int(raw)
                if rid not in cited:
                    cited.append(rid)
            answer = verified_answer(draft) if cited else None
            if answer is None:
                logger.debug(
                    "journey agent model-loop decision=refuse reason=unrepairable"
                )
                return finish({"status": "refuse", "message": _UNVERIFIABLE})
        if answer is not None:
            logger.debug("journey agent model-loop decision=answer")
            return finish(answer)

        enriched = _disambiguation_context(question, tracker["searches"])
        if enriched is not None:
            logger.debug("journey agent model-loop decision=disambiguate")
            return finish(enriched)
        for _args, result in reversed(tracker["searches"]):
            stops = result.get("stops", [])
            if len(stops) > 1:
                logger.debug("journey agent model-loop decision=disambiguate")
                return finish(
                    {
                        "status": "disambiguate",
                        "message": "I found more than one stop with that "
                        "name. Which one did you mean?",
                        "candidates": [
                            {"id": s["id"], "name": s["name"]} for s in stops
                        ],
                    }
                )
        for _args, result in tracker["searches"]:
            if result.get("status") == "empty":
                logger.debug(
                    "journey agent model-loop decision=refuse reason=unknown-place"
                )
                return finish({"status": "refuse", "message": _UNKNOWN_PLACE})
        for name, _args, result in tracker["calls"]:
            if name == "find_routes" and result.get("ok"):
                if not result.get("routes"):
                    logger.debug(
                        "journey agent model-loop decision=refuse reason=no-direct"
                    )
                    return finish({"status": "refuse", "message": _NO_DIRECT})
        logger.debug(
            "journey agent model-loop decision=refuse reason=unverifiable"
        )
        return finish({"status": "refuse", "message": _UNVERIFIABLE})
    except Exception:
        logger.exception("journey model loop failed")
        return fallback()
