from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from apps.models import App, AppUser


User = get_user_model()


class AppTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", password="Pass1234", is_active=True, user_type=User.UserType.BASIC
        )
        self.editor = User.objects.create_user(
            email="editor@example.com", password="Pass1234", is_active=True, user_type=User.UserType.BASIC
        )
        self.viewer = User.objects.create_user(
            email="viewer@example.com", password="Pass1234", is_active=True, user_type=User.UserType.BASIC
        )
        self.client = APIClient()

    def test_create_app_respects_limit(self):
        self.client.force_authenticate(user=self.owner)
        # create up to limit 3 for basic
        for i in range(3):
            resp = self.client.post(reverse("app-list"), {"name": f"App {i}", "description": ""}, format="json")
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        resp = self.client.post(reverse("app-list"), {"name": "App 4"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(resp.data.get("code"), "APP_LIMIT_REACHED")

    def test_list_shows_only_memberships(self):
        app_owned = App.objects.create(name="Owned App", owner=self.owner)
        AppUser.objects.create(app=app_owned, user=self.owner, role=AppUser.Role.OWNER)
        app_shared = App.objects.create(name="Shared App", owner=self.owner)
        AppUser.objects.create(app=app_shared, user=self.viewer, role=AppUser.Role.VIEWER)

        self.client.force_authenticate(user=self.viewer)
        resp = self.client.get(reverse("app-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["name"], "Shared App")

    def test_update_permissions(self):
        app = App.objects.create(name="Owner App", owner=self.owner)
        AppUser.objects.create(app=app, user=self.owner, role=AppUser.Role.OWNER)
        AppUser.objects.create(app=app, user=self.editor, role=AppUser.Role.EDITOR)
        AppUser.objects.create(app=app, user=self.viewer, role=AppUser.Role.VIEWER)

        # Viewer cannot update
        self.client.force_authenticate(user=self.viewer)
        resp = self.client.patch(reverse("app-detail", args=[app.id]), {"name": "New Name"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # Editor can update
        self.client.force_authenticate(user=self.editor)
        resp = self.client.patch(reverse("app-detail", args=[app.id]), {"name": "Editor Name"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        app.refresh_from_db()
        self.assertEqual(app.name, "Editor Name")

        # Only owner can delete
        resp = self.client.delete(reverse("app-detail", args=[app.id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.owner)
        resp = self.client.delete(reverse("app-detail", args=[app.id]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_collaborators_list_add_delete_owner_only(self):
        app = App.objects.create(name="Owner App", owner=self.owner)
        AppUser.objects.create(app=app, user=self.owner, role=AppUser.Role.OWNER)

        # non-owner cannot list or add
        self.client.force_authenticate(user=self.editor)
        list_resp = self.client.get(reverse("app-collaborators", args=[app.id]))
        self.assertEqual(list_resp.status_code, status.HTTP_403_FORBIDDEN)
        add_resp = self.client.post(
            reverse("app-collaborators", args=[app.id]),
            {"email": self.editor.email, "role": AppUser.Role.EDITOR},
            format="json",
        )
        self.assertEqual(add_resp.status_code, status.HTTP_403_FORBIDDEN)

        # owner adds collaborator
        self.client.force_authenticate(user=self.owner)
        add_resp = self.client.post(
            reverse("app-collaborators", args=[app.id]),
            {"email": self.editor.email, "role": AppUser.Role.EDITOR},
            format="json",
        )
        self.assertEqual(add_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(add_resp.data["role"], AppUser.Role.EDITOR)

        list_resp = self.client.get(reverse("app-collaborators", args=[app.id]))
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_resp.data), 2)

        # owner cannot remove owner, can remove collaborator
        delete_owner_resp = self.client.delete(
            reverse("app-collaborators-delete", args=[app.id, self.owner.id])
        )
        self.assertEqual(delete_owner_resp.status_code, status.HTTP_400_BAD_REQUEST)

        delete_collab_resp = self.client.delete(
            reverse("app-collaborators-delete", args=[app.id, self.editor.id])
        )
        self.assertEqual(delete_collab_resp.status_code, status.HTTP_204_NO_CONTENT)
