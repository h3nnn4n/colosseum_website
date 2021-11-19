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
    # Agents pages
    path("agents/", views.AgentListView.as_view(), name="agents"),
    path("agents/<str:pk>/", views.AgentDetailView.as_view(), name="agent_detail"),
    path("agents/<str:pk>/edit/", views.AgentUpdateView.as_view(), name="agent_edit"),
    # Match pages
    path("matches/", views.MatchListView.as_view(), name="matches"),
    # FIXME: This is obviously temporary
    path("agent/upload/", views.upload, name="agent_upload"),
    path("agent/upload_success/", views.upload_success, name="agent_upload_success"),
    # Home
    path(
        "", RedirectView.as_view(url="home/", permanent=True), name="redirect_to_home"
    ),
    path("home/", views.index, name="home"),
    # API
    path("api/", include(router.urls)),
    # Register page
    path("accounts/register/", views.register_request, name="register"),
    # WIP pages
    path("tournaments/", views.wip, name="tournaments"),
    path("about/", views.wip, name="about"),
]
