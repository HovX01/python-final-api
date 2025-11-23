from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from users.emails import send_password_reset_email, send_verification_email
from users.serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    VerifyEmailSerializer,
)
from users.throttles import LoginRateThrottle, PasswordResetRateThrottle, RegisterRateThrottle


User = get_user_model()


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegisterRateThrottle]
    serializer_class = RegisterSerializer

    @extend_schema(request=RegisterSerializer, responses={201: OpenApiResponse(description="Verification email sent")})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_verification_email(user, request=request)
        return Response({"detail": "Verification email sent."}, status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = VerifyEmailSerializer

    @extend_schema(request=VerifyEmailSerializer, responses={200: OpenApiResponse(description="Email verified")})
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
        return Response({"detail": "Email verified."})


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginRateThrottle]

    def _set_refresh_cookie(self, response, refresh_token: str):
        response.set_cookie(
            settings.REFRESH_COOKIE_NAME,
            refresh_token,
            httponly=True,
            secure=settings.REFRESH_COOKIE_SECURE,
            samesite=settings.REFRESH_COOKIE_SAMESITE,
            path=settings.REFRESH_COOKIE_PATH,
            max_age=settings.REFRESH_TOKEN_MAX_AGE,
            domain=getattr(settings, "REFRESH_COOKIE_DOMAIN", None),
        )

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        refresh = response.data.get("refresh")
        if refresh:
            self._set_refresh_cookie(response, refresh)
            response.data.pop("refresh", None)
        return response


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]

    def _set_refresh_cookie(self, response, refresh_token: str):
        response.set_cookie(
            settings.REFRESH_COOKIE_NAME,
            refresh_token,
            httponly=True,
            secure=settings.REFRESH_COOKIE_SECURE,
            samesite=settings.REFRESH_COOKIE_SAMESITE,
            path=settings.REFRESH_COOKIE_PATH,
            max_age=settings.REFRESH_TOKEN_MAX_AGE,
            domain=getattr(settings, "REFRESH_COOKIE_DOMAIN", None),
        )

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh") or request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not refresh_token:
            return Response({"detail": "Refresh token not provided."}, status=status.HTTP_400_BAD_REQUEST)
        request.data["refresh"] = refresh_token
        response = super().post(request, *args, **kwargs)
        new_refresh = response.data.get("refresh")
        if new_refresh:
            self._set_refresh_cookie(response, new_refresh)
            response.data.pop("refresh", None)
        return response


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={204: OpenApiResponse(description="Logged out")})
    def post(self, request):
        refresh_token = request.data.get("refresh") or request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(
            settings.REFRESH_COOKIE_NAME,
            path=settings.REFRESH_COOKIE_PATH,
            domain=getattr(settings, "REFRESH_COOKIE_DOMAIN", None),
        )
        if not refresh_token:
            return response

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            pass
        return response


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetRateThrottle]
    serializer_class = PasswordResetRequestSerializer

    @extend_schema(request=PasswordResetRequestSerializer, responses={200: OpenApiResponse(description="Email sent if exists")})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.context.get("user")
        if user:
            send_password_reset_email(user)
        return Response({"detail": "If the account exists, an email has been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    @extend_schema(request=PasswordResetConfirmSerializer, responses={200: OpenApiResponse(description="Password reset")})
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password has been reset."})
