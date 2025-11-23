from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.models import AppUser, App


class IsAppMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        membership = obj.app_users.filter(user=request.user).first()
        if not membership:
            return False
        if request.method in SAFE_METHODS:
            return True
        if request.method in ("PUT", "PATCH"):
            return membership.role in (AppUser.Role.OWNER, AppUser.Role.EDITOR)
        if request.method == "DELETE":
            return membership.role == AppUser.Role.OWNER
        return False


class IsAppOwner(BasePermission):
    def has_permission(self, request, view):
        app = getattr(view, "app", None)
        if isinstance(app, App):
            return app.app_users.filter(user=request.user, role=AppUser.Role.OWNER).exists()
        return False
