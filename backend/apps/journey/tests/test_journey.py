"""Journey endpoint contract tests (US1, T008).

Stubbed model client (no network, no key); the three tools run for
real against the factory dataset. Written first; FAILS before T010/T011.
"""
import json

from django.test import override_settings
from rest_framework.test import APIClient

from apps.journey.providers import meta as provider
from apps.transport.tests import factories as f
from apps.transport.tests.factories import ApiTestCase


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


class StubModel:
    """Scripted model client; records received messages."""

    def __init__(self, script=None, error=None):
        self.script = list(script or [])
        self.error = error
        self.calls = 0
        self.received = []

    def __call__(self, **kwargs):
        self.calls += 1
        self.received.append(kwargs.get("messages", []))
        if self.error is not None and self.calls == 1:
            raise self.error
        return self.script.pop(0)


class JourneyTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-journey")
        cls.master = f.make_master(
            cls.import_run, 41, "Loop", operator="KSRTC", network="Kochi"
        )
        cls.south = f.make_stop(
            cls.import_run, 501, "Ernakulam South", 9.97, 76.28
        )
        cls.fort = f.make_stop(
            cls.import_run, 502, "Fort Kochi", 9.97, 76.24
        )
        cls.alone = f.make_stop(
            cls.import_run, 503, "Lonely Point", 9.90, 76.20
        )
        cls.route = f.make_route(
            cls.import_run, 501, "South-Fort", from_text="",
            to_text="",
        )
        f.link_master(cls.import_run, cls.master, cls.route, 1)
        f.link_stop(cls.import_run, cls.route, cls.south, 1)
        f.link_stop(cls.import_run, cls.route, cls.fort, 2)

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self._real = provider.complete_with_tools

    def tearDown(self):
        provider.complete_with_tools = self._real

    def ask(self, body):
        return self.client.post("/api/v1/journey/", body, format="json")

    def test_answer_cites_verified_route_with_evidence(self):
        stub = StubModel(
            script=[
                _Response(
                    _Message(
                        tool_calls=[
                            _ToolCall(
                                "c1",
                                "find_routes",
                                json.dumps(
                                    {
                                        "from_stop_id": self.south.id,
                                        "to_stop_id": self.fort.id,
                                    }
                                ),
                            )
                        ]
                    )
                ),
                _Response(
                    _Message(
                        content="Take the South-Fort service from "
                        "Ernakulam South to Fort Kochi, see "
                        f"/routes/{self.route.id}."
                    )
                ),
            ]
        )
        provider.complete_with_tools = stub
        body = self.ask(
            {"question": "How do I get from Ernakulam South to Fort Kochi?"}
        ).json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["boarding_stop"]["name"], "Ernakulam South")
        self.assertEqual(body["alighting_stop"]["name"], "Fort Kochi")
        self.assertEqual(len(body["routes"]), 1)
        self.assertEqual(
            body["routes"][0]["evidence"], f"/routes/{self.route.id}"
        )
        self.assertEqual(body["meta"]["model"], "muse-spark-1.3")
        self.assertEqual(body["meta"]["provider"], "meta")
        self.assertIsInstance(body["meta"]["latency_ms"], int)
        for banned in ("10:30", "minutes", "transfer", "change at"):
            self.assertNotIn(banned, body["answer"])
        detail = self.client.get(f"/api/v1/routes/{self.route.id}/")
        self.assertEqual(detail.status_code, 200)
        names = [s["stop"]["name"] for s in detail.json()["stops"]]
        self.assertEqual(names, ["Ernakulam South", "Fort Kochi"])

    def test_unconnected_pair_refuses_without_invention(self):
        stub = StubModel(
            script=[
                _Response(
                    _Message(
                        tool_calls=[
                            _ToolCall(
                                "c1",
                                "find_routes",
                                json.dumps(
                                    {
                                        "from_stop_id": self.south.id,
                                        "to_stop_id": self.alone.id,
                                    }
                                ),
                            )
                        ]
                    )
                ),
                _Response(
                    _Message(content="There is no direct service there.")
                ),
            ]
        )
        provider.complete_with_tools = stub
        body = self.ask(
            {"question": "How do I get from Ernakulam South to Lonely Point?"}
        ).json()
        self.assertEqual(body["status"], "refuse")
        self.assertNotIn("routes", body)
        self.assertIn("direct", body["message"].lower())

    def test_blank_question_asks_again_without_model_call(self):
        stub = StubModel(script=[])
        provider.complete_with_tools = stub
        body = self.ask({"question": "   "}).json()
        self.assertEqual(body["status"], "refuse")
        self.assertIn("question", body["message"].lower())
        self.assertEqual(stub.calls, 0)

    def test_hallucinated_route_is_refused(self):
        stub = StubModel(
            script=[
                _Response(_Message(content="Take it, see /routes/99999.")),
                _Response(_Message(content="Take it, see /routes/99999.")),
            ]
        )
        provider.complete_with_tools = stub
        body = self.ask({"question": "How do I get there?"}).json()
        self.assertEqual(body["status"], "refuse")
        self.assertNotIn("routes", body)

    def test_time_shaped_draft_is_repaired_then_answered(self):
        stub = StubModel(
            script=[
                _Response(
                    _Message(
                        tool_calls=[
                            _ToolCall(
                                "c1",
                                "find_routes",
                                json.dumps(
                                    {
                                        "from_stop_id": self.south.id,
                                        "to_stop_id": self.fort.id,
                                    }
                                ),
                            )
                        ]
                    )
                ),
                _Response(
                    _Message(
                        content="Take South-Fort, departs 10:30, "
                        "takes 20 minutes, see "
                        f"/routes/{self.route.id}."
                    )
                ),
                _Response(
                    _Message(
                        content="Take the South-Fort service from "
                        "Ernakulam South to Fort Kochi, see "
                        f"/routes/{self.route.id}."
                    )
                ),
            ]
        )
        provider.complete_with_tools = stub
        body = self.ask(
            {"question": "How do I get from Ernakulam South to Fort Kochi?"}
        ).json()
        self.assertEqual(body["status"], "ok")
        self.assertNotIn("10:30", body["answer"])
        self.assertNotIn("minutes", body["answer"])

    def test_transfer_shaped_draft_is_refused_when_unrepairable(self):
        stub = StubModel(
            script=[
                _Response(
                    _Message(
                        tool_calls=[
                            _ToolCall(
                                "c1",
                                "find_routes",
                                json.dumps(
                                    {
                                        "from_stop_id": self.south.id,
                                        "to_stop_id": self.fort.id,
                                    }
                                ),
                            )
                        ]
                    )
                ),
                _Response(
                    _Message(
                        content="Take South-Fort then transfer at the hub, "
                        f"see /routes/{self.route.id}."
                    )
                ),
                _Response(
                    _Message(
                        content="Still transfer at the hub, see "
                        f"/routes/{self.route.id}."
                    )
                ),
            ]
        )
        provider.complete_with_tools = stub
        body = self.ask(
            {"question": "How do I get from Ernakulam South to Fort Kochi?"}
        ).json()
        self.assertEqual(body["status"], "refuse")

    def test_model_outage_returns_cannot_answer_fallback(self):
        stub = StubModel(error=Exception("boom"))
        provider.complete_with_tools = stub
        body = self.ask({"question": "How do I get there?"}).json()
        self.assertEqual(body["status"], "refuse")
        self.assertIn("right now", body["message"].lower())
        self.assertEqual(body["meta"]["model"], "none")
        self.assertEqual(body["meta"]["provider"], "local-fallback")

    def test_history_is_bounded_to_last_six_turns(self):
        history = [
            {"role": "user", "content": f"old {i}"} for i in range(8)
        ]
        stub = StubModel(
            script=[_Response(_Message(content="No direct service known."))]
        )
        provider.complete_with_tools = stub
        self.ask({"question": "And back?", "history": history})
        sent = stub.received[0]
        olds = [m["content"] for m in sent if m.get("content", "").startswith("old ")]
        self.assertEqual(olds, [f"old {i}" for i in range(2, 8)])

    def test_missing_question_is_plain_400(self):
        response = self.ask({})
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_non_object_body_is_plain_400(self):
        response = self.client.post(
            "/api/v1/journey/", [1, 2], format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_get_is_plain_405(self):
        response = self.client.get("/api/v1/journey/")
        self.assertEqual(response.status_code, 405)
        self.assertIn("detail", response.json())

    @override_settings(
        REST_FRAMEWORK={
            "EXCEPTION_HANDLER": (
                "apps.transport.api.errors.plain_exception_handler"
            ),
            "DEFAULT_THROTTLE_RATES": {
                "transport_minute": "1/min",
                "transport_day": "5000/day",
            },
        }
    )
    def test_throttle_429_is_plain_with_retry_after(self):
        stub = StubModel(
            script=[
                _Response(
                    _Message(
                        tool_calls=[
                            _ToolCall(
                                "c1",
                                "find_routes",
                                json.dumps(
                                    {
                                        "from_stop_id": self.south.id,
                                        "to_stop_id": self.fort.id,
                                    }
                                ),
                            )
                        ]
                    )
                ),
                _Response(
                    _Message(
                        content="Take the South-Fort service, see "
                        f"/routes/{self.route.id}."
                    )
                ),
            ]
        )
        provider.complete_with_tools = stub
        first = self.ask(
            {"question": "How do I get from South to Fort?"}
        )
        self.assertEqual(first.status_code, 200)
        throttled = self.ask(
            {"question": "How do I get from South to Fort?"}
        )
        self.assertEqual(throttled.status_code, 429)
        self.assertEqual(
            throttled.json()["detail"],
            "Too many requests. Please wait a moment and try again.",
        )
        self.assertIn("Retry-After", throttled.headers)


class ProofTests(ApiTestCase):
    """Read-only, key-safety, and AI-surface purity proof (T027/T028)."""

    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-proof")
        cls.master = f.make_master(
            cls.import_run, 61, "ProofLoop", operator="KSRTC",
            network="Kochi",
        )
        cls.south = f.make_stop(
            cls.import_run, 611, "Ernakulam South", 9.97, 76.28
        )
        cls.fort = f.make_stop(
            cls.import_run, 612, "Fort Kochi", 9.97, 76.24
        )
        cls.route = f.make_route(
            cls.import_run, 611, "ProofRun", from_text="",
            to_text="",
        )
        f.link_master(cls.import_run, cls.master, cls.route, 1)
        f.link_stop(cls.import_run, cls.route, cls.south, 1)
        f.link_stop(cls.import_run, cls.route, cls.fort, 2)

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self._real = provider.complete_with_tools

    def tearDown(self):
        provider.complete_with_tools = self._real

    def test_unknown_tool_call_is_rejected_with_zero_writes(self):
        from apps.transport.models import Route, Stop

        stops_before = Stop.objects.count()
        routes_before = Route.objects.count()
        stub = StubModel(
            script=[
                _Response(
                    _Message(
                        tool_calls=[
                            _ToolCall("evil1", "delete_stop", json.dumps({}))
                        ]
                    )
                ),
                _Response(_Message(content="I cannot verify that.")),
            ]
        )
        provider.complete_with_tools = stub
        body = self.client.post(
            "/api/v1/journey/", {"question": "Remove a stop?"}, format="json"
        ).json()
        self.assertEqual(body["status"], "refuse")
        self.assertEqual(Stop.objects.count(), stops_before)
        self.assertEqual(Route.objects.count(), routes_before)

    def test_model_key_never_leaks_into_responses(self):
        from django.test import override_settings

        from apps.journey import tools as journey_tools

        stub = StubModel(
            script=[
                _Response(
                    _Message(
                        tool_calls=[
                            _ToolCall(
                                "c1",
                                "find_routes",
                                json.dumps(
                                    {
                                        "from_stop_id": self.south.id,
                                        "to_stop_id": self.fort.id,
                                    }
                                ),
                            )
                        ]
                    )
                ),
                _Response(
                    _Message(
                        content="Take ProofRun, see "
                        f"/routes/{self.route.id}."
                    )
                ),
            ]
        )
        provider.complete_with_tools = stub
        with override_settings(MODEL_API_KEY="secret-key-999"):
            response = self.client.post(
                "/api/v1/journey/",
                {"question": "How do I get from South to Fort?"},
                format="json",
            )
        self.assertEqual(response.json()["status"], "ok")
        self.assertNotIn("secret-key-999", response.content.decode())
        self.assertNotIn(
            "secret-key-999",
            json.dumps(journey_tools.TOOL_SCHEMAS),
        )

    def test_tool_payloads_carry_no_provenance_or_osm_ids(self):
        from apps.journey import tools as journey_tools

        payloads = [
            journey_tools.search_stops(query="Ernakulam"),
            journey_tools.find_routes(self.south.id, self.fort.id),
            journey_tools.get_route_detail(self.route.id),
        ]
        for payload in payloads:
            text = json.dumps(payload).lower()
            for banned in ("osm", "tags", "import_run", "provenance"):
                self.assertNotIn(banned, text)


class DisambiguationTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-disambiguate")
        cls.master = f.make_master(
            cls.import_run, 51, "NorthLoop", operator="KSRTC",
            network="Kochi",
        )
        cls.north_hub = f.make_stop(
            cls.import_run, 511, "North Hub", 10.05, 76.30
        )
        cls.north_edge = f.make_stop(
            cls.import_run, 512, "North Edge", 10.06, 76.31
        )
        cls.south = f.make_stop(
            cls.import_run, 513, "Ernakulam South", 9.97, 76.28
        )
        cls.route = f.make_route(
            cls.import_run, 511, "Hub-South", from_text="",
            to_text="",
        )
        f.link_master(cls.import_run, cls.master, cls.route, 1)
        f.link_stop(cls.import_run, cls.route, cls.north_hub, 1)
        f.link_stop(cls.import_run, cls.route, cls.south, 2)

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self._real = provider.complete_with_tools

    def tearDown(self):
        provider.complete_with_tools = self._real

    def ask(self, body):
        return self.client.post("/api/v1/journey/", body, format="json")

    def test_ambiguous_name_returns_candidates_without_answer(self):
        stub = StubModel(
            script=[
                _Response(
                    _Message(
                        tool_calls=[
                            _ToolCall(
                                "c1",
                                "search_stops",
                                json.dumps({"query": "North"}),
                            )
                        ]
                    )
                ),
                _Response(_Message(content="Which stop did you mean?")),
            ]
        )
        provider.complete_with_tools = stub
        body = self.ask({"question": "How do I get from North to South?"}).json()
        self.assertEqual(body["status"], "disambiguate")
        self.assertNotIn("routes", body)
        names = {c["name"] for c in body["candidates"]}
        self.assertEqual(names, {"North Hub", "North Edge"})
        ids = {c["id"] for c in body["candidates"]}
        self.assertEqual(ids, {self.north_hub.id, self.north_edge.id})
        self.assertIn("which one", body["message"].lower())

    def test_follow_up_for_chosen_stop_answers_honestly(self):
        stub = StubModel(
            script=[
                _Response(
                    _Message(
                        tool_calls=[
                            _ToolCall(
                                "c1",
                                "find_routes",
                                json.dumps(
                                    {
                                        "from_stop_id": self.north_hub.id,
                                        "to_stop_id": self.south.id,
                                    }
                                ),
                            )
                        ]
                    )
                ),
                _Response(
                    _Message(
                        content="Take the Hub-South service from North Hub "
                        "to Ernakulam South, see "
                        f"/routes/{self.route.id}."
                    )
                ),
            ]
        )
        provider.complete_with_tools = stub
        body = self.ask(
            {
                "question": "North Hub",
                "context": {
                    "candidate_stop_ids": [self.north_hub.id, self.north_edge.id]
                },
            }
        ).json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["boarding_stop"]["name"], "North Hub")
        self.assertEqual(
            body["routes"][0]["evidence"], f"/routes/{self.route.id}"
        )
        sent = stub.received[0]
        hints = [m["content"] for m in sent if m.get("role") == "system"]
        self.assertTrue(any(str(self.north_hub.id) in h for h in hints))

    def test_unknown_name_is_not_invented(self):
        stub = StubModel(
            script=[
                _Response(
                    _Message(
                        tool_calls=[
                            _ToolCall(
                                "c1",
                                "search_stops",
                                json.dumps({"query": "Atlantis Central"}),
                            )
                        ]
                    )
                ),
                _Response(_Message(content="I cannot find that place.")),
            ]
        )
        provider.complete_with_tools = stub
        body = self.ask({"question": "How do I get from Atlantis Central?"}).json()
        self.assertEqual(body["status"], "refuse")
        self.assertNotIn("routes", body)
        self.assertTrue(
            "spelling" in body["message"].lower()
            or "map" in body["message"].lower()
        )
