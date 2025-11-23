from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class App(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_apps")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("owner", "name")
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class AppUser(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"

    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="app_users")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="app_memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    invited_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("app", "user")

    def __str__(self):
        return f"{self.user.email} -> {self.app.name} ({self.role})"
