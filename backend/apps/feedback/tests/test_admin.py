"""US3: curator triage happens in Django Admin (spec US3, contracts C1)."""

from django.contrib import admin
from django.test import TestCase

from apps.feedback.models import FeedbackReport


class FeedbackAdminTest(TestCase):
    def test_admin_lists_report_and_status_transitions_persist(self):
        # Fails until FeedbackReportAdmin is registered (T014).
        model_admin = admin.site._registry.get(FeedbackReport)
        assert model_admin is not None, "FeedbackReport not registered in Admin"

        report = FeedbackReport.objects.create(
            reference="FB-ADMIN001",
            category="incorrect",
            message="Wrong terminus.",
        )
        assert report.status == "new"

        list_display = list(model_admin.list_display)
        for field in (
            "reference",
            "category",
            "route",
            "stop",
            "status",
            "created_at",
        ):
            assert field in list_display, f"{field} missing from list_display"

        for status in ("reviewed", "dismissed", "reviewed"):
            report.status = status
            report.save()
            assert FeedbackReport.objects.get(pk=report.pk).status == status

        readonly = set(getattr(model_admin, "readonly_fields", ()))
        for field in ("reference", "category", "message", "created_at"):
            assert field in readonly, f"{field} should be readonly"
        assert "status" not in readonly, "status must stay editable"
