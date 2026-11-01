"""Area-search tests (012): group-first matrix flow, walk notes, fallback.

Shared Kaloor-shape fixtures live here (see `make_kaloor_corridor`) and are
reused by every 012 story phase so all phases test the same geography.
"""
from django.test import TestCase

from apps.journey import tools
from apps.transport.tests import factories as f


def make_kaloor_corridor(label="factory-area-search"):
    """Origin cluster + near/far destination clusters + one servable route.

    a1/a2 are opposite sides (~25m apart), a3 walkable; k1/k2 opposite sides,
    k3 walkable, k4/k5 far (>1km). route1 serves a1 -> k1 in order.
    """
    _, run = f.make_snapshot(label=label)
    master = f.make_master(
        run, 71, "AreaLoop", operator="KSRTC", network="Kochi"
    )
    a1 = f.make_stop(run, 701, "Aluva", 10.1100, 76.3500)
    a2 = f.make_stop(run, 702, "Aluva", 10.1102, 76.3501)
    a3 = f.make_stop(run, 703, "Aluva", 10.1098, 76.3499)
    k1 = f.make_stop(run, 712, "Kaloor", 9.9900, 76.2900)
    k2 = f.make_stop(run, 713, "Kaloor", 9.9902, 76.2901)
    k3 = f.make_stop(run, 714, "Kaloor", 9.9898, 76.2899)
    k4 = f.make_stop(run, 715, "Kaloor", 10.0500, 76.3500)
    k5 = f.make_stop(run, 716, "Kaloor", 10.0501, 76.3501)
    route1 = f.make_route(run, 721, "Aluva-East", from_text="", to_text="")
    f.link_master(run, master, route1, 1)
    f.link_stop(run, route1, a1, 1)
    f.link_stop(run, route1, k1, 2)
    return {
        "run": run,
        "a1": a1,
        "a2": a2,
        "a3": a3,
        "k1": k1,
        "k2": k2,
        "k3": k3,
        "k4": k4,
        "k5": k5,
        "route1": route1,
    }


class DistanceTests(TestCase):
    def test_known_pair_meters(self):
        out = tools.distance_m(9.9900, 76.2900, 9.9902, 76.2901)
        self.assertTrue(out["ok"])
        self.assertAlmostEqual(out["distance_m"], 24.8, delta=1.5)

    def test_zero_distance(self):
        out = tools.distance_m(9.99, 76.29, 9.99, 76.29)
        self.assertTrue(out["ok"])
        self.assertAlmostEqual(out["distance_m"], 0.0, delta=1e-6)

    def test_invalid_input_errors(self):
        out = tools.distance_m("nine", 76.29, 9.99, 76.29)
        self.assertFalse(out["ok"])


class _Fn:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.function = _Fn(name, arguments)


class _Message:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class _Choice:
    def __init__(self, message):
        self.message = message


class _Response:
    def __init__(self, message):
        self.choices = [_Choice(message)]


class UnusedModel:
    """No scripted turns: any model call raises, proving no model was needed."""

    def __call__(self, **kwargs):
        raise AssertionError("model loop reached; deterministic flow expected")


class AreaFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.geo = make_kaloor_corridor(label="factory-area-flow")

    def setUp(self):
        super().setUp()
        from apps.journey.providers import meta as provider

        self._real = provider.complete_with_tools
        provider.complete_with_tools = UnusedModel()

    def tearDown(self):
        from apps.journey.providers import meta as provider

        provider.complete_with_tools = self._real
        super().tearDown()

    def test_area_to_area_answers_without_pick(self):
        from apps.journey.agent import run_journey

        payload, tools_used = run_journey(
            question="How do I get from Aluva to Kaloor?"
        )
        geo = self.geo
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["alighting_stop"]["id"], geo["k1"].id)
        self.assertEqual(
            payload["routes"][0]["evidence"],
            f"/routes/{geo['route1'].id}",
        )
        self.assertIn("walk", payload["answer"])
        self.assertIn("search_places", tools_used)
        self.assertIn("find_routes_matrix", tools_used)

    def test_wrong_side_pick_answers_via_mate(self):
        from apps.journey.agent import run_journey

        geo = self.geo
        payload, _ = run_journey(
            question="Kaloor",
            context={
                "candidate_stop_ids": [geo["k1"].id, geo["k2"].id],
                "slot": "to",
                "selected_stop_id": geo["k2"].id,
                "resolved": {"id": geo["a1"].id, "name": "Aluva"},
            },
        )
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["alighting_stop"]["id"], geo["k1"].id)
        self.assertIn("walk", payload["answer"])

    def test_origin_wrong_side_pick_answers_via_mate(self):
        from apps.journey.agent import run_journey

        geo = self.geo
        payload, _ = run_journey(
            question="Aluva",
            context={
                "candidate_stop_ids": [geo["a1"].id, geo["a2"].id],
                "slot": "from",
                "selected_stop_id": geo["a2"].id,
                "resolved": {"id": geo["k1"].id, "name": "Kaloor"},
            },
        )
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["boarding_stop"]["id"], geo["a1"].id)
        self.assertIn("Also near Aluva", payload["answer"])
        self.assertIn("walk", payload["answer"])


class TokenFallbackTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _, run = f.make_snapshot(label="factory-token-fallback")
        cls.south_railway = f.make_stop(run, 981, "South Railway", 9.97, 76.28)
        cls.north_railway = f.make_stop(run, 982, "North Railway", 9.96, 76.27)
        cls.aluva = f.make_stop(run, 983, "Aluva", 10.11, 76.35)

    def test_token_fallback_finds_shorter_name(self):
        out = tools.search_stops(query="South Railway Station")
        self.assertTrue(out["ok"])
        ids = [stop["id"] for stop in out["stops"]]
        self.assertIn(self.south_railway.id, ids)
        self.assertLess(
            ids.index(self.south_railway.id),
            ids.index(self.north_railway.id),
        )

    def test_token_fallback_groups(self):
        out = tools.search_places(query="South Railway Station")
        self.assertTrue(out["ok"])
        member_ids = [
            member["id"] for group in out["groups"] for member in group["members"]
        ]
        self.assertIn(self.south_railway.id, member_ids)

    def test_exact_match_skips_fallback(self):
        from unittest import mock

        from apps.journey import tools as tools_module

        with mock.patch.object(
            tools_module,
            "_token_overlap_rows",
            side_effect=AssertionError("fallback used on exact hit"),
        ):
            stops_out = tools.search_stops(query="Aluva")
            self.assertTrue(stops_out["ok"])
            self.assertIn(
                self.aluva.id, [stop["id"] for stop in stops_out["stops"]]
            )
            places_out = tools.search_places(query="Aluva")
            self.assertTrue(places_out["ok"])
            self.assertTrue(places_out["groups"])

    def test_unknown_stays_empty(self):
        stops_out = tools.search_stops(query="ZzxqNoSuchPlace")
        self.assertTrue(stops_out["ok"])
        self.assertEqual(stops_out["status"], "empty")
        places_out = tools.search_places(query="ZzxqNoSuchPlace")
        self.assertTrue(places_out["ok"])
        self.assertEqual(places_out.get("status"), "empty")
        self.assertEqual(places_out.get("groups"), [])


class SingleEndedTests(TestCase):
    def test_single_ended_keeps_legacy_loop(self):
        # Out of scope for 012: no from-to shape, so the legacy model
        # loop engages (model called) and stays honest (no invented route).
        from apps.journey.agent import run_journey

        seen = []

        class ScriptedModel:
            def __init__(self):
                self.turns = [
                    _Response(
                        _Message(
                            tool_calls=[
                                _ToolCall(
                                    "c1",
                                    "search_places",
                                    '{"query": "Kaloor"}',
                                )
                            ]
                        )
                    ),
                    _Response(_Message(content="Kaloor has many stops.")),
                ]

            def __call__(self, **kwargs):
                seen.append(kwargs.get("messages", []))
                return self.turns.pop(0)

        import apps.journey.providers.meta as provider_module

        real = provider_module.complete_with_tools
        provider_module.complete_with_tools = ScriptedModel()
        try:
            payload, tools_used = run_journey(question="Kaloor buses?")
        finally:
            provider_module.complete_with_tools = real
        self.assertTrue(seen, "legacy model loop was not engaged")
        self.assertEqual(payload["status"], "refuse")
        self.assertNotIn("routes", payload)
        self.assertIn("search_places", tools_used)


class FallbackTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.geo = make_kaloor_corridor(label="factory-area-fallback")

    def test_no_viable_pair_refuses_politely(self):
        from apps.journey.agent import run_journey
        from apps.transport.tests import factories as f

        geo = self.geo
        f.make_stop(geo["run"], 991, "Lonely", 9.80, 76.20)
        payload, _ = run_journey(
            question="How do I get from Aluva to Lonely?"
        )
        self.assertEqual(payload["status"], "refuse")
        self.assertIn("direct service", payload["message"])

    def test_empty_place_offers_pick(self):
        from apps.journey.agent import run_journey

        payload, _ = run_journey(
            question="How do I get from Aluva to Zzxq?"
        )
        self.assertEqual(payload["status"], "disambiguate")
        self.assertEqual(payload["slot"], "to")
        self.assertEqual(payload["offered_ids"], [])
        self.assertIn("map", payload["message"].lower())

    def test_zoom_in_asks_to_narrow(self):
        from apps.journey import tools

        out = tools.search_places(
            bbox="75.0,9.0,78.0,10.0",
        )
        self.assertTrue(out["ok"])
        self.assertEqual(out.get("status"), "zoom_in")
        self.assertIn("zoom", out.get("detail", "").lower())

    def test_no_bypass_records_matrix_audit(self):
        from apps.journey.agent import run_journey

        geo = self.geo
        payload, tools_used = run_journey(
            question="Kaloor",
            context={
                "candidate_stop_ids": [geo["k1"].id, geo["k2"].id],
                "slot": "to",
                "selected_stop_id": geo["k2"].id,
                "resolved": {"id": geo["a1"].id, "name": "Aluva"},
            },
        )
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["alighting_stop"]["id"], geo["k1"].id)
        for name in (
            "search_places",
            "find_routes_matrix",
            "get_route_detail",
            "distance_m",
        ):
            self.assertIn(name, tools_used)
        self.assertNotIn("find_routes", tools_used)

    def test_truncation_offers_pick(self):
        from unittest import mock

        from apps.journey import tools as tools_module
        from apps.journey.agent import run_journey

        with mock.patch.object(
            tools_module, "MATRIX_PAIR_CAP", 4
        ):
            payload, _ = run_journey(
                question="How do I get from Aluva to Kaloor?"
            )
        self.assertEqual(payload["status"], "disambiguate")
        self.assertTrue(len(payload["offered_ids"]) > 0)
        for candidate in payload["candidates"]:
            self.assertIsInstance(candidate["lat"], float)
            self.assertIsInstance(candidate["lon"], float)


class NearbyStopsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.geo = make_kaloor_corridor(label="factory-nearby")

    def test_default_radius_ordered(self):
        k1 = self.geo["k1"]
        out = tools.nearby_stops(lat=k1.lat, lon=k1.lon)
        self.assertTrue(out["ok"])
        stops = out["stops"]
        self.assertGreaterEqual(len(stops), 3)
        distances = [s["distance_m"] for s in stops]
        self.assertEqual(distances, sorted(distances))
        self.assertLessEqual(max(distances), 500)
        self.assertEqual(stops[0]["id"], k1.id)

    def test_max_radius_enforced(self):
        out = tools.nearby_stops(lat=9.99, lon=76.29, radius_m=2001)
        self.assertFalse(out["ok"])
        ok_max = tools.nearby_stops(lat=9.99, lon=76.29, radius_m=2000)
        self.assertTrue(ok_max["ok"])

    def test_invalid_coords_error(self):
        out = tools.nearby_stops(lat=999, lon=76.29)
        self.assertFalse(out["ok"])

    def test_cap_100(self):
        _, run = f.make_snapshot(label="factory-nearby-cap")
        for i in range(105):
            f.make_stop(run, 9000 + i, "Crowd", 9.99, 76.29)
        out = tools.nearby_stops(lat=9.99, lon=76.29)
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["stops"]), 100)
