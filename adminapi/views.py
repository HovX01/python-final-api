from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from adminapi.permissions import IsAdminUserType
from adminapi.serializers import AdminUserSerializer, AdminUserToggleSerializer

User = get_user_model()


class AdminUserListView(APIView):
    permission_classes = [IsAdminUserType]

    def get(self, request):
        qs = User.objects.all().annotate(owned_app_count=Count("owned_apps"))

        email = request.query_params.get("email")
        user_type = request.query_params.get("user_type")
        is_disabled = request.query_params.get("is_disabled_by_admin")
        subscription_status = request.query_params.get("subscription_status")

        if email:
            qs = qs.filter(email__icontains=email)
        if user_type:
            qs = qs.filter(user_type=user_type)
        if is_disabled is not None:
            if is_disabled.lower() == "true":
                qs = qs.filter(is_disabled_by_admin=True)
            elif is_disabled.lower() == "false":
                qs = qs.filter(is_disabled_by_admin=False)
        if subscription_status:
            qs = qs.filter(subscription__status=subscription_status)

        serializer = AdminUserSerializer(qs, many=True)
        return Response(serializer.data)


class AdminUserDetailView(APIView):
    permission_classes = [IsAdminUserType]

    def get_object(self, pk):
        return User.objects.annotate(owned_app_count=Count("owned_apps")).filter(pk=pk).first()

    def get(self, request, user_id):
        user = self.get_object(user_id)
        if not user:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = AdminUserSerializer(user)
        return Response(serializer.data)

    def patch(self, request, user_id):
        user = self.get_object(user_id)
        if not user:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = AdminUserToggleSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminUserSerializer(user).data)
