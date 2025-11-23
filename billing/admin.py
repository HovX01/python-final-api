from django.contrib import admin
from billing.models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "plan_id", "stripe_subscription_id", "cancel_at_period_end", "current_period_end")
    search_fields = ("user__email", "stripe_subscription_id", "stripe_customer_id")
    list_filter = ("status", "plan_id", "cancel_at_period_end")
