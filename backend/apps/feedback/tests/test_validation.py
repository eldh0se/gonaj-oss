"""US4 backend edge tests (T015): every bad submit fails plainly with 400."""

from django.test import TestCase
from rest_framework.test import APIClient

from apps.feedback.models import FeedbackReport

URL = "/api/v1/feedback/"
GOOD = {"category": "incorrect", "message": "Wrong terminus."}


def post(body, **kwargs):
    return APIClient().post(URL, body, format="json", **kwargs)


class FeedbackValidationTest(TestCase):
    def test_non_object_body_is_400(self):
        response = post(["not", "an", "object"])
        assert response.status_code == 400
        assert FeedbackReport.objects.count() == 0

    def test_bad_category_is_400(self):
        response = post({**GOOD, "category": "broken"})
        assert response.status_code == 400
        assert FeedbackReport.objects.count() == 0

    def test_empty_and_whitespace_message_is_400(self):
        for message in ("", "   "):
            response = post({**GOOD, "message": message})
            assert response.status_code == 400, repr(message)
        assert FeedbackReport.objects.count() == 0

    def test_overlong_message_is_400(self):
        response = post({**GOOD, "message": "x" * 2001})
        assert response.status_code == 400
        assert FeedbackReport.objects.count() == 0

    def test_non_integer_ids_are_invalid_reference(self):
        for field in ("route_id", "stop_id"):
            response = post({**GOOD, field: "abc"})
            assert response.status_code == 400, field
            assert response.json().get("code") == "invalid-reference", field
        assert FeedbackReport.objects.count() == 0

    def test_unknown_ids_are_invalid_reference_never_500(self):
        for field in ("route_id", "stop_id"):
            response = post({**GOOD, field: 99999})
            assert response.status_code == 400, field
            assert response.json().get("code") == "invalid-reference", field
        assert FeedbackReport.objects.count() == 0

    def test_supplied_non_writable_fields_are_400(self):
        for field in ("reference", "status", "created_at", "updated_at"):
            response = post({**GOOD, field: "FB-FORBIDDEN"})
            assert response.status_code == 400, field
        assert FeedbackReport.objects.count() == 0

    def test_journey_must_stay_an_object(self):
        response = post({**GOOD, "journey": ["from", "to"]})
        assert response.status_code == 400
        assert FeedbackReport.objects.count() == 0

    def test_identical_posts_each_create_a_record(self):
        # No backend dedupe by design: the single-record guarantee for
        # one user submit lives in the dialog pending guard (spec FR-004),
        # so two distinct valid POSTs are two reports.
        first = post(GOOD)
        second = post(GOOD)
        assert first.status_code == 201
        assert second.status_code == 201
        assert FeedbackReport.objects.count() == 2
        assert first.json()["reference"] != second.json()["reference"]
