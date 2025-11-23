from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers
from billing.models import Subscription


User = get_user_model()


class CheckoutSessionSerializer(serializers.Serializer):
    plan_id = serializers.ChoiceField(choices=[(k, k) for k in settings.PLAN_PRICE_MAP.keys()])


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = (
            "status",
            "plan_id",
            "price_id",
            "cancel_at_period_end",
            "current_period_end",
            "current_period_start",
            "trial_end",
            "stripe_subscription_id",
        )
