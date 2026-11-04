"""Feedback contract tests (017): 201 + receipt, links, journey header."""
import re

from rest_framework.test import APIClient

from apps.feedback.models import FeedbackReport
from apps.transport.tests import factories as f
from apps.transport.tests.factories import ApiTestCase


class FeedbackContractTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-feedback")
        cls.route = f.make_route(cls.import_run, 911, "Aluva Direct")
        cls.stop = f.make_stop(cls.import_run, 912, "Kaloor", 9.99, 76.29)

    def post(self, body):
        return APIClient().post("/api/v1/feedback/", body, format="json")

    def test_contextual_report_returns_receipt_and_links(self):
        response = self.post({
            "category": "incorrect",
            "message": "This route skips Kaloor in the evening.",
            "route_id": self.route.id,
            "stop_id": self.stop.id,
            "journey": {
                "from_name": "Aluva",
                "to_name": "Fort Kochi",
                "question": "How do I get there?",
            },
        })
        self.assertEqual(response.status_code, 201)
        reference = response.data["reference"]
        self.assertRegex(reference, r"^FB-[A-Z0-9]{8}$")
        self.assertIn("reference", response.data.get("receipt", ""))
        report = FeedbackReport.objects.get(reference=reference)
        self.assertEqual(report.route_id, self.route.id)
        self.assertEqual(report.stop_id, self.stop.id)
        self.assertEqual(report.status, "new")
        self.assertIn("Journey: Aluva \u2192 Fort Kochi", report.message)
        self.assertIn("Asked: How do I get there?", report.message)

    def test_general_report_without_context(self):
        response = self.post({"category": "missing", "message": "No stop named here."})
        self.assertEqual(response.status_code, 201)
        report = FeedbackReport.objects.get(reference=response.data["reference"])
        self.assertIsNone(report.route_id)
        self.assertIsNone(report.stop_id)
