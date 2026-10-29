"""Shared list envelope pagination (FR-019).

Every list response (routes, stops, connectivity) uses exactly the
fields ``count``, ``results``, ``total_pages``, ``current_page`` and
``page_size``. The default page size is 20 and requests above 100
are served at 100. A page beyond the end is an empty ``results``
page with correct totals — never an error. Non-numeric or
non-positive ``page``/``page_size`` values produce the shared
plain-language 400, never a 500.
"""
import math

from rest_framework.pagination import BasePagination

from .errors import PlainBadRequest


class SharedEnvelopePagination(BasePagination):
    default_page_size = 20
    max_page_size = 100

    def _page_param(self, request, name, default):
        raw = request.query_params.get(name, default)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            raise PlainBadRequest(
                "That page request does not look right. "
                "Please use a page number of 1 or more, and a page "
                "size between 1 and 100."
            )
        if value < 1:
            raise PlainBadRequest(
                "That page request does not look right. "
                "Please use a page number of 1 or more, and a page "
                "size between 1 and 100."
            )
        return value

    def paginate_queryset(self, queryset, request, view=None):
        self.page_number = self._page_param(request, "page", 1)
        requested_size = self._page_param(
            request, "page_size", self.default_page_size
        )
        self.page_size = min(requested_size, self.max_page_size)
        self.count = queryset.count()
        self.total_pages = (
            math.ceil(self.count / self.page_size) if self.count else 0
        )
        start = (self.page_number - 1) * self.page_size
        end = start + self.page_size
        self.page_items = list(queryset[start:end])
        return self.page_items

    def get_paginated_response(self, data):
        from rest_framework.response import Response

        return Response(
            {
                "count": self.count,
                "results": data,
                "total_pages": self.total_pages,
                "current_page": self.page_number,
                "page_size": self.page_size,
            }
        )
