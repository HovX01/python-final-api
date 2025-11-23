from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class HealthAndSchemaTests(APITestCase):
    def test_health_endpoint(self):
        resp = self.client.get(reverse("health"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data.get("status"), "ok")

    def test_schema_available(self):
        resp = self.client.get(reverse("schema"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("openapi", resp.data)
