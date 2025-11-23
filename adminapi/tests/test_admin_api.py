from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from billing.models import Subscription
from apps.models import App, AppUser

User = get_user_model()


class AdminApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="Pass1234", is_active=True, is_staff=True, user_type=User.UserType.BASIC
        )
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass1234", is_active=True, user_type=User.UserType.PRO
        )
        Subscription.objects.create(user=self.user, status="active", plan_id="pro")
        app = App.objects.create(name="User App", owner=self.user)
        AppUser.objects.create(app=app, user=self.user, role=AppUser.Role.OWNER)
        self.client = APIClient()

    def test_admin_list_and_filter(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(reverse("admin-users-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 2)

        resp = self.client.get(reverse("admin-users-list"), {"email": "user@example.com"})
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["subscription_status"], "active")
        self.assertEqual(resp.data[0]["owned_app_count"], 1)

    def test_admin_detail_and_disable(self):
        self.client.force_authenticate(user=self.admin)
        detail_url = reverse("admin-users-detail", args=[self.user.id])
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], self.user.email)

        patch_resp = self.client.patch(detail_url, {"is_disabled_by_admin": True}, format="json")
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_disabled_by_admin)

    def test_non_admin_blocked(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(reverse("admin-users-list"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
