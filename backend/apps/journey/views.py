"""Journey helper endpoints: POST-only, unauthenticated, throttled.

The agent is stateless per request: follow-up context (candidate
stop ids, bounded history) travels in the request/response payload,
never in server memory, cache, or the database. Logs carry model,
provider, latency, and tools used — never questions, answers,
transcripts, or audio.
"""
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

import logging
import time

from django.conf import settings

from apps.journey.agent import run_journey
from apps.journey.providers import meta as provider
from apps.transport.api.errors import PlainBadRequest
from apps.transport.api.throttling import READ_THROTTLE_CLASSES
from apps.transport.models import Stop

logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 5 * 1024 * 1024
STOP_VOCABULARY_LIMIT = 100


def _bad_request(detail):
    return PlainBadRequest(detail)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes(READ_THROTTLE_CLASSES)
def journey(request):
    """Ask in everyday words; receive an answer, a disambiguation
    prompt, or an honest refusal (contracts/journey.md)."""
    if not isinstance(request.data, dict):
        raise _bad_request(
            "That journey question does not look right. "
            "Please send it as a JSON object and try again."
        )
    question = request.data.get("question")
    if not isinstance(question, str):
        raise _bad_request(
            "That journey question does not look right. "
            "Please ask in words and try again."
        )
    history = request.data.get("history", [])
    context = request.data.get("context", {})
    if not isinstance(history, list) or not isinstance(context, dict):
        raise _bad_request(
            "That journey question does not look right. "
            "Please ask in words and try again."
        )
    payload, _tools_used = run_journey(
        question=question, history=history, context=context
    )
    return Response(payload)


def _stop_vocabulary():
    """Stop names for transcription vocabulary biasing (capped).

    The stop table carries no frequency signal, so the first names in
    alphabetical order stand in for the highest-frequency names.
    """
    names = (
        Stop.objects.order_by("name")
        .values_list("name", flat=True)
        .distinct()[:STOP_VOCABULARY_LIMIT]
    )
    return ", ".join(name for name in names if name)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes(READ_THROTTLE_CLASSES)
def transcribe(request):
    """Voice input mode only: audio in, editable transcript out.

    The audio bytes are used for this call only and never stored:
    not on disk, database, cache, or logs (contracts/transcribe.md).
    """
    upload = request.FILES.get("audio")
    if upload is None:
        raise PlainBadRequest(
            "We could not hear a journey question. "
            "Please record it and try again."
        )
    try:
        size = upload.size
    except (AttributeError, ValueError):
        size = None
    if size is not None and size > MAX_AUDIO_BYTES:
        raise PlainBadRequest(
            "That recording is too long. "
            "Please keep it short and try again."
        )
    audio = upload.read(MAX_AUDIO_BYTES + 1)
    if not audio or len(audio) > MAX_AUDIO_BYTES:
        raise PlainBadRequest(
            "We could not transcribe that audio. Please try again."
        )
    started = time.monotonic()
    try:
        result = provider.transcribe_audio(
            audio_bytes=audio,
            filename=upload.name or "question.webm",
            prompt=_stop_vocabulary(),
        )
    except Exception:
        logger.exception("journey transcription failed")
        raise PlainBadRequest(
            "We could not transcribe that audio. Please try again."
        )
    if isinstance(result, str):
        text = result
    else:
        text = getattr(result, "text", "") or ""
    if not text.strip():
        raise PlainBadRequest(
            "We could not transcribe that audio. Please try again."
        )
    latency_ms = int((time.monotonic() - started) * 1000)
    model = getattr(settings, "TRANSCRIBE_MODEL", "muse-voice-transcribe-1.0")
    provider_name = getattr(settings, "JOURNEY_MODEL_PROVIDER", "meta")
    logger.info(
        "journey-transcribe model=%s provider=%s latency_ms=%d",
        model,
        provider_name,
        latency_ms,
    )
    return Response(
        {
            "transcript": text.strip(),
            "meta": {
                "model": model,
                "provider": provider_name,
                "latency_ms": latency_ms,
            },
        }
    )
