from django.urls import include, path, re_path
from django.views.generic.base import RedirectView
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register(r"users", views.UserViewSet)
router.register(r"agents", views.AgentViewSet)
router.register(r"games", views.GameViewSet)
router.register(r"matches", views.MatchViewSet)
router.register(r"tournaments", views.TournamentViewSet)

urlpatterns = [
    path("agent/upload/", views.upload, name="agent_upload"),
    path("home/", views.index, name="home"),
    path("api/", include(router.urls)),
    path(
        "", RedirectView.as_view(url="home/", permanent=True), name="redirect_to_home"
    ),
    path("accounts/register/", views.register_request, name="register"),
]
