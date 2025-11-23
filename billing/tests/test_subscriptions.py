import json
from unittest import mock
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from billing.models import Subscription


User = get_user_model()


class SubscriptionTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="sub@example.com", password="Pass1234", is_active=True, user_type=User.UserType.BASIC
        )
        self.client.force_authenticate(user=self.user)

    @mock.patch("billing.views.stripe.checkout.Session.create")
    @mock.patch("billing.views.stripe.Customer.create")
    def test_checkout_session_creates_customer_and_returns_url(self, mock_customer_create, mock_session_create):
        mock_customer_create.return_value = {"id": "cus_123"}
        mock_session_create.return_value = {"id": "cs_123", "url": "https://checkout.test", "subscription": "sub_123"}

        response = self.client.post(
            reverse("subscriptions-stripe-checkout"),
            {"plan_id": "pro"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("checkout_url", response.data)
        subscription = Subscription.objects.get(user=self.user)
        self.assertEqual(subscription.stripe_customer_id, "cus_123")
        self.assertEqual(subscription.stripe_subscription_id, "sub_123")
        self.assertEqual(subscription.plan_id, "pro")

    @mock.patch("billing.views.stripe.billing_portal.Session.create")
    @mock.patch("billing.views.ensure_customer")
    def test_billing_portal_session(self, mock_ensure_customer, mock_portal_create):
        mock_ensure_customer.return_value = "cus_123"
        mock_portal_create.return_value = {"id": "bps_123", "url": "https://portal.test"}

        response = self.client.post(reverse("subscriptions-stripe-portal"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("portal_url", response.data)

    def test_subscription_me_returns_data(self):
        subscription = Subscription.objects.create(
            user=self.user,
            status=Subscription.Status.ACTIVE,
            plan_id="pro",
            price_id="price_pro_placeholder",
            stripe_subscription_id="sub_abc",
        )
        response = self.client.get(reverse("subscriptions-me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["subscription"]["plan_id"], "pro")
        self.assertEqual(response.data["subscription"]["stripe_subscription_id"], subscription.stripe_subscription_id)

    @mock.patch("billing.views.stripe.Webhook.construct_event")
    @mock.patch("billing.views.apply_subscription_data")
    def test_webhook_updates_subscription_on_customer_event(self, mock_apply, mock_construct):
        subscription = Subscription.objects.create(
            user=self.user, stripe_subscription_id="sub_123", stripe_customer_id="cus_123"
        )
        event_payload = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123",
                    "status": "active",
                    "items": {"data": [{"price": {"id": "price_pro_placeholder"}}]},
                }
            },
        }
        mock_construct.return_value = event_payload

        response = self.client.post(
            reverse("subscriptions-stripe-webhook"),
            data=json.dumps({"dummy": "data"}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_apply.assert_called_once()
        self.assertEqual(mock_apply.call_args[0][0], subscription)

    @mock.patch("billing.views.stripe.Subscription.retrieve")
    @mock.patch("billing.views.stripe.Webhook.construct_event")
    def test_checkout_session_webhook_fetches_subscription_details(self, mock_construct, mock_retrieve):
        mock_retrieve.return_value = {
            "id": "sub_456",
            "customer": "cus_456",
            "status": "active",
            "items": {"data": [{"price": {"id": "price_pro_placeholder"}}]},
            "current_period_end": 1735689600,
            "current_period_start": 1733097600,
        }
        event_payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test",
                    "customer": "cus_456",
                    "subscription": "sub_456",
                    "metadata": {"user_id": self.user.id, "plan_id": "pro"},
                }
            },
        }
        mock_construct.return_value = event_payload

        response = self.client.post(
            reverse("subscriptions-stripe-webhook"),
            data=json.dumps({"dummy": "data"}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_retrieve.assert_called_once_with("sub_456")
        subscription = Subscription.objects.get(user=self.user)
        self.assertEqual(subscription.stripe_subscription_id, "sub_456")
        self.assertEqual(subscription.stripe_customer_id, "cus_456")
