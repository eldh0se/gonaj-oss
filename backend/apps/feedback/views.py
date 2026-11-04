"""Anonymous passenger feedback: validate first, then budget, then store."""
import logging
import secrets
import string

from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.feedback.models import CATEGORY_CHOICES, FeedbackReport
from apps.transport.api.throttling import FEEDBACK_THROTTLE_CLASSES, check_budgets
from apps.transport.models import Route, Stop

logger = logging.getLogger(__name__)

CATEGORIES = {key for key, _ in CATEGORY_CHOICES}
REFERENCE_ALPHABET = string.ascii_uppercase + string.digits
REFERENCE_ATTEMPTS = 5
MAX_MESSAGE_CHARS = 2000
NON_WRITABLE = ("reference", "status", "created_at", "updated_at")


def _bad_request(detail, code=None):
    body = {"detail": detail}
    if code is not None:
        body["code"] = code
    return Response(body, status=status.HTTP_400_BAD_REQUEST)


def _make_reference():
    return "FB-" + "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(8))


def _journey_header(journey):
    parts = []
    origin = (journey.get("from_name") or "").strip()
    destination = (journey.get("to_name") or "").strip()
    if origin or destination:
        parts.append(f"Journey: {origin} \u2192 {destination}".strip())
    question = (journey.get("question") or "").strip()
    if question:
        parts.append(f"Asked: {question}")
    return " | ".join(parts)


@api_view(["POST"])
@permission_classes([AllowAny])
def feedback(request):
    body = request.data
    if not isinstance(body, dict):
        return _bad_request(
            "That request does not look right. "
            "Please check the values and try again."
        )
    for key in NON_WRITABLE:
        if key in body:
            return _bad_request(
                "That request includes fields that cannot be set. "
                "Please remove them and try again."
            )
    category = body.get("category")
    if category not in CATEGORIES:
        return _bad_request(
            "Please choose a category: incorrect, missing, outdated, or other."
        )
    message = body.get("message")
    if not isinstance(message, str) or not message.strip():
        return _bad_request(
            "Please write a message describing the issue."
        )
    text = message.strip()
    if len(text) > MAX_MESSAGE_CHARS:
        return _bad_request(
            "Please keep the message to 2000 characters or fewer."
        )
    route = None
    if body.get("route_id") is not None:
        try:
            route = Route.objects.get(pk=int(body.get("route_id")))
        except (TypeError, ValueError, Route.DoesNotExist):
            return _bad_request(
                "The route or stop this refers to no longer exists. "
                "Please check and try again.",
                code="invalid-reference",
            )
    stop = None
    if body.get("stop_id") is not None:
        try:
            stop = Stop.objects.get(pk=int(body.get("stop_id")))
        except (TypeError, ValueError, Stop.DoesNotExist):
            return _bad_request(
                "The route or stop this refers to no longer exists. "
                "Please check and try again.",
                code="invalid-reference",
            )
    journey = body.get("journey") or {}
    if not isinstance(journey, dict):
        return _bad_request(
            "That request does not look right. "
            "Please check the values and try again."
        )
    for key in ("from_name", "to_name", "question"):
        if key in journey and not isinstance(journey[key], str):
            return _bad_request(
                "That request does not look right. "
                "Please check the values and try again."
            )
    header = _journey_header(journey)
    stored = f"{header}\n\n{text}" if header else text

    check_budgets(request, FEEDBACK_THROTTLE_CLASSES)

    reference = None
    for _ in range(REFERENCE_ATTEMPTS):
        candidate = _make_reference()
        try:
            report = FeedbackReport.objects.create(
                reference=candidate,
                category=category,
                message=stored,
                route=route,
                stop=stop,
            )
            reference = report.reference
            break
        except IntegrityError:
            continue
    if reference is None:
        logger.error("feedback reference exhaustion")
        return Response(
            {"detail": "We could not save that report. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    receipt = (
        f"Thanks \u2014 your report {reference} is received. "
        "It is not verified yet. Reporting is anonymous with no tracking. "
        "Please save your reference for your records; there is no lookup."
    )
    return Response(
        {"reference": reference, "receipt": receipt},
        status=status.HTTP_201_CREATED,
    )
