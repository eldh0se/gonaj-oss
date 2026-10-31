"""Log redaction filter (specs/007-debug-production-logging, FR-006/FR-007).

Scrub secret, credential, token, and private-content values from log
records in every mode. The filter is key-based: mapping arguments
whose key names a protected class are replaced with "***" before the
record is emitted. Positional arguments pass through untouched, so
call sites MUST keep questions, answers, transcripts, audio, and key
material out of positional values (see contracts/logging.md section 5).
"""
import logging

REDACTED = "***"

_KEY_HINTS = (
    "key",
    "secret",
    "password",
    "token",
    "authorization",
    "audio",
    "transcript",
    "question",
    "answer",
)


def _scrub_mapping(mapping):
    return {
        name: (
            REDACTED
            if any(hint in str(name).lower() for hint in _KEY_HINTS)
            else value
        )
        for name, value in mapping.items()
    }


class RedactionFilter(logging.Filter):
    """Replace protected mapping-argument values with "***"."""

    def filter(self, record):
        if isinstance(record.args, dict):
            record.args = _scrub_mapping(record.args)
        return True
