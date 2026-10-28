"""Admin login verification (spec Story 2, data-model Admin Account)."""
from django.contrib.auth.models import User
from django.test import TestCase


class AdminLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.username = "ops-admin"
        cls.password = "test-admin-pass-123"  # noqa: S105 - test fixture only
        User.objects.create_superuser(
            username=cls.username,
            email="ops@example.com",
            password=cls.password,
        )

    def test_login_page_renders(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)

    def test_valid_superuser_reaches_dashboard(self):
        logged_in = self.client.login(
            username=self.username, password=self.password
        )
        self.assertTrue(logged_in)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)

    def test_invalid_credentials_create_no_session(self):
        response = self.client.post(
            "/admin/login/",
            {"username": self.username, "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
