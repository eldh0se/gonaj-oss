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

SYSTEM_PROMPT = (
    "You are the Gonaj journey helper. Answer in everyday language "
    "about direct bus services only, using the read-only tools. "
    "Every route you cite must come from a find_routes or "
    "get_route_detail result, and you must cite it as /routes/:id. "
    "Never mention schedules, departure or arrival times, durations, "
    "frequencies, or transfers. If a stop name matches several stops, "
    "do not guess: ask the passenger to choose. If no direct service "
    "is known, or a place cannot be found, say so plainly and invent "
    "nothing."
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


def _candidate_entry(stop_id, name, detail):
    entry = {"id": stop_id, "name": name}
    if detail:
        entry["detail"] = detail
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


def _remaining_from_question(question, known_slot, known_id, tracker):
    """Derive the other end from a from/to question without the model.

    Returns ("answer", from_id, to_id) for a singleton match,
    ("prompt", ids) for several matches, ("unknown",) when nothing
    matches, or (None,) when the question carries no usable other end.
    """
    match = _FROM_TO.search(question or "")
    if not match:
        return (None,)
    if known_slot == "from":
        other_text = match.group(2).strip()
    else:
        other_text = match.group(1).strip()
    if not other_text:
        return (None,)
    result = tools.search_stops(query=other_text)
    tracker["tools_used"].append("search_stops")
    tracker["calls"].append(
        ("search_stops", {"query": other_text}, result)
    )
    if not result.get("ok"):
        return (None,)
    stops = result.get("stops") or []
    if not stops:
        return ("unknown",)
    if len(stops) == 1:
        other_id = stops[0]["id"]
        if known_slot == "from":
            return ("answer", known_id, other_id)
        return ("answer", other_id, known_id)
    return ("prompt", [stop["id"] for stop in stops])


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
                stop["id"], stop["name"], _candidate_detail_from_row(stop)
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
    if name == "search_stops":
        for key in ("query", "bbox"):
            if key in args and not isinstance(args[key], str):
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
    validated = _validate_tool_args(name, args) if name in _TOOL_FUNCTIONS else None
    if validated is None:
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
    return response.choices[0].message


def _verify_route(route_id, from_id, to_id):
    """Independent DB check: servable route holds both stops in order."""
    detail = tools.get_route_detail(route_id)
    if not detail.get("ok"):
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
        return detail["route"]
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

    def selection_finish(payload):
        latency_ms = int((time.monotonic() - started) * 1000)
        meta = _selection_meta(latency_ms)
        payload["meta"] = meta
        _log(
            meta["model"], meta["provider"], latency_ms, tracker["tools_used"]
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
        """Local verified answer (or honest refusal) without any model call."""
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
                route = _verify_route(row["id"], from_id, to_id)
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
    if selection[0] == "invalid":
        return selection_finish(
            {"status": "refuse", "message": _UNMATCHED_PICK}
        )
    if selection[0] == "full":
        _, from_id, to_id = selection
        return answer_direct(from_id, to_id)
    if selection[0] == "partial":
        _, known_slot, known_id, remaining_slot, remaining_ids, slots = (
            selection
        )
        if not remaining_ids:
            derived = _remaining_from_question(
                question, known_slot, known_id, tracker
            )
            if derived[0] == "answer":
                return answer_direct(derived[1], derived[2])
            if derived[0] == "prompt":
                remaining_ids = derived[1]
            elif derived[0] == "unknown":
                return selection_finish(
                    {"status": "refuse", "message": _UNKNOWN_PLACE}
                )
            else:
                return selection_finish(
                    {"status": "refuse", "message": _UNMATCHED_PICK}
                )
        known_name = _stop_name(known_id) or ""
        stops = Stop.objects.filter(pk__in=remaining_ids).in_bulk()
        candidates = [
            _candidate_entry(
                sid, (stops[sid].name or ""), _candidate_detail(stops[sid])
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
        return payload, tracker["tools_used"]

    def fallback():
        for route_id, (from_id, to_id) in tracker["findings"].items():
            route = _verify_route(route_id, from_id, to_id)
            if route is not None:
                payload, _ = _answer_payload(
                    route, from_id, to_id, "", _meta(0, fallback=True)
                )
                return finish(payload, fallback=True)
        return finish({"status": "refuse", "message": _CANNOT_ANSWER}, fallback=True)

    try:
        draft = ""
        for _ in range(MAX_TOOL_TURNS):
            message = _model_turn(messages)
            entry = _assistant_entry(message)
            if not entry["tool_calls"]:
                draft = entry["content"] or ""
                break
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
            return finish({"status": "refuse", "message": _UNVERIFIABLE})

        cited = []
        for raw in _ROUTE_REF.findall(draft):
            rid = int(raw)
            if rid not in cited:
                cited.append(rid)

        def verified_answer(text):
            if _forbidden(text):
                return None
            verified = []
            for rid in cited:
                pair = tracker["findings"].get(rid)
                if pair is None:
                    return None
                route = _verify_route(rid, pair[0], pair[1])
                if route is None:
                    return None
                verified.append((route, pair[0], pair[1]))
            if not verified:
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
            messages.append({"role": "user", "content": REPAIR_NUDGE})
            try:
                repair = _model_turn(messages)
                draft = getattr(repair, "content", None) or ""
            except Exception:
                return fallback()
            cited = []
            for raw in _ROUTE_REF.findall(draft):
                rid = int(raw)
                if rid not in cited:
                    cited.append(rid)
            answer = verified_answer(draft) if cited else None
            if answer is None:
                return finish({"status": "refuse", "message": _UNVERIFIABLE})
        if answer is not None:
            return finish(answer)

        enriched = _disambiguation_context(question, tracker["searches"])
        if enriched is not None:
            return finish(enriched)
        for _args, result in reversed(tracker["searches"]):
            stops = result.get("stops", [])
            if len(stops) > 1:
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
                return finish({"status": "refuse", "message": _UNKNOWN_PLACE})
        for name, _args, result in tracker["calls"]:
            if name == "find_routes" and result.get("ok"):
                if not result.get("routes"):
                    return finish({"status": "refuse", "message": _NO_DIRECT})
        return finish({"status": "refuse", "message": _UNVERIFIABLE})
    except Exception:
        logger.exception("journey model loop failed")
        return fallback()
