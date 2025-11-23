from rest_framework.routers import DefaultRouter
from django.urls import path, include
from apps.views import AppViewSet
from apps.collaborators import CollaboratorListCreateView, CollaboratorDeleteView

router = DefaultRouter()
router.register(r"apps", AppViewSet, basename="app")

urlpatterns = [
    path("apps/<int:app_id>/collaborators/", CollaboratorListCreateView.as_view(), name="app-collaborators"),
    path("apps/<int:app_id>/collaborators/<int:user_id>/", CollaboratorDeleteView.as_view(), name="app-collaborators-delete"),
    path("", include(router.urls)),
]
