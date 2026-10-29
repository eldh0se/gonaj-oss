"""Query-count regression tests (T032).

Proves the plan's no-per-row-queries goal at factory scale: every
read completes in a small bounded number of queries regardless of
result size, so map browsing stays single-query-shaped.
"""
from rest_framework.test import APIClient

from . import factories as f
from .factories import ApiTestCase


class QueryCountTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-perf")
        cls.master = f.make_master(cls.import_run, 71, "M")
        cls.stops = [
            f.make_stop(cls.import_run, 700 + i, f"Stop {i}",
                        10.0 + i * 0.001, 76.3)
            for i in range(12)
        ]
        cls.route = f.make_route(
            cls.import_run, 701, "Long Run", from_text="A",
            to_text="B",
        )
        f.link_master(cls.import_run, cls.master, cls.route, 1)
        for position, stop in enumerate(cls.stops, start=1):
            f.link_stop(cls.import_run, cls.route, stop, position)

    def setUp(self):
        self.client = APIClient()

    def test_routes_list_query_count(self):
        with self.assertNumQueries(2):
            response = self.client.get(
                "/api/v1/routes/", {"search": "Long"})
        self.assertEqual(response.status_code, 200)

    def test_stops_list_query_count(self):
        with self.assertNumQueries(2):
            response = self.client.get("/api/v1/stops/", {"search": "Stop"})
        self.assertEqual(response.status_code, 200)

    def test_route_detail_query_count(self):
        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1/routes/{self.route.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["stops"]), 12)

    def test_stop_detail_query_count(self):
        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1/stops/{self.stops[0].id}/")
        self.assertEqual(response.status_code, 200)

    def test_connectivity_query_count(self):
        with self.assertNumQueries(3):
            response = self.client.get("/api/v1/connectivity/", {
                "from": self.stops[0].id, "to": self.stops[-1].id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
