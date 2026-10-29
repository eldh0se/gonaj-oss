"""Per-IP throttling tests (T035, FR-021–FR-024).

Uses test-lowered rates. Verifies the shared budget, the 429 with
`Retry-After`, per-client isolation, hashed counter keys with no raw
IP material, and spoof-proof identity unless a proxy is configured.
"""
from django.core.cache import caches
from django.test import override_settings
from rest_framework.test import APIClient

from . import factories as f
from .factories import ApiTestCase

LOW_RATES = {
    "EXCEPTION_HANDLER":
        "apps.transport.api.errors.plain_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "transport_minute": "3/min",
        "transport_day": "1000/day",
    },
}
LOCMEM_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}


@override_settings(REST_FRAMEWORK=LOW_RATES)
class ThrottleTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        _, cls.import_run = f.make_snapshot(label="factory-throttle")
        cls.master = f.make_master(cls.import_run, 51, "M")
        cls.a = f.make_stop(cls.import_run, 501, "A", 10.0, 76.3)
        cls.b = f.make_stop(cls.import_run, 502, "B", 10.01, 76.31)
        cls.route = f.make_route(
            cls.import_run, 501, "A-B", from_text="A", to_text="B")
        f.link_master(cls.import_run, cls.master, cls.route, 1)
        f.link_stop(cls.import_run, cls.route, cls.a, 1)
        f.link_stop(cls.import_run, cls.route, cls.b, 2)
        cls.paths = [
            ("/api/v1/routes/", {}),
            ("/api/v1/stops/", {"search": "A"}),
            (f"/api/v1/routes/{1}/", {}),
        ]

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_budget_is_shared_across_endpoints(self):
        for path, params in self.paths:
            response = self.client.get(path, params,
                                       REMOTE_ADDR="10.0.0.1")
            self.assertEqual(response.status_code, 200, path)
        response = self.client.get("/api/v1/stops/", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(response.status_code, 429)

    def test_over_limit_returns_plain_429_with_retry_after(self):
        for _ in range(3):
            self.client.get("/api/v1/routes/", REMOTE_ADDR="10.0.0.2")
        response = self.client.get("/api/v1/routes/",
                                   REMOTE_ADDR="10.0.0.2")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {
            "detail": "Too many requests. "
                      "Please wait a moment and try again.",
        })
        self.assertIn("Retry-After", response)

    def test_other_client_is_unaffected(self):
        for _ in range(3):
            self.client.get("/api/v1/routes/", REMOTE_ADDR="10.0.0.3")
        response = self.client.get("/api/v1/routes/",
                                   REMOTE_ADDR="10.0.0.4")
        self.assertEqual(response.status_code, 200)

    def test_counter_keys_carry_no_raw_ip(self):
        self.client.get("/api/v1/routes/", REMOTE_ADDR="10.9.8.7")
        cache = caches["default"]
        keys = list(cache._cache.keys())
        self.assertTrue(keys)
        for key in keys:
            self.assertNotIn("10.9.8.7", key)
            self.assertIn("throttle_transport_", key)

    def test_spoofed_forwarded_for_ignored_without_proxy(self):
        for _ in range(3):
            self.client.get("/api/v1/routes/", REMOTE_ADDR="10.0.0.5")
        response = self.client.get(
            "/api/v1/routes/", REMOTE_ADDR="10.0.0.5",
            HTTP_X_FORWARDED_FOR="9.9.9.9, 8.8.8.8")
        self.assertEqual(response.status_code, 429)

    @override_settings(TRANSPORT_TRUSTED_PROXY="proxy.internal")
    def test_forwarded_for_honoured_with_trusted_proxy(self):
        for _ in range(3):
            response = self.client.get(
                "/api/v1/routes/", REMOTE_ADDR="proxy.internal",
                HTTP_X_FORWARDED_FOR="9.9.9.9")
            self.assertEqual(response.status_code, 200)
        response = self.client.get(
            "/api/v1/routes/", REMOTE_ADDR="proxy.internal",
            HTTP_X_FORWARDED_FOR="9.9.9.9")
        self.assertEqual(response.status_code, 429)
        other = self.client.get(
            "/api/v1/routes/", REMOTE_ADDR="proxy.internal",
            HTTP_X_FORWARDED_FOR="1.1.1.1")
        self.assertEqual(other.status_code, 200)
