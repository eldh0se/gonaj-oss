"""Routes list and route detail contract tests (US1, US3).

Covers spec SC-001/SC-002/SC-005/SC-007: browse-all, the four
search fields, exact operator/network filters, stored order and
duplicate preservation, hidden internal fields, the shared
envelope, ordered detail with origin/terminus, explicit empty
membership, and plain-language not-found responses.
"""
from rest_framework.test import APIClient

from . import factories as f
from .factories import ApiTestCase


class RouteListTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot()
        cls.master1 = f.make_master(
            cls.import_run, 1, "Ernakulam \u2014 Fort Kochi",
            operator="KSRTC", network="Kochi",
        )
        cls.master2 = f.make_master(
            cls.import_run, 2, "Ernakulam \u2014 Fort Kochi",
            operator="Private", network=None,
        )
        cls.s1 = f.make_stop(
            cls.import_run, 101, "Ernakulam South", 9.968, 76.29,
            name_ml="\u0d0e\u0d31\u0d23\u0d3e\u0d15\u0d41\u0d33\u0d02",
        )
        cls.s2 = f.make_stop(cls.import_run, 102, "Fort Kochi", 9.965, 76.242)
        cls.s3 = f.make_stop(cls.import_run, 103, "Mattancherry", 9.958, 76.26)
        cls.s4 = f.make_stop(cls.import_run, 104, "Depot Gate", 9.99, 76.30)
        cls.r1 = f.make_route(
            cls.import_run, 201, "EKM-Fort Kochi AC",
            from_text="Ernakulam", to_text="Fort Kochi",
        )
        f.link_master(cls.import_run, cls.master1, cls.r1, 1)
        f.link_stop(cls.import_run, cls.r1, cls.s1, 1)
        f.link_stop(cls.import_run, cls.r1, cls.s2, 2)
        cls.r2 = f.make_route(
            cls.import_run, 202, "EKM-Mattancherry Local",
            from_text="Ernakulam", to_text="Mattancherry",
        )
        f.link_master(cls.import_run, cls.master1, cls.r2, 2)
        f.link_stop(cls.import_run, cls.r2, cls.s1, 1)
        f.link_stop(cls.import_run, cls.r2, cls.s3, 2)
        cls.r3 = f.make_route(
            cls.import_run, 203, "Private Shuttle",
            from_text="A", to_text="B",
        )
        f.link_master(cls.import_run, cls.master2, cls.r3, 1)
        f.link_stop(cls.import_run, cls.r3, cls.s4, 1)
        # Withheld: quarantined platform-less route and orphan route.
        cls.r4 = f.make_route(cls.import_run, 204, "Ghost", quarantined=True)
        cls.r5 = f.make_route(cls.import_run, 205, "Orphan Line")

    def setUp(self):
        self.client = APIClient()

    def test_blank_search_returns_browse_all_in_envelope(self):
        response = self.client.get("/api/v1/routes/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            set(body), {"count", "results", "total_pages",
                        "current_page", "page_size"},
        )
        self.assertEqual(body["count"], 3)
        self.assertEqual(body["page_size"], 20)
        self.assertEqual(body["current_page"], 1)
        self.assertEqual(body["total_pages"], 1)
        # Stored order: master-membership position, then id
        # (r3 holds position 1 in its master, r2 holds position 2).
        self.assertEqual(
            [r["id"] for r in body["results"]],
            [self.r1.id, self.r3.id, self.r2.id],
        )

    def test_absent_and_whitespace_search_are_browse_all(self):
        for params in ({}, {"search": ""}, {"search": "   "}):
            response = self.client.get("/api/v1/routes/", params)
            self.assertEqual(response.json()["count"], 3, params)

    def test_search_by_name(self):
        body = self.client.get(
            "/api/v1/routes/", {"search": "Fort Kochi AC"}).json()
        self.assertEqual([r["id"] for r in body["results"]], [self.r1.id])

    def test_search_by_origin_is_case_insensitive(self):
        body = self.client.get(
            "/api/v1/routes/", {"search": "ernakulam"}).json()
        self.assertEqual(
            [r["id"] for r in body["results"]], [self.r1.id, self.r2.id])

    def test_search_by_destination(self):
        body = self.client.get(
            "/api/v1/routes/", {"search": "fort kochi"}).json()
        self.assertEqual([r["id"] for r in body["results"]], [self.r1.id])

    def test_search_by_served_stop_name(self):
        body = self.client.get(
            "/api/v1/routes/", {"search": "Mattancherry"}).json()
        self.assertEqual([r["id"] for r in body["results"]], [self.r2.id])

    def test_operator_filter_exact_and_partial(self):
        body = self.client.get(
            "/api/v1/routes/", {"operator": "KSRTC"}).json()
        self.assertEqual(
            [r["id"] for r in body["results"]], [self.r1.id, self.r2.id])
        body = self.client.get(
            "/api/v1/routes/", {"operator": "KSR"}).json()
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["results"], [])

    def test_network_filter_exact_and_case_sensitive(self):
        body = self.client.get(
            "/api/v1/routes/", {"network": "Kochi"}).json()
        self.assertEqual(
            [r["id"] for r in body["results"]], [self.r1.id, self.r2.id])
        body = self.client.get(
            "/api/v1/routes/", {"network": "kochi"}).json()
        self.assertEqual(body["count"], 0)

    def test_operator_filter_combines_with_search(self):
        body = self.client.get("/api/v1/routes/", {
            "search": "EKM-Mattancherry Local",
            "operator": "Private"}).json()
        self.assertEqual(body["count"], 0)

    def test_withheld_routes_never_listed(self):
        body = self.client.get("/api/v1/routes/").json()
        ids = [r["id"] for r in body["results"]]
        self.assertNotIn(self.r4.id, ids)
        self.assertNotIn(self.r5.id, ids)

    def test_route_result_shape_and_hidden_fields(self):
        row = self.client.get("/api/v1/routes/").json()["results"][0]
        self.assertEqual(
            set(row),
            {"id", "name", "origin", "destination", "operator", "network"},
        )
        self.assertEqual(row["origin"], "Ernakulam")
        self.assertEqual(row["operator"], "KSRTC")

    def test_pagination_pages_cap_and_beyond_end(self):
        body = self.client.get("/api/v1/routes/", {
            "page_size": 2, "page": 2}).json()
        self.assertEqual(
            (body["current_page"], body["page_size"], body["total_pages"]),
            (2, 2, 2),
        )
        self.assertEqual(len(body["results"]), 1)
        body = self.client.get(
            "/api/v1/routes/", {"page_size": 500}).json()
        self.assertEqual(body["page_size"], 100)
        self.assertLessEqual(len(body["results"]), 100)
        body = self.client.get("/api/v1/routes/", {"page": 9999}).json()
        self.assertEqual(
            (body["count"], body["results"], body["current_page"]),
            (3, [], 9999),
        )

    def test_invalid_pagination_is_plain_language_error(self):
        for params in ({"page": "abc"}, {"page": "0"}, {"page_size": "-5"}):
            response = self.client.get("/api/v1/routes/", params)
            self.assertEqual(response.status_code, 400, params)
            self.assertEqual(set(response.json()), {"detail"})


