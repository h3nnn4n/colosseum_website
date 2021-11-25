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
    path("agents/create/", views.AgentCreateView.as_view(), name="agent_create"),
    path("agents/<str:pk>/", views.AgentDetailView.as_view(), name="agent_detail"),
    path("agents/<str:pk>/edit/", views.AgentUpdateView.as_view(), name="agent_edit"),
    # Match pages
    path("matches/", views.MatchListView.as_view(), name="matches"),
    # Tournaments
    path("tournaments/", views.TournamentListView.as_view(), name="tournaments"),
    path(
        "tournaments/<str:pk>/",
        views.TournamentDetailView.as_view(),
        name="tournament_detail",
    ),
    # About page
    path("about/", views.AboutView.as_view(), name="about"),
    # Home
    path(
        "", RedirectView.as_view(url="home/", permanent=True), name="redirect_to_home"
    ),
    path("home/", views.index, name="home"),
    # API
    path("api/", include(router.urls)),
    path("api/next_match/", views.NextMatchAPIView.as_view(), name="next_match"),
    # Register page
    path("accounts/register/", views.register_request, name="register"),
    # Plots
    path("plots/matches_per_day/", views.plot_matches_per_day, name="matches_per_day"),
    path("plots/agent_elo_plot/<str:pk>/", views.plot_agent_elo, name="agent_elo_plot"),
]
