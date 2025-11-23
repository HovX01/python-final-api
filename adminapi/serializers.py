from django.contrib.auth import get_user_model
from rest_framework import serializers
from billing.models import Subscription

User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    subscription_status = serializers.SerializerMethodField()
    subscription_plan = serializers.SerializerMethodField()
    owned_app_count = serializers.IntegerField(source="owned_apps.count", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "user_type",
            "is_active",
            "is_disabled_by_admin",
            "subscription_status",
            "subscription_plan",
            "owned_app_count",
        )

    def get_subscription_status(self, obj):
        sub = getattr(obj, "subscription", None)
        return sub.status if sub else None

    def get_subscription_plan(self, obj):
        sub = getattr(obj, "subscription", None)
        return sub.plan_id if sub else None


class AdminUserToggleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("is_disabled_by_admin",)