class PostgresOrderingTests(ApiTestCase):
    """Postgres-legality regression tests (T036).

    SQLite permits ORDER BY on a joined column under SELECT DISTINCT;
    PostgreSQL rejects it. The list orderings must therefore resolve
    to selected outputs (annotations), never to related-field joins.
    """

    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-ordering")
        cls.master = f.make_master(cls.import_run, 61, "M")
        cls.route = f.make_route(cls.import_run, 601, "R")
        f.link_master(cls.import_run, cls.master, cls.route, 1)

    def setUp(self):
        self.client = APIClient()

    def test_list_ordering_uses_selected_outputs_only(self):
        from apps.transport.api import views as api_views

        queryset = api_views.order_routes(
            api_views.routes_with_master_fields(
                api_views.servable_routes()))
        order_terms = list(queryset.query.order_by)
        self.assertTrue(order_terms)
        for term in order_terms:
            base = term.lstrip("-")
            self.assertTrue(
                base in queryset.query.annotation_select
                or base in [field.name for field in
                            queryset.model._meta.concrete_fields],
                f"ORDER BY {term} is not a selected output",
            )
        # Behaviour unchanged: stored order, duplicates preserved.
        body = self.client.get("/api/v1/routes/").json()
        self.assertEqual(body["count"], 1)

    def test_multi_master_route_resolves_to_one_row(self):
        other = f.make_master(self.import_run, 62, "M2")
        f.link_master(self.import_run, other, self.route, 1)
        response = self.client.get(f"/api/v1/routes/{self.route.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.route.id)


class RouteDetailTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-detail")
        cls.master = f.make_master(cls.import_run, 11, "M", operator="KSRTC")
        cls.other = f.make_master(cls.import_run, 12, "M2")
        cls.a = f.make_stop(cls.import_run, 111, "Alpha", 10.0, 76.3)
        cls.b = f.make_stop(cls.import_run, 112, "Beta", 10.01, 76.31)
        cls.route = f.make_route(
            cls.import_run, 211, "Alpha-Beta", from_text="Alpha",
            to_text="Beta",
        )
        f.link_master(cls.import_run, cls.master, cls.route, 1)
        f.link_stop(cls.import_run, cls.route, cls.a, 1)
        f.link_stop(cls.import_run, cls.route, cls.b, 2)
        # Single stop: both origin and terminus.
        cls.single = f.make_route(
            cls.import_run, 212, "Solo", from_text="Alpha", to_text="Alpha")
        f.link_master(cls.import_run, cls.master, cls.single, 2)
        f.link_stop(cls.import_run, cls.single, cls.a, 1)
        # Duplicate platform steps preserved in stored order.
        cls.dupe = f.make_route(
            cls.import_run, 213, "Looper", from_text="Alpha",
            to_text="Alpha")
        f.link_master(cls.import_run, cls.other, cls.dupe, 1)
        f.link_stop(cls.import_run, cls.dupe, cls.a, 1)
        f.link_stop(cls.import_run, cls.dupe, cls.a, 2)
        # Servable yet membership-empty route: explicit empty list.
        cls.empty = f.make_route(cls.import_run, 214, "Fresh")
        f.link_master(cls.import_run, cls.other, cls.empty, 2)
        cls.quarantined = f.make_route(cls.import_run, 215, "Ghost",
                                       quarantined=True)

    def setUp(self):
        self.client = APIClient()

    def test_ordered_stops_with_origin_and_terminus(self):
        body = self.client.get(
            f"/api/v1/routes/{self.route.id}/").json()
        self.assertEqual(
            set(body),
            {"id", "name", "origin", "destination", "operator",
             "network", "stops"},
        )
        self.assertEqual(
            [(s["position"], s["stop"]["id"]) for s in body["stops"]],
            [(1, self.a.id), (2, self.b.id)],
        )
        self.assertEqual(
            (body["stops"][0]["is_origin"], body["stops"][0]["is_terminus"]),
            (True, False),
        )
        self.assertEqual(
            (body["stops"][1]["is_origin"], body["stops"][1]["is_terminus"]),
            (False, True),
        )

    def test_single_stop_is_both_origin_and_terminus(self):
        body = self.client.get(
            f"/api/v1/routes/{self.single.id}/").json()
        self.assertEqual(len(body["stops"]), 1)
        self.assertTrue(body["stops"][0]["is_origin"])
        self.assertTrue(body["stops"][0]["is_terminus"])

    def test_duplicate_platform_steps_preserved(self):
        body = self.client.get(
            f"/api/v1/routes/{self.dupe.id}/").json()
        self.assertEqual(
            [s["stop"]["id"] for s in body["stops"]],
            [self.a.id, self.a.id],
        )

    def test_membership_empty_route_returns_explicit_empty_list(self):
        response = self.client.get(f"/api/v1/routes/{self.empty.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["stops"], [])

    def test_unknown_and_withheld_ids_share_plain_404(self):
        for pk in (99999999, self.quarantined.id):
            response = self.client.get(f"/api/v1/routes/{pk}/")
            self.assertEqual(response.status_code, 404, pk)
            self.assertEqual(set(response.json()), {"detail"})
            self.assertIn("route", response.json()["detail"].lower())
