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
logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 5 * 1024 * 1024


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


def _wav_params(audio):
    """(channels, sample_rate, bits) for PCM WAV bytes, else None."""
    import struct

    if (
        len(audio) < 44
        or audio[0:4] != b"RIFF"
        or audio[8:12] != b"WAVE"
    ):
        return None
    offset = 12
    while offset + 8 <= len(audio):
        chunk_id = audio[offset : offset + 4]
        (chunk_size,) = struct.unpack_from("<I", audio, offset + 4)
        body = offset + 8
        if chunk_id == b"fmt " and chunk_size >= 16:
            (
                audio_format,
                channels,
                sample_rate,
                _byte_rate,
                _block_align,
                bits,
            ) = struct.unpack_from("<HHIIHH", audio, body)
            if audio_format != 1:
                return None
            return channels, sample_rate, bits
        offset = body + chunk_size + (chunk_size % 2)
    return None


def _normalized_wav_filename(name):
    """Force a ``*.wav`` filename, defaulting to ``question.wav``."""
    stem = (name or "").rsplit(".", 1)[0].strip() or "question"
    return f"{stem}.wav"


def _is_wav_upload(upload, audio):
    """True when the upload claims WAV and the bytes parse as PCM WAV."""
    name = (getattr(upload, "name", "") or "").lower()
    if not name.endswith(".wav"):
        return False
    if getattr(upload, "content_type", "") not in (
        "audio/wav",
        "audio/x-wav",
    ):
        return False
    params = _wav_params(audio)
    if params is None:
        return False
    channels, sample_rate, bits = params
    return channels == 1 and bits == 16 and sample_rate in (16000, 24000)


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
    if not _is_wav_upload(upload, audio):
        raise PlainBadRequest(
            "We could not transcribe that audio. Please try again."
        )
    started = time.monotonic()
    try:
        result = provider.transcribe_audio(
            audio_bytes=audio,
            filename=_normalized_wav_filename(
                getattr(upload, "name", "")
            ),
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
