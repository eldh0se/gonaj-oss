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
            verified = []
            for rid in cited:
                pair = tracker["findings"].get(rid)
                if pair is None:
                    return None
                route = _verify_route(rid, pair[0], pair[1])
                if route is None:
                    return None
                verified.append((route, pair))
            if not verified or _forbidden(text):
                return None
            route, (from_id, to_id) = verified[0]
            payload, _ = _answer_payload(route, from_id, to_id, text, None)
            return payload

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
