from django.conf import settings
from rest_framework import serializers
from apps.models import App, AppUser


class AppSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = App
        fields = ("id", "name", "description", "created_at", "updated_at", "role")
        read_only_fields = ("id", "created_at", "updated_at", "role")

    def get_role(self, obj) -> str | None:
        user = self.context["request"].user
        membership = obj.app_users.filter(user=user).first()
        return membership.role if membership else None

    def create(self, validated_data):
        user = self.context["request"].user
        app = App.objects.create(owner=user, **validated_data)
        AppUser.objects.create(app=app, user=user, role=AppUser.Role.OWNER)
        return app
