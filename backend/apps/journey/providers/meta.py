"""Server-side Meta model client (backend only).

Chat uses the OpenAI SDK against the declared Meta endpoint; voice
transcription uses direct HTTPS against the Meta ASR endpoint (the
SDK's fixed ``audio.transcriptions`` shape is incompatible with it).
The model key never leaves the server: it appears in no response,
log, or frontend bundle. Tests stub :func:`complete_with_tools` and
:func:`transcribe_audio`, so no network or key is needed there.
"""
import json
import logging

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openai import APIConnectionError, APITimeoutError, OpenAI

logger = logging.getLogger(__name__)


def _api_key():
    key = getattr(settings, "MODEL_API_KEY", "")
    if not key:
        raise ImproperlyConfigured(
            "Missing required environment variable: MODEL_API_KEY"
        )
    return key


def model_client():
    """Authenticated SDK client for the declared Meta endpoint."""
    return OpenAI(
        base_url=getattr(
            settings, "MODEL_API_BASE_URL", "https://api.meta.ai/v1"
        ),
        api_key=_api_key(),
        timeout=getattr(settings, "MODEL_TIMEOUT_SECONDS", 20),
    )


def _with_one_retry(label, call):
    """Run ``call`` once, retrying a single time on timeout/connection
    errors (research: bounded retries, reads only)."""
    try:
        return call()
    except (
        APITimeoutError,
        APIConnectionError,
        httpx.TimeoutException,
        httpx.TransportError,
    ) as exc:
        logger.warning(
            "journey model %s failed once (%s); retrying",
            label,
            type(exc).__name__,
        )
        return call()


TRANSCRIBE_MODEL = "muse-voice-transcribe-1.0"
TRANSCRIBE_URL = "https://api.meta.ai/v1/asr/transcribe"
TRANSCRIBE_TIMEOUT_S = 20.0


def complete_with_tools(*, model, messages, tools):
    """One tool-loop turn against the declared chat model."""
    client = model_client()
    return _with_one_retry(
        "chat",
        lambda: client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
        ),
    )


def transcribe_audio(*, audio_bytes, filename="question.wav", keywords=()):
    """Transcribe journey audio via the Meta ASR endpoint.

    Direct HTTPS POST (multipart ``request`` JSON part plus the
    ``audio/wav`` part). Returns the transcript text (possibly empty —
    the view turns that into the plain cannot-transcribe message).
    Raises on transport errors (after one transient retry) and
    non-200 responses; the view converts those to the same plain
    message. The audio bytes are used for this call only; nothing is
    stored. ``keywords`` carries vocabulary biasing (stop names) so
    dictation preserves stop spellings.
    """

    def call():
        response = httpx.post(
            TRANSCRIBE_URL,
            files={
                "request": (
                    None,
                    json.dumps(
                        {
                            "model": getattr(
                                settings,
                                "TRANSCRIBE_MODEL",
                                TRANSCRIBE_MODEL,
                            ),
                            "audioEncoding": "WAV",
                            "mode": "PUSH_TO_TALK",
                            "languageBias": ["English"],
                            "keywords": list(keywords or []),
                        }
                    ),
                    "application/json",
                ),
                "audio": (
                    filename or "question.wav",
                    bytes(audio_bytes or b""),
                    "audio/wav",
                ),
            },
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {_api_key()}",
            },
            timeout=TRANSCRIBE_TIMEOUT_S,
        )
        if response.status_code != 200:
            raise RuntimeError(
                "transcribe failed: "
                f"{response.status_code or 'no status'}"
            )
        return response

    response = _with_one_retry("transcribe", call)
    try:
        body = response.json()
    except (TypeError, ValueError):
        raise RuntimeError("transcribe failed: bad response")
    if not isinstance(body, dict):
        raise RuntimeError("transcribe failed: bad response")
    envelope = body.get("TranscribeResponse", body)
    if not isinstance(envelope, dict):
        return ""
    text = envelope.get("transcript", "")
    return text.strip() if isinstance(text, str) else ""
