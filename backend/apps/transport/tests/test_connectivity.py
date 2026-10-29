"""Direct-connectivity contract tests (US4).

Covers spec SC-006/SC-007: forward-order routes returned once with
positions and evidence, reverse-only routes excluded, empty envelope
for unconnected pairs, resolvable evidence links, no time or
transfer content, the shared envelope, and plain-language errors
for bad stop ids.
"""
from rest_framework.test import APIClient

from . import factories as f
from .factories import ApiTestCase


class ConnectivityTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-connectivity")
        cls.master = f.make_master(
            cls.import_run, 41, "Loop", operator="KSRTC",
            network="Kochi",
        )
        cls.a = f.make_stop(cls.import_run, 401, "A", 10.0, 76.3)
        cls.b = f.make_stop(cls.import_run, 402, "B", 10.01, 76.31)
        cls.c = f.make_stop(cls.import_run, 403, "C", 10.02, 76.32)
        cls.route = f.make_route(
            cls.import_run, 401, "A-B-C", from_text="A",
            to_text="C",
        )
        f.link_master(cls.import_run, cls.master, cls.route, 1)
        f.link_stop(cls.import_run, cls.route, cls.a, 1)
        f.link_stop(cls.import_run, cls.route, cls.b, 2)
        f.link_stop(cls.import_run, cls.route, cls.c, 3)
        # Withheld carrier of the same stops: never returned.
        cls.ghost_master = f.make_master(cls.import_run, 42, "G")
        cls.ghost = f.make_route(
            cls.import_run, 402, "Ghost A-C", from_text="A",
            to_text="C", quarantined=True,
        )
        f.link_master(cls.import_run, cls.ghost_master, cls.ghost, 1)
        f.link_stop(cls.import_run, cls.ghost, cls.a, 1)
        f.link_stop(cls.import_run, cls.ghost, cls.c, 2)

    def setUp(self):
        self.client = APIClient()

    def test_forward_pair_returns_route_once_with_evidence(self):
        body = self.client.get("/api/v1/connectivity/", {
            "from": self.a.id, "to": self.c.id}).json()
        self.assertEqual(body["count"], 1)
        row = body["results"][0]
        self.assertEqual(row["id"], self.route.id)
        self.assertEqual(
            (row["from_position"], row["to_position"]), (1, 3))
        self.assertEqual(
            row["evidence"], f"/api/v1/routes/{self.route.id}/")
        evidence = self.client.get(row["evidence"])
        self.assertEqual(evidence.status_code, 200)

    def test_reverse_pair_excludes_forward_only_route(self):
        body = self.client.get("/api/v1/connectivity/", {
            "from": self.c.id, "to": self.a.id}).json()
        self.assertEqual((body["count"], body["results"]), (0, []))

    def test_withheld_route_never_returned(self):
        body = self.client.get("/api/v1/connectivity/", {
            "from": self.a.id, "to": self.c.id}).json()
        ids = [r["id"] for r in body["results"]]
        self.assertNotIn(self.ghost.id, ids)

    def test_response_carries_no_times_or_transfers(self):
        import json
        body = self.client.get("/api/v1/connectivity/", {
            "from": self.a.id, "to": self.b.id}).json()
        text = json.dumps(body).lower()
        for token in ("depart", "arriv", "duration", "frequency",
                      "transfer", "change", "minute"):
            self.assertNotIn(token, text)

    def test_bad_ids_are_plain_400(self):
        unknown = 10 ** 9
        cases = [
            {},
            {"from": self.a.id},
            {"to": self.b.id},
            {"from": self.a.id, "to": self.a.id},
            {"from": "abc", "to": self.b.id},
            {"from": self.a.id, "to": unknown},
            {"from": unknown, "to": self.b.id},
        ]
        for params in cases:
            response = self.client.get("/api/v1/connectivity/", params)
            self.assertEqual(response.status_code, 400, params)
            self.assertEqual(set(response.json()), {"detail"}, params)

    def test_shared_envelope_fields(self):
        body = self.client.get("/api/v1/connectivity/", {
            "from": self.a.id, "to": self.c.id}).json()
        self.assertEqual(
            set(body),
            {"count", "results", "total_pages", "current_page",
             "page_size"},
        )
