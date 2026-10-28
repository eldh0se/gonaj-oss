"""Versioned API root contract tests (contracts/api-root.md)."""
from django.test import TestCase


class ApiRootTests(TestCase):
    def test_version_root_returns_discovery_payload(self):
        response = self.client.get("/api/v1/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"name": "gonaj", "version": "v1"})

    def test_unknown_version_is_not_found(self):
        response = self.client.get("/api/v9/")
        self.assertEqual(response.status_code, 404)
