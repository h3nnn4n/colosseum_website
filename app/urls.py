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
    # FIXME: This is obviously temporary
    path("agents/", views.AgentListView.as_view(), name="agents"),
    path("agents/<str:pk>/", views.AgentDetailView.as_view(), name="agent_detail"),
    path("agents/<str:pk>/edit/", views.AgentUpdateView.as_view(), name="agent_edit"),
    path("agent/upload/", views.upload, name="agent_upload"),
    path("agent/upload_success/", views.upload_success, name="agent_upload_success"),
    path("home/", views.index, name="home"),
    path("api/", include(router.urls)),
    path(
        "", RedirectView.as_view(url="home/", permanent=True), name="redirect_to_home"
    ),
    path("accounts/register/", views.register_request, name="register"),
]
