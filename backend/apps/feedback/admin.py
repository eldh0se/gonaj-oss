"""Curator triage surface for anonymous passenger feedback (017 US3).

Listing only: all fields readonly except `status`, which moves
new → reviewed|dismissed (re-triage allowed both ways).
"""

from django.contrib import admin

from .models import FeedbackReport


@admin.register(FeedbackReport)
class FeedbackReportAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "category",
        "route",
        "stop",
        "status",
        "created_at",
    )
    list_filter = ("status", "category")
    search_fields = ("reference", "message")
    readonly_fields = (
        "reference",
        "category",
        "message",
        "route",
        "stop",
        "created_at",
        "updated_at",
    )
