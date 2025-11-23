from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from users.tokens import email_verification_token


def send_verification_email(user, request=None):
    token = email_verification_token.make_token(user)
    uid = user.pk
    path = reverse("auth-verify-email")
    verification_link = f"{settings.FRONTEND_URL.rstrip('/')}{path}?uid={uid}&token={token}"
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
