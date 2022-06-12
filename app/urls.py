from django.urls import include, path
from django.views.generic.base import RedirectView
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register(r"users", views.UserViewSet)
router.register(r"agents", views.AgentViewSet)
router.register(r"games", views.GameViewSet)
router.register(r"seasons", views.SeasonViewSet)
router.register(r"matches", views.MatchViewSet)
router.register(r"tournaments", views.TournamentViewSet)

favicon_view = RedirectView.as_view(url="/static/favicon.ico", permanent=True)

urlpatterns = [
    # favicon
    path("favicon.ico", favicon_view, name="favicon"),
    # Agents pages
    path("agents/", views.AgentListView.as_view(), name="agents"),
    path("agents/create/", views.AgentCreateView.as_view(), name="agent_create"),
    path("agents/<str:pk>/", views.AgentDetailView.as_view(), name="agent_detail"),
    path("agents/<str:pk>/edit/", views.AgentUpdateView.as_view(), name="agent_edit"),
    # Games pages
    path("games/", views.GameListView.as_view(), name="games"),
    path("games/<str:pk>/", views.GameDetailView.as_view(), name="game_detail"),
    # Seasons pages
    path("seasons/", views.SeasonListView.as_view(), name="seasons"),
    path("seasons/<str:pk>/", views.SeasonDetailView.as_view(), name="season_detail"),
    # Match pages
    path("matches/", views.MatchListView.as_view(), name="matches"),
    path("matches/<str:pk>/", views.MatchDetailView.as_view(), name="match_detail"),
    path(
        "matches/<str:pk>/replay/", views.MatchReplayView.as_view(), name="match_replay"
    ),
    # Tournaments
    path("tournaments/", views.TournamentListView.as_view(), name="tournaments"),
    path(
        "tournaments/<str:pk>/",
        views.TournamentDetailView.as_view(),
        name="tournament_detail",
    ),
    # Users pages
    path("users/", views.UserListView.as_view(), name="users"),
    path("users/<str:pk>/", views.UserDetailView.as_view(), name="user_detail"),
    path("users/<str:pk>/edit/", views.UserEditView.as_view(), name="user_edit"),
    # About page
    path("about/", views.AboutView.as_view(), name="about"),
    # Home
    path(
        "home/",
        RedirectView.as_view(url="home/", permanent=False),
        name="redirect_to_home",
    ),
    path("/", views.HomeView.as_view(), name="home"),
    # API
    path("api/", include(router.urls)),
    path("api/next_match/", views.NextMatchAPIView.as_view(), name="next_match"),
    path(
        "api/automated_seasons/",
        views.AutomatedSeasonsAPIView.as_view(),
        name="automated_seasons",
    ),
    path(
        "api/colosseum_heartbeat/",
        views.ColosseumHeartbeatAPIView.as_view(),
        name="colosseum_heartbeat",
    ),
    # Register page
    path("accounts/register/", views.register_request, name="register"),
    # Plots
    path("plots/matches_per_day/", views.plot_matches_per_day, name="matches_per_day"),
    path("plots/agent_elo_plot/<str:pk>/", views.plot_agent_elo, name="agent_elo_plot"),
    # Debug
    path("api/debug/ping/", views.PingAPIView.as_view(), name="ping"),
    path("api/debug/redis_info/", views.RedisInfoAPIView.as_view(), name="redis_info"),
    path(
        "api/debug/match_queue/",
        views.MatchQueueDebugAPIView.as_view(),
        name="match_queue_debug",
    ),
    path(
        "api/debug/tainted_matches/",
        views.TaintedMatchesDebugAPIView.as_view(),
        name="tainted_matches_debug",
    ),
]
