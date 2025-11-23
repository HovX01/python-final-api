from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model


User = get_user_model()


class Subscription(models.Model):
    class Status(models.TextChoices):
        INCOMPLETE = "incomplete", "Incomplete"
        INCOMPLETE_EXPIRED = "incomplete_expired", "Incomplete Expired"
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"
        UNPAID = "unpaid", "Unpaid"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    price_id = models.CharField(max_length=255, blank=True, null=True)
    plan_id = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=64, choices=Status.choices, default=Status.INCOMPLETE)
    cancel_at_period_end = models.BooleanField(default=False)
    current_period_end = models.DateTimeField(blank=True, null=True)
    current_period_start = models.DateTimeField(blank=True, null=True)
    trial_end = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_plan_from_price(self, price_id: str | None):
        if not price_id:
            self.plan_id = ""
            return
        for plan, pid in settings.PLAN_PRICE_MAP.items():
            if pid == price_id:
                self.plan_id = plan
                return
        self.plan_id = ""

    def mark_status(self, status: str, price_id: str | None = None, cancel_at_period_end: bool | None = None, period_end=None, period_start=None, trial_end=None):
        self.status = status
        if price_id:
            self.price_id = price_id
            self.set_plan_from_price(price_id)
        if cancel_at_period_end is not None:
            self.cancel_at_period_end = cancel_at_period_end
        if period_end:
            self.current_period_end = timezone.make_aware(period_end) if timezone.is_naive(period_end) else period_end
        if period_start:
            self.current_period_start = timezone.make_aware(period_start) if timezone.is_naive(period_start) else period_start
        if trial_end:
            self.trial_end = timezone.make_aware(trial_end) if timezone.is_naive(trial_end) else trial_end
        self.save()

    def __str__(self):
        return f"{self.user.email} - {self.status}"
