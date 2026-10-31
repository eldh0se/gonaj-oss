"""Place-group tests (009): search_places grouping, find_routes_matrix direction."""
from django.test import TestCase

from apps.journey import tools
from apps.transport.tests import factories as f


class PlaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-places")
        cls.master = f.make_master(
            cls.import_run, 71, "PlaceLoop", operator="KSRTC",
            network="Kochi",
        )
        cls.aluva = f.make_stop(
            cls.import_run, 711, "Aluva", 10.11, 76.35
        )
        # Cluster A: five same-named stops within tens of meters.
        cls.k1 = f.make_stop(cls.import_run, 712, "Kaloor", 9.9900, 76.2900)
        cls.k2 = f.make_stop(cls.import_run, 713, "Kaloor", 9.9902, 76.2901)
        cls.k3 = f.make_stop(cls.import_run, 714, "Kaloor", 9.9898, 76.2899)
        cls.k4 = f.make_stop(cls.import_run, 715, "Kaloor", 9.9901, 76.2898)
        cls.k5 = f.make_stop(cls.import_run, 716, "Kaloor", 9.9899, 76.2902)
        # Cluster B: two same-named stops kilometres away.
        cls.k6 = f.make_stop(cls.import_run, 717, "Kaloor", 10.0500, 76.3500)
        cls.k7 = f.make_stop(cls.import_run, 718, "Kaloor", 10.0501, 76.3501)
        cls.route1 = f.make_route(
            cls.import_run, 711, "Aluva-East", from_text="",
            to_text="",
        )
        f.link_master(cls.import_run, cls.master, cls.route1, 1)
        f.link_stop(cls.import_run, cls.route1, cls.aluva, 1)
        f.link_stop(cls.import_run, cls.route1, cls.k1, 2)
        f.link_stop(cls.import_run, cls.route1, cls.k2, 3)
        cls.route2 = f.make_route(
            cls.import_run, 712, "Beta-Run", from_text="", to_text="",
        )
        f.link_master(cls.import_run, cls.master, cls.route2, 2)
        f.link_stop(cls.import_run, cls.route2, cls.k3, 1)
        f.link_stop(cls.import_run, cls.route2, cls.k4, 2)

    def test_shared_name_yields_two_groups(self):
        out = tools.search_places(query="Kaloor")
        self.assertTrue(out["ok"])
        groups = out["groups"]
        self.assertEqual(len(groups), 2)
        self.assertEqual({g["key"] for g in groups}, {"kaloor#1", "kaloor#2"})
        self.assertEqual(sorted(len(g["members"]) for g in groups), [2, 5])
        big = next(g for g in groups if len(g["members"]) == 5)
        self.assertGreater(big["spread_m"], 0)
        self.assertLess(big["spread_m"], 150)
        self.assertEqual(big["route_count"], 2)
        self.assertEqual(
            [r["name"] for r in big["routes"]], ["Aluva-East", "Beta-Run"]
        )
        small = next(g for g in groups if len(g["members"]) == 2)
        self.assertEqual(small["route_count"], 0)
        self.assertEqual(small["routes"], [])

    def test_search_guards(self):
        wide = tools.search_places(bbox="76.0,9.0,77.0,10.0")
        self.assertTrue(wide["ok"])
        self.assertEqual(wide["status"], "zoom_in")
        self.assertEqual(wide["groups"], [])
        missing = tools.search_places(query="Atlantis Central")
        self.assertTrue(missing["ok"])
        self.assertEqual(missing["status"], "empty")
        self.assertEqual(missing["groups"], [])
        both = tools.search_places(query="Kaloor", bbox="76.29,9.99,76.30,10.0")
        self.assertFalse(both["ok"])
        single = tools.search_places(query="Aluva")
        self.assertTrue(single["ok"])
        self.assertEqual(len(single["groups"]), 1)
        self.assertEqual(single["groups"][0]["spread_m"], 0)
        self.assertEqual(len(single["groups"][0]["members"]), 1)

    def test_grouping_is_deterministic(self):
        first = tools.search_places(query="Kaloor")["groups"]
        second = tools.search_places(query="Kaloor")["groups"]
        self.assertEqual(
            [(g["key"], [m["id"] for m in g["members"]]) for g in first],
            [(g["key"], [m["id"] for m in g["members"]]) for g in second],
        )

    def test_matrix_drops_opposite_direction(self):
        out = tools.find_routes_matrix(
            from_ids=[self.aluva.id, self.k1.id],
            to_ids=[self.aluva.id, self.k1.id, self.k2.id],
        )
        self.assertTrue(out["ok"])
        pairs = {
            (p["from_stop_id"], p["to_stop_id"]) for p in out["pairs"]
        }
        self.assertEqual(
            pairs,
            {
                (self.aluva.id, self.k1.id),
                (self.aluva.id, self.k2.id),
                (self.k1.id, self.k2.id),
            },
        )
        for pair in out["pairs"]:
            self.assertTrue(pair["routes"])
            for route in pair["routes"]:
                self.assertTrue(
                    route["evidence"].startswith("/routes/")
                )
        unknown = tools.find_routes_matrix(
            from_ids=[99999], to_ids=[self.k1.id]
        )
        self.assertFalse(unknown["ok"])

    def test_opposite_side_members_stay_individual(self):
        out = tools.search_places(query="Kaloor")
        groups = out["groups"]
        host = next(
            g
            for g in groups
            if {m["id"] for m in g["members"]} >= {self.k1.id, self.k2.id}
        )
        ids = [m["id"] for m in host["members"]]
        self.assertIn(self.k1.id, ids)
        self.assertIn(self.k2.id, ids)
        coords = {(m["lat"], m["lon"]) for m in host["members"]}
        self.assertGreater(len(coords), 1)

    def test_matrix_resolves_exact_member(self):
        out = tools.find_routes_matrix(
            from_ids=[self.k1.id], to_ids=[self.k2.id]
        )
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["pairs"]), 1)
        self.assertEqual(out["pairs"][0]["from_stop_id"], self.k1.id)
        self.assertEqual(out["pairs"][0]["to_stop_id"], self.k2.id)
