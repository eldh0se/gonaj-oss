"""US4 backend throttle test (T016): over-budget POST → 429 + Retry-After."""

from django.test import override_settings
from rest_framework.test import APIClient

from apps.feedback.models import FeedbackReport
from apps.transport.tests.factories import ApiTestCase

URL = "/api/v1/feedback/"
GOOD = {"category": "other", "message": "General remark."}

LOW_FEEDBACK_RATES = {
    "EXCEPTION_HANDLER": "apps.transport.api.errors.plain_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "feedback_min": "2/min",
        "feedback_day": "1000/day",
    },
}


@override_settings(REST_FRAMEWORK=LOW_FEEDBACK_RATES)
class FeedbackThrottleTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def post(self):
        return self.client.post(URL, GOOD, format="json",
                                REMOTE_ADDR="10.7.7.7")

    def test_over_budget_returns_429_with_retry_after(self):
        assert self.post().status_code == 201
        assert self.post().status_code == 201
        denied = self.post()
        assert denied.status_code == 429
        assert denied.json() == {
            "detail": "Too many requests. "
                      "Please wait a moment and try again.",
        }
        assert "Retry-After" in denied
        assert FeedbackReport.objects.count() == 2

    def test_rejected_requests_never_consume_budget(self):
        bad = self.client.post(URL, {"category": "bogus", "message": ""},
                               format="json", REMOTE_ADDR="10.7.7.8")
        assert bad.status_code == 400
        # Both budget slots are still free: the 400 never reached
        # check_budgets, so two valid posts still succeed.
        assert self.client.post(URL, GOOD, format="json",
                                REMOTE_ADDR="10.7.7.8").status_code == 201
        assert self.client.post(URL, GOOD, format="json",
                                REMOTE_ADDR="10.7.7.8").status_code == 201
        denied = self.client.post(URL, GOOD, format="json",
                                  REMOTE_ADDR="10.7.7.8")
        assert denied.status_code == 429
