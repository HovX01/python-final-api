from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from users.tokens import email_verification_token


User = get_user_model()


class AuthFlowTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_creates_inactive_basic_user_and_sends_email(self):
        payload = {
            "email": "newuser@example.com",
            "password": "StrongPass123",
            "first_name": "New",
            "last_name": "User",
        }
        url = reverse("auth-register")
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email=payload["email"])
        self.assertFalse(user.is_active)
        self.assertEqual(user.user_type, User.UserType.BASIC)
        self.assertEqual(len(mail.outbox), 1)

    def test_verify_email_activates_user(self):
        user = User.objects.create_user(email="verifyme@example.com", password="Pass1234")
        token = email_verification_token.make_token(user)
        url = reverse("auth-verify-email")
        response = self.client.post(
            url, {"uid": user.pk, "token": token}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_login_blocks_inactive_or_disabled(self):
        inactive = User.objects.create_user(email="inactive@example.com", password="Pass1234")
        disabled = User.objects.create_user(
            email="disabled@example.com", password="Pass1234", is_active=True, is_disabled_by_admin=True
        )
        url = reverse("auth-login")

        resp_inactive = self.client.post(
            url, {"email": inactive.email, "password": "Pass1234"}, format="json"
        )
        self.assertEqual(resp_inactive.status_code, status.HTTP_400_BAD_REQUEST)

        resp_disabled = self.client.post(
            url, {"email": disabled.email, "password": "Pass1234"}, format="json"
        )
        self.assertEqual(resp_disabled.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_sets_refresh_cookie_and_returns_access(self):
        user = User.objects.create_user(
            email="active@example.com", password="Pass1234", is_active=True
        )
        url = reverse("auth-login")
        response = self.client.post(
            url, {"email": user.email, "password": "Pass1234"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh_token", response.cookies)

    def test_refresh_reads_cookie(self):
        user = User.objects.create_user(
            email="refresh@example.com", password="Pass1234", is_active=True
        )
        login_resp = self.client.post(
            reverse("auth-login"),
            {"email": user.email, "password": "Pass1234"},
            format="json",
        )
        refresh_cookie = login_resp.cookies["refresh_token"]

        self.client.cookies["refresh_token"] = refresh_cookie.value
        refresh_resp = self.client.post(reverse("auth-refresh"), {}, format="json")

        self.assertEqual(refresh_resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_resp.data)

    def test_logout_clears_refresh_cookie(self):
        user = User.objects.create_user(
            email="logout@example.com", password="Pass1234", is_active=True
        )
        login_resp = self.client.post(
            reverse("auth-login"),
            {"email": user.email, "password": "Pass1234"},
            format="json",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}"
        )
        self.client.cookies["refresh_token"] = login_resp.cookies["refresh_token"].value
        resp = self.client.post(reverse("auth-logout"), {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn("refresh_token", resp.cookies)

    def test_forgot_and_reset_password_flow(self):
        user = User.objects.create_user(
            email="resetme@example.com", password="OldPass123", is_active=True
        )
        forgot_resp = self.client.post(
            reverse("auth-forgot-password"),
            {"email": user.email},
            format="json",
        )
        self.assertEqual(forgot_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        from django.contrib.auth.tokens import default_token_generator

        token = default_token_generator.make_token(user)
        reset_resp = self.client.post(
            reverse("auth-reset-password"),
            {"uid": user.pk, "token": token, "new_password": "NewPass123"},
            format="json",
        )
        self.assertEqual(reset_resp.status_code, status.HTTP_200_OK)

        login_resp = self.client.post(
            reverse("auth-login"),
            {"email": user.email, "password": "NewPass123"},
            format="json",
        )
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
