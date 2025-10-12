# tests/test_password_reset_uniform_response.py
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

class PasswordResetUniformResponseTests(APITestCase):
    def setUp(self):
        U = get_user_model()
        U.objects.create_user(username="alice", email="alice@example.com", password="x")

    def test_uniform_response_existing(self):
        r = self.client.post("/api/auth/password-reset/", {"email":"alice@example.com"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("detail", r.json())

    def test_uniform_response_non_existing(self):
        r = self.client.post("/api/auth/password-reset/", {"email":"nope@example.com"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("detail", r.json())