"""Read-only and open-access tests (T033, FR-001–FR-003, SC-008).

Write verbs are refused without changing data; all five reads work
with no credentials or cookies and introduce no tracking headers.
"""
from rest_framework.test import APIClient

from apps.transport.models import Route, Stop

from . import factories as f
from .factories import ApiTestCase


class ReadOnlyTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-access")
        cls.master = f.make_master(cls.import_run, 61, "M")
        cls.a = f.make_stop(cls.import_run, 601, "A", 10.0, 76.3)
        cls.route = f.make_route(
            cls.import_run, 601, "A-B", from_text="A", to_text="B")
        f.link_master(cls.import_run, cls.master, cls.route, 1)
        f.link_stop(cls.import_run, cls.route, cls.a, 1)

    def setUp(self):
        self.client = APIClient()

    def test_write_verbs_refused_without_data_change(self):
        routes_before = Route.objects.count()
        stops_before = Stop.objects.count()
        paths = [
            "/api/v1/routes/",
            f"/api/v1/routes/{self.route.id}/",
            "/api/v1/stops/",
            f"/api/v1/stops/{self.a.id}/",
            "/api/v1/connectivity/",
        ]
        for path in paths:
            for method in ("post", "put", "patch", "delete"):
                response = getattr(self.client, method)(path, {})
                # Authentication is disabled on these views, so
                # refused verbs reach the GET-only check directly.
                self.assertEqual(response.status_code, 405,
                                 (method, path))
                self.assertEqual(set(response.json()), {"detail"},
                                 (method, path))
        self.assertEqual(Route.objects.count(), routes_before)
        self.assertEqual(Stop.objects.count(), stops_before)

    def test_unknown_api_paths_are_plain_json_404(self):
        for path in ("/api/v1/routes/abc/", "/api/v1/stops/xyz/",
                     "/api/v1/no-such-endpoint/"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404, path)
            self.assertEqual(response.json(), {
                "detail": "We could not find what you asked for. "
                          "Please check the link and try again.",
            }, path)

    def test_reads_need_no_credentials_or_cookies(self):
        paths = [
            "/api/v1/routes/",
            f"/api/v1/routes/{self.route.id}/",
            "/api/v1/stops/",
            f"/api/v1/stops/{self.a.id}/",
            f"/api/v1/connectivity/?from={self.a.id}&to={self.a.id}",
        ]
        for path in paths:
            response = self.client.get(path)
            self.assertNotEqual(response.status_code, 401, path)
            self.assertNotEqual(response.status_code, 403, path)
            self.assertNotIn("Set-Cookie", response, path)
