from django.urls import path
from billing.views import (
    BillingPortalSessionView,
    StripeWebhookView,
    SubscriptionCheckoutSessionView,
    SubscriptionDetailView,
)

urlpatterns = [
    path("subscriptions/stripe/checkout/", SubscriptionCheckoutSessionView.as_view(), name="subscriptions-stripe-checkout"),
    path("subscriptions/stripe/portal/", BillingPortalSessionView.as_view(), name="subscriptions-stripe-portal"),
    path("subscriptions/me/", SubscriptionDetailView.as_view(), name="subscriptions-me"),
    path("subscriptions/stripe/webhook/", StripeWebhookView.as_view(), name="subscriptions-stripe-webhook"),
]
