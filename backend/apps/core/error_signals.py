"""Uncaught-exception triage records (specs/007-debug-production-logging).

Django's own ``django.request`` log covers uncaught 500s with the
path, but not the method. This receiver adds the missing piece —
one ERROR entry with method, path, and traceback per uncaught
request exception (FR-005, contract G-1) — for every app, since
uncaught failures can surface on any endpoint.
"""
import logging

from django.core.signals import got_request_exception
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(got_request_exception, dispatch_uid="gonaj-log-uncaught-500")
def log_uncaught_exception(sender, request, **kwargs):
    logger.exception(
        "api error status=%d method=%s path=%s",
        500,
        request.method,
        request.path,
    )
