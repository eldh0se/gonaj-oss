"""Server-side Meta model client (OpenAI SDK, backend only).

The model key never leaves the server: it appears in no response,
log, or frontend bundle. Tests stub :func:`complete_with_tools` and
:func:`transcribe_audio`, so no network or key is needed there.
"""
import logging

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
    except (APITimeoutError, APIConnectionError) as exc:
        logger.warning(
            "journey model %s failed once (%s); retrying",
            label,
            type(exc).__name__,
        )
        return call()


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


def transcribe_audio(*, audio_bytes, filename="question.webm", prompt=""):
    """Transcribe journey audio via the declared voice model.

    The audio bytes are used for this call only; nothing is stored.
    ``prompt`` carries optional vocabulary biasing (stop names) so
    dictation preserves stop spellings.
    """
    client = model_client()
    kwargs = {
        "model": getattr(
            settings, "TRANSCRIBE_MODEL", "muse-voice-transcribe-1.0"
        ),
        "file": (filename, audio_bytes),
        "language": "en",
    }
    if prompt:
        kwargs["prompt"] = prompt
    return _with_one_retry(
        "transcribe", lambda: client.audio.transcriptions.create(**kwargs)
    )
