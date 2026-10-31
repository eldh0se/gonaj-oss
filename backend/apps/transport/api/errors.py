"""Plain-language error rendering (FR-015, FR-020).

Every error across the transport API is a single plain-language
sentence a passenger can act on. No field names, database messages,
OSM identifiers, or stack details ever appear in a response body.
"""
import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class PlainBadRequest(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = (
        "That request does not look right. "
        "Please check the values and try again."
    )


class PlainNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = (
        "We could not find what you asked for. "
        "Please check the link and try again."
    )


class PlainMethodNotAllowed(APIException):
    status_code = status.HTTP_405_METHOD_NOT_ALLOWED
    default_detail = (
        "This service is read-only. "
        "Please use a view link instead of sending changes."
    )


logger = logging.getLogger(__name__)


def _request_context(context):
    """Method + path for error records (FR-005).

    Uses ``request.path`` (never the query string), so routine
    records carry no user-supplied content at all.
    """
    request = context.get("request") if isinstance(context, dict) else None
    if request is None:
        return "?", "?"
    return request.method, request.path


def api_not_found(request, exception=None):
    """URL-resolver 404s under /api/* (T037).

    DRF's handler only sees exceptions raised inside views; unknown
    API paths and non-integer detail ids never reach a view. This
    keeps those responses in the shared plain-language shape while
    leaving non-API 404 behaviour untouched.
    """
    from django.http import JsonResponse
    from django.views.defaults import page_not_found

    if request.path.startswith("/api/"):
        logger.warning(
            "api client_error status=%d method=%s path=%s",
            404,
            request.method,
            request.path,
        )
        return JsonResponse(
            {
                "detail": "We could not find what you asked for. "
                "Please check the link and try again."
            },
            status=404,
        )
    return page_not_found(request, exception)


def plain_exception_handler(exc, context):
    """DRF exception handler: flatten every error to ``{"detail"}``."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data.get("detail", None) if isinstance(
        response.data, dict
    ) else None
    if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        # Never leak DRF's technical throttle wording; the contract
        # fixes this sentence and the Retry-After header carries the
        # wait time (FR-022).
        message = "Too many requests. Please wait a moment and try again."
    elif isinstance(detail, str):
        message = detail
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        message = PlainNotFound.default_detail
    elif response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        message = PlainMethodNotAllowed.default_detail
    elif 400 <= response.status_code < 500:
        message = PlainBadRequest.default_detail
    else:
        message = (
            "Something went wrong on our side. "
            "Please try again in a little while."
        )
    response.data = {"detail": message}
    method, path = _request_context(context)
    if response.status_code >= 500:
        logger.exception(
            "api error status=%d method=%s path=%s",
            response.status_code,
            method,
            path,
        )
    elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS or (
        400 <= response.status_code < 500
    ):
        logger.warning(
            "api client_error status=%d method=%s path=%s",
            response.status_code,
            method,
            path,
        )
    return response
