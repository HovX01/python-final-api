import stripe
from datetime import datetime, timezone as dt_timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from billing.models import Subscription
from billing.serializers import CheckoutSessionSerializer, SubscriptionSerializer

User = get_user_model()

stripe.api_key = settings.STRIPE_SECRET_KEY


def get_or_create_subscription(user: User) -> Subscription:
    subscription, _ = Subscription.objects.get_or_create(user=user)
    return subscription


def ensure_customer(subscription: Subscription, user: User) -> str:
    if subscription.stripe_customer_id:
        return subscription.stripe_customer_id
    customer = stripe.Customer.create(
        email=user.email,
        name=f"{user.first_name} {user.last_name}".strip() or None,
        metadata={"user_id": user.id},
    )
    subscription.stripe_customer_id = customer["id"]
    subscription.save(update_fields=["stripe_customer_id", "updated_at"])
    return customer["id"]


def update_user_plan(subscription: Subscription):
    user = subscription.user
    if subscription.status in (
        Subscription.Status.ACTIVE,
        Subscription.Status.TRIALING,
    ):
        if subscription.plan_id and user.user_type != subscription.plan_id:
            user.user_type = subscription.plan_id
            user.save(update_fields=["user_type"])
    elif subscription.status in (
        Subscription.Status.CANCELED,
        Subscription.Status.INCOMPLETE,
        Subscription.Status.INCOMPLETE_EXPIRED,
        Subscription.Status.UNPAID,
    ):
        if user.user_type != User.UserType.BASIC:
            user.user_type = User.UserType.BASIC
            user.save(update_fields=["user_type"])


def apply_subscription_data(subscription: Subscription, data: dict):
    items = data.get("items", {}).get("data", [])
    price_id = None
    if items:
        price = items[0].get("price", {})
        price_id = price.get("id")
    status_value = data.get("status", Subscription.Status.INCOMPLETE)
    cancel_at_period_end = data.get("cancel_at_period_end", False)

    def parse_timestamp(value):
        if value is None:
            return None
        return datetime.fromtimestamp(value, tz=dt_timezone.utc)

    subscription.stripe_subscription_id = data.get("id") or subscription.stripe_subscription_id
    subscription.stripe_customer_id = data.get("customer") or subscription.stripe_customer_id
    subscription.mark_status(
        status=status_value,
        price_id=price_id,
        cancel_at_period_end=cancel_at_period_end,
        period_end=parse_timestamp(data.get("current_period_end")),
        period_start=parse_timestamp(data.get("current_period_start")),
        trial_end=parse_timestamp(data.get("trial_end")),
    )
    update_user_plan(subscription)


class SubscriptionCheckoutSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan_id = serializer.validated_data["plan_id"]
        price_id = settings.PLAN_PRICE_MAP.get(plan_id)
        user = request.user
        subscription = get_or_create_subscription(user)
        customer_id = ensure_customer(subscription, user)
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            success_url=settings.CHECKOUT_SUCCESS_URL,
            cancel_url=settings.CHECKOUT_CANCEL_URL,
            subscription_data={"metadata": {"plan_id": plan_id}},
            metadata={"user_id": user.id, "plan_id": plan_id},
        )
        if session.get("subscription"):
            subscription.stripe_subscription_id = session["subscription"]
            subscription.price_id = price_id
            subscription.set_plan_from_price(price_id)
            subscription.save(update_fields=["stripe_subscription_id", "price_id", "plan_id", "updated_at"])
        return Response({"checkout_url": session.get("url")})


class BillingPortalSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        subscription = get_or_create_subscription(user)
        customer_id = ensure_customer(subscription, user)
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=settings.PORTAL_RETURN_URL,
        )
        return Response({"portal_url": portal_session.get("url")})


class SubscriptionDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        subscription = Subscription.objects.filter(user=request.user).first()
        if not subscription:
            return Response({"subscription": None})
        data = SubscriptionSerializer(subscription).data
        return Response({"subscription": data})


class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return Response({"detail": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response({"detail": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event.get("type")
        data_object = event.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            user_id = data_object.get("metadata", {}).get("user_id")
            user = User.objects.filter(id=user_id).first()
            if not user:
                return Response(status=status.HTTP_200_OK)
            subscription = get_or_create_subscription(user)
            subscription.stripe_customer_id = data_object.get("customer") or subscription.stripe_customer_id
            subscription.stripe_subscription_id = data_object.get("subscription") or subscription.stripe_subscription_id
            subscription.save(update_fields=["stripe_customer_id", "stripe_subscription_id", "updated_at"])
            if subscription.stripe_subscription_id:
                sub_data = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
                apply_subscription_data(subscription, sub_data)
        elif event_type.startswith("customer.subscription."):
            subscription_id = data_object.get("id")
            subscription = Subscription.objects.filter(stripe_subscription_id=subscription_id).first()
            if not subscription:
                customer_id = data_object.get("customer")
                subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
            if subscription:
                apply_subscription_data(subscription, data_object)
        return Response(status=status.HTTP_200_OK)
