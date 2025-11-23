from django.urls import path
from adminapi.views import AdminUserListView, AdminUserDetailView


urlpatterns = [
    path("admin/users/", AdminUserListView.as_view(), name="admin-users-list"),
    path("admin/users/<int:user_id>/", AdminUserDetailView.as_view(), name="admin-users-detail"),
]
