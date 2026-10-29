"""Stops list and stop detail contract tests (US2, US3).

Covers spec SC-003/SC-004/SC-005/SC-007: name search, closed-bound
bbox lookup with an edge stop included, search+bbox exclusivity,
zoom_in and empty outcomes, always-present coordinates and serving
routes, serving-routes limited to servable routes, and plain
not-found responses.
"""
from rest_framework.test import APIClient

from . import factories as f
from .factories import ApiTestCase


class StopListTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-stops")
        cls.master = f.make_master(
            cls.import_run, 21, "North Line", operator="KSRTC",
            network="Kochi",
        )
        cls.hub = f.make_stop(cls.import_run, 301, "North Hub", 10.0, 76.3)
        cls.edge = f.make_stop(
            cls.import_run, 302, "North Edge", 10.05, 76.3)
        cls.far = f.make_stop(
            cls.import_run, 303, "South Terminal", 9.9, 76.25)
        cls.route = f.make_route(
            cls.import_run, 301, "North Shuttle", from_text="North",
            to_text="South",
        )
        f.link_master(cls.import_run, cls.master, cls.route, 1)
        f.link_stop(cls.import_run, cls.route, cls.hub, 1)
        f.link_stop(cls.import_run, cls.route, cls.edge, 2)

    def setUp(self):
        self.client = APIClient()

    def test_search_by_name_fragment(self):
        body = self.client.get(
            "/api/v1/stops/", {"search": "north"}).json()
        self.assertEqual(
            {r["id"] for r in body["results"]},
            {self.hub.id, self.edge.id},
        )
        self.assertEqual(body["count"], 2)
        self.assertEqual(body["status"], "ok")

    def test_neither_param_is_paginated_browse_all(self):
        body = self.client.get("/api/v1/stops/").json()
        self.assertEqual(body["count"], 3)
        self.assertEqual(body["status"], "ok")

    def test_bbox_returns_inside_including_edge(self):
        body = self.client.get("/api/v1/stops/", {
            "bbox": "76.29,9.99,76.31,10.05"}).json()
        self.assertEqual(
            {r["id"] for r in body["results"]},
            {self.hub.id, self.edge.id},
        )

    def test_bbox_excludes_outside(self):
        body = self.client.get("/api/v1/stops/", {
            "bbox": "76.29,9.99,76.31,10.0"}).json()
        self.assertEqual(
            [r["id"] for r in body["results"]], [self.hub.id])

    def test_search_and_bbox_together_is_plain_400(self):
        response = self.client.get("/api/v1/stops/", {
            "search": "north", "bbox": "76.0,9.0,77.0,11.0"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"detail"})

    def test_malformed_bboxes_are_plain_400(self):
        for bbox in ("76.3,10.0", "a,b,c,d", "77.0,9.0,76.0,11.0",
                     "200.0,9.0,201.0,10.0"):
            response = self.client.get("/api/v1/stops/", {"bbox": bbox})
            self.assertEqual(response.status_code, 400, bbox)
            self.assertEqual(set(response.json()), {"detail"}, bbox)

    def test_oversized_area_returns_zoom_in_with_zero_stops(self):
        body = self.client.get("/api/v1/stops/", {
            "bbox": "76.0,9.0,77.0,11.0"}).json()
        self.assertEqual(
            (body["status"], body["count"], body["results"]),
            ("zoom_in", 0, []),
        )
        self.assertIn("zoom", body["detail"].lower())

    def test_valid_empty_area_returns_empty_status(self):
        body = self.client.get("/api/v1/stops/", {
            "bbox": "0.0,0.0,0.1,0.1"}).json()
        self.assertEqual(
            (body["status"], body["count"], body["results"]),
            ("empty", 0, []),
        )


class StopDetailTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-stop-detail")
        cls.master = f.make_master(cls.import_run, 31, "M", operator="KSRTC")
        cls.hub = f.make_stop(cls.import_run, 311, "Hub", 10.0, 76.3)
        cls.lonely = f.make_stop(cls.import_run, 312, "Lonely", 10.1, 76.4)
        cls.only_withheld = f.make_stop(
            cls.import_run, 313, "Ghost Stop", 10.2, 76.5)
        cls.route = f.make_route(
            cls.import_run, 311, "Hub Run", from_text="Hub",
            to_text="Town",
        )
        f.link_master(cls.import_run, cls.master, cls.route, 1)
        f.link_stop(cls.import_run, cls.route, cls.hub, 1)
        cls.ghost = f.make_route(
            cls.import_run, 312, "Ghost", quarantined=True)
        f.link_stop(cls.import_run, cls.ghost, cls.only_withheld, 1)

    def setUp(self):
        self.client = APIClient()

    def test_detail_carries_coordinates_and_serving_routes(self):
        body = self.client.get(
            f"/api/v1/stops/{self.hub.id}/").json()
        self.assertEqual(
            set(body),
            {"id", "name", "name_ml", "lat", "lon", "serving_routes"},
        )
        self.assertEqual((body["lat"], body["lon"]), (10.0, 76.3))
        self.assertEqual(
            body["serving_routes"],
            [{"id": self.route.id, "name": "Hub Run"}],
        )

    def test_unserved_stop_returns_explicit_empty_list(self):
        body = self.client.get(
            f"/api/v1/stops/{self.lonely.id}/").json()
        self.assertEqual(body["serving_routes"], [])

    def test_stop_served_only_by_withheld_route_lists_empty(self):
        body = self.client.get(
            f"/api/v1/stops/{self.only_withheld.id}/").json()
        self.assertEqual(body["serving_routes"], [])

    def test_unknown_stop_is_plain_404(self):
        response = self.client.get("/api/v1/stops/99999999/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(set(response.json()), {"detail"})
        self.assertIn("stop", response.json()["detail"].lower())
