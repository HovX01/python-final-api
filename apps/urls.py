from rest_framework.routers import DefaultRouter
from apps.views import AppViewSet

router = DefaultRouter()
router.register(r"apps", AppViewSet, basename="app")

urlpatterns = router.urls
