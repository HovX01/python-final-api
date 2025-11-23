from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from users.tokens import email_verification_token


def _build_link(path: str, uid, token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}?uid={uid}&token={token}"


def send_verification_email(user, request=None):
    token = email_verification_token.make_token(user)
    uid = user.pk
    path = reverse("auth-verify-email")
    verification_link = _build_link(path, uid, token)
    subject = "Verify your email"
    message = (
        "Welcome! Please verify your email to activate your account.\n"
        f"Verification link: {verification_link}\n"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[user.email],
    )
    return token


def send_password_reset_email(user):
    token = default_token_generator.make_token(user)
    uid = user.pk
    path = reverse("auth-reset-password")
    reset_link = _build_link(path, uid, token)
    subject = "Reset your password"
    message = (
        "You requested a password reset.\n"
        f"Reset link: {reset_link}\n"
        "If you did not request this, you can ignore this email."
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[user.email],
    )
    return token
