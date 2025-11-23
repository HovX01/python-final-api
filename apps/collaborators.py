from django.contrib.auth import get_user_model
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from apps.models import App, AppUser
from apps.permissions import IsAppOwner

User = get_user_model()


class CollaboratorSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = AppUser
        fields = ("user", "email", "role", "invited_at")
        read_only_fields = ("user", "email", "invited_at")


class CollaboratorAddSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=AppUser.Role.choices, default=AppUser.Role.VIEWER)

    def validate_email(self, value):
        try:
            user = User.objects.get(email__iexact=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        self.context["user_obj"] = user
        return value

    def create(self, validated_data):
        app: App = self.context["app"]
        user: User = self.context["user_obj"]
        if AppUser.objects.filter(app=app, user=user).exists():
            raise serializers.ValidationError({"detail": "User already a collaborator."})
        return AppUser.objects.create(app=app, user=user, role=validated_data["role"])


class CollaboratorListCreateView(APIView):
    permission_classes = [IsAppOwner]

    def initial(self, request, *args, **kwargs):
        app_id = kwargs.get("app_id")
        self.app = App.objects.filter(id=app_id).prefetch_related("app_users__user").first()
        if not self.app:
            from rest_framework.exceptions import NotFound
            raise NotFound("App not found.")
        super().initial(request, *args, **kwargs)

    @extend_schema(responses=CollaboratorSerializer(many=True))
    def get(self, request, app_id):
        collaborators = self.app.app_users.all()
        data = CollaboratorSerializer(collaborators, many=True).data
        return Response(data)

    @extend_schema(request=CollaboratorAddSerializer, responses=CollaboratorSerializer)
    def post(self, request, app_id):
        serializer = CollaboratorAddSerializer(data=request.data, context={"app": self.app})
        serializer.is_valid(raise_exception=True)
        collaborator = serializer.save()
        output = CollaboratorSerializer(collaborator).data
        return Response(output, status=status.HTTP_201_CREATED)


class CollaboratorDeleteView(APIView):
    permission_classes = [IsAppOwner]

    def initial(self, request, *args, **kwargs):
        app_id = kwargs.get("app_id")
        self.app = App.objects.filter(id=app_id).prefetch_related("app_users__user").first()
        if not self.app:
            from rest_framework.exceptions import NotFound
            raise NotFound("App not found.")
        super().initial(request, *args, **kwargs)

    @extend_schema(responses={204: None})
    def delete(self, request, app_id, user_id):
        membership = self.app.app_users.filter(user_id=user_id).first()
        if not membership:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if membership.role == AppUser.Role.OWNER:
            return Response({"detail": "Cannot remove owner."}, status=status.HTTP_400_BAD_REQUEST)
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
