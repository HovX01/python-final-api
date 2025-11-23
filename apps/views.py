from rest_framework import viewsets, status
from rest_framework.response import Response
from apps.models import App
from apps.permissions import IsAppMember
from apps.serializers import AppSerializer
from django.conf import settings


class AppViewSet(viewsets.ModelViewSet):
    serializer_class = AppSerializer
    permission_classes = [IsAppMember]

    def get_queryset(self):
        user = self.request.user
        return App.objects.filter(app_users__user=user).distinct()

    def create(self, request, *args, **kwargs):
        user = request.user
        owned_count = App.objects.filter(owner=user).count()
        limit = settings.PLAN_LIMITS.get(user.user_type, 0)
        if owned_count >= limit:
            return Response(
                {"detail": f"App limit reached for plan {user.user_type}.", "code": "APP_LIMIT_REACHED"},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        return serializer.save()
