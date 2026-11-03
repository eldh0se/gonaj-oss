"""Ranked answer tests (010): grouped operators, hints, destinations."""
import json
import re

from rest_framework.test import APIClient

from apps.journey import agent
from apps.transport.tests import factories as f
from apps.transport.tests.factories import ApiTestCase


class RankedTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-ranked")
        cls.ksrtc = f.make_master(
            cls.import_run, 81, "Kochi KSRTC", operator="KSRTC",
            network="Kochi",
        )
        cls.private = f.make_master(
            cls.import_run, 82, "City Private", operator="City Private",
            network="Kochi",
        )
        cls.a = f.make_stop(cls.import_run, 811, "Aluva", 10.11, 76.35)
        cls.b = f.make_stop(cls.import_run, 812, "Kaloor", 9.99, 76.29)
        cls.x = f.make_stop(cls.import_run, 813, "Midway", 10.05, 76.32)
        cls.c = f.make_stop(cls.import_run, 814, "Nowhere", 10.20, 76.40)
        cls.r1 = f.make_route(
            cls.import_run, 811, "Aluva Direct", from_text="",
            to_text="",
        )
        f.link_master(cls.import_run, cls.ksrtc, cls.r1, 1)
        f.link_stop(cls.import_run, cls.r1, cls.a, 1)
        f.link_stop(cls.import_run, cls.r1, cls.b, 2)
        cls.r2 = f.make_route(
            cls.import_run, 812, "Aluva Hopper", from_text="",
            to_text="",
        )
        f.link_master(cls.import_run, cls.ksrtc, cls.r2, 2)
        f.link_stop(cls.import_run, cls.r2, cls.a, 1)
        f.link_stop(cls.import_run, cls.r2, cls.x, 2)
        f.link_stop(cls.import_run, cls.r2, cls.b, 3)
        cls.r3 = f.make_route(
            cls.import_run, 813, "City Sprint", from_text="",
            to_text="",
        )
        f.link_master(cls.import_run, cls.private, cls.r3, 1)
        f.link_stop(cls.import_run, cls.r3, cls.a, 1)
        f.link_stop(cls.import_run, cls.r3, cls.b, 2)

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def ask(self, body):
        return self.client.post("/api/v1/journey/", body, format="json")

    def test_ksrtc_only_matrix_yields_ksrtc_wording(self):
        out = agent.rank_pairs(
            [
                {"route_id": self.r1.id, "from_id": self.a.id,
                 "to_id": self.b.id},
                {"route_id": self.r2.id, "from_id": self.a.id,
                 "to_id": self.b.id},
            ]
        )
        options = out["options"]
        self.assertEqual(
            [o["route"]["id"] for o in options], [self.r1.id, self.r2.id]
        )
        self.assertTrue(
            all(o["operator"] == "KSRTC" for o in options)
        )
        self.assertIn("2 direct options", out["answer"])
        self.assertNotIn("Other services", out["answer"])

    def test_mixed_operators_share_one_flat_list(self):
        out = agent.rank_pairs(
            [
                {"route_id": self.r1.id, "from_id": self.a.id,
                 "to_id": self.b.id},
                {"route_id": self.r3.id, "from_id": self.a.id,
                 "to_id": self.b.id},
            ]
        )
        self.assertEqual(
            [o["route"]["id"] for o in out["options"]],
            [self.r1.id, self.r3.id],
        )
        self.assertEqual(
            [o["operator"] for o in out["options"]],
            ["KSRTC", "City Private"],
        )

    def test_unknown_operator_sorts_last(self):
        out = agent.rank_pairs(
            [
                {"route_id": self.r1.id, "from_id": self.a.id,
                 "to_id": self.b.id},
            ],
            operators={self.r1.id: None},
        )
        self.assertEqual(len(out["options"]), 1)
        self.assertEqual(out["options"][0]["operator"], "Other services")

    def test_single_option_is_one_item_list(self):
        out = agent.rank_pairs(
            [
                {"route_id": self.r1.id, "from_id": self.a.id,
                 "to_id": self.b.id},
            ]
        )
        self.assertEqual(len(out["options"]), 1)
        self.assertEqual(out["total_options"], 1)
        self.assertEqual(out["total_pages"], 1)

    def test_boarding_hint_only_when_supported(self):
        out = agent.rank_pairs(
            [
                {"route_id": self.r1.id, "from_id": self.a.id,
                 "to_id": self.b.id},
            ]
        )
        hint = out["options"][0].get("boarding_hint")
        self.assertTrue(hint)
        self.assertIn("Aluva", hint)
        bare = agent.rank_pairs(
            [
                {"route_id": self.r1.id, "from_id": self.a.id,
                 "to_id": self.b.id},
            ],
            names={self.a.id: ""},
        )
        self.assertNotIn("boarding_hint", bare["options"][0])

    def test_no_times_in_ranked_text(self):
        out = agent.rank_pairs(
            [
                {"route_id": self.r1.id, "from_id": self.a.id,
                 "to_id": self.b.id},
                {"route_id": self.r3.id, "from_id": self.a.id,
                 "to_id": self.b.id},
            ]
        )
        self.assertFalse(agent._forbidden(out["answer"]))
        self.assertNotRegex(out["answer"], r"\d{1,2}:\d{2}")
        for token in ("minutes", "transfer", "change at"):
            self.assertNotIn(token, out["answer"].lower())

    def test_destinations_capped_with_evidence(self):
        members = [
            {"stop": {"id": 900 + i, "name": f"Place {i}"},
             "evidence": f"/routes/{900 + i}"}
            for i in range(7)
        ]
        out = agent.rank_pairs(
            [
                {"route_id": self.r1.id, "from_id": self.a.id,
                 "to_id": self.b.id},
            ],
            destinations=members,
        )
        self.assertEqual(len(out["destinations"]), 5)
        for dest in out["destinations"]:
            self.assertTrue(dest["evidence"].startswith("/routes/"))
        self.assertIn("2 more", out["answer"])

    def test_flat_options_follow_global_rank_order(self):
        # 014: no per-operator groups; one flat list ordered by
        # (stop_count, route id) across operators.
        out = agent.rank_pairs(
            [
                {"route_id": self.r1.id, "from_id": self.a.id,
                 "to_id": self.b.id},
                {"route_id": self.r2.id, "from_id": self.a.id,
                 "to_id": self.b.id},
                {"route_id": self.r3.id, "from_id": self.a.id,
                 "to_id": self.b.id},
            ]
        )
        self.assertNotIn("groups", out)
        self.assertNotIn("option_groups", out)
        self.assertEqual(
            [o["route"]["id"] for o in out["options"]],
            [self.r1.id, self.r3.id, self.r2.id],
        )

    def test_flat_options_carry_operator_and_network(self):
        out = agent.rank_pairs(
            [
                {"route_id": self.r1.id, "from_id": self.a.id,
                 "to_id": self.b.id},
                {"route_id": self.r3.id, "from_id": self.a.id,
                 "to_id": self.b.id},
            ]
        )
        by_route = {o["route"]["id"]: o for o in out["options"]}
        self.assertEqual(by_route[self.r1.id]["operator"], "KSRTC")
        self.assertEqual(by_route[self.r1.id]["network"], "Kochi")
        self.assertEqual(
            by_route[self.r3.id]["operator"], "City Private"
        )
        self.assertEqual(by_route[self.r3.id]["network"], "Kochi")

    def test_flat_unknown_operator_sorts_last(self):
        out = agent.rank_pairs(
            [
                {"route_id": self.r3.id, "from_id": self.a.id,
                 "to_id": self.b.id},
                {"route_id": self.r1.id, "from_id": self.a.id,
                 "to_id": self.b.id},
            ],
            operators={self.r1.id: None},
        )
        self.assertEqual(
            [o["operator"] for o in out["options"]],
            ["City Private", "Other services"],
        )

    def test_flat_prose_is_bounded_summary(self):
        out = agent.rank_pairs(
            [
                {"route_id": self.r1.id, "from_id": self.a.id,
                 "to_id": self.b.id},
                {"route_id": self.r2.id, "from_id": self.a.id,
                 "to_id": self.b.id},
                {"route_id": self.r3.id, "from_id": self.a.id,
                 "to_id": self.b.id},
            ]
        )
        self.assertLessEqual(len(out["answer"]), 1000)
        self.assertIn("3 direct options", out["answer"])
        self.assertIn("Aluva Direct", out["answer"])

    def test_prose_summary_omits_full_enumeration(self):
        # US3: the summary names only the quickest option, never the
        # full list, and stays within 1000 characters.
        out = agent.rank_pairs(
            [
                {"route_id": self.r1.id, "from_id": self.a.id,
                 "to_id": self.b.id},
                {"route_id": self.r2.id, "from_id": self.a.id,
                 "to_id": self.b.id},
                {"route_id": self.r3.id, "from_id": self.a.id,
                 "to_id": self.b.id},
            ]
        )
        self.assertIn("Aluva Direct", out["answer"])
        self.assertNotIn("Aluva Hopper", out["answer"])
        self.assertNotIn("City Sprint", out["answer"])
        self.assertLessEqual(len(out["answer"]), 1000)

    def test_empty_matrix_refuses_without_options(self):
        body = self.ask(
            {
                "question": "Nowhere",
                "history": [
                    {
                        "role": "user",
                        "content": "How do I get from Aluva to Nowhere?",
                    }
                ],
                "context": {
                    "candidate_stop_ids": [self.c.id],
                    "selected_stop_id": self.c.id,
                    "slot": "to",
                    "resolved": {"id": self.a.id, "name": "Aluva"},
                },
            }
        ).json()
        self.assertEqual(body["status"], "refuse")
        self.assertNotIn("option_groups", body)
        self.assertNotIn("routes", body)
