from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from users.tokens import email_verification_token


User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name")

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.IntegerField()
    token = serializers.CharField()

    def validate(self, attrs):
        try:
            user = User.objects.get(pk=attrs["uid"])
        except User.DoesNotExist:
            raise serializers.ValidationError(_("Invalid user."))

        if user.is_disabled_by_admin:
            raise serializers.ValidationError(_("User is disabled by admin."))

        if not email_verification_token.check_token(user, attrs["token"]):
            raise serializers.ValidationError(_("Invalid or expired token."))

        attrs["user"] = user
        return attrs


class LoginSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD

    def validate(self, attrs):
        credentials = {
            "email": attrs.get("email"),
            "password": attrs.get("password"),
        }
        user = authenticate(
            request=self.context.get("request"),
            **{User.USERNAME_FIELD: credentials["email"], "password": credentials["password"]},
        )
        if not user:
            raise serializers.ValidationError(_("Invalid credentials."))

        if not user.is_active:
            raise serializers.ValidationError(_("Please verify your email before logging in."))

        if user.is_disabled_by_admin:
            raise serializers.ValidationError(_("User is disabled by admin."))

        refresh = self.get_token(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email__iexact=value)
        except User.DoesNotExist:
            return value
        if user.is_disabled_by_admin:
            raise serializers.ValidationError(_("User is disabled by admin."))
        self.context["user"] = user
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.IntegerField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        try:
            user = User.objects.get(pk=attrs["uid"])
        except User.DoesNotExist:
            raise serializers.ValidationError(_("Invalid user."))

        if user.is_disabled_by_admin:
            raise serializers.ValidationError(_("User is disabled by admin."))

        from django.contrib.auth.tokens import default_token_generator

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError(_("Invalid or expired token."))

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        new_password = self.validated_data["new_password"]
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return user
