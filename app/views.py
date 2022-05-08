import json
import logging
import lzma
from datetime import datetime, timedelta

import humanize
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db.models import F
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import generic
from django.views.decorators.cache import cache_page
from django_redis import get_redis_connection
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from app import (
    constants,
    forms,
    metrics,
    models,
    permissions,
    serializers,
    services,
    utils,
)
from app.services import match_queue

from . import plots


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("APP")


class AgentListView(generic.ListView):
    template_name = "agents/index.html"
    context_object_name = "agents"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["games"] = models.Game.objects.all().order_by("name")
        return context

    def get_queryset(self):
        return (
            models.Agent.objects.all()
            .annotate(
                elo_rating=F("ratings__elo"),
                owner_username=F("owner__username"),
            )
            .filter(ratings__season__active=True, ratings__season__main=True)
            .order_by("-elo_rating")
        )


class AgentDetailView(generic.DetailView):
    model = models.Agent
    template_name = "agents/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        trophies = services.trophy.trophies_for_agent(self.get_object())
        context["first_place_trophies"] = trophies["FIRST"]
        context["second_place_trophies"] = trophies["SECOND"]
        context["third_place_trophies"] = trophies["THIRD"]

        return context


class AgentCreateView(LoginRequiredMixin, generic.CreateView):
    model = models.Agent
    template_name = "agents/create.html"
    success_url = "/agents/"
    form_class = forms.AgentForm

    def get_form_kwargs(self):
        kwargs = super(AgentCreateView, self).get_form_kwargs()
        if hasattr(self, "object"):
            kwargs.update({"instance": self.object})
        kwargs["user"] = self.request.user
        return kwargs


class AgentUpdateView(permissions.IsOwnerPermissionMixin, generic.UpdateView):
    model_permission_user_field = "owner"
    model = models.Agent
    template_name = "agents/edit.html"
    success_url = "/agents/"
    form_class = forms.AgentForm

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.owner = request.user
        return super().post(request, *args, **kwargs)


class GameListView(generic.ListView):
    template_name = "games/index.html"
    context_object_name = "games"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["games"] = models.Game.objects.all().order_by("name")
        return context

    def get_queryset(self):
        return models.Game.objects.all()


class GameDetailView(generic.DetailView):
    model = models.Game
    template_name = "games/detail.html"


class SeasonListView(generic.ListView):
    template_name = "seasons/index.html"
    context_object_name = "seasons"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["seasons"] = models.Season.objects.all().order_by("-end_date")[:25]
        return context

    def get_queryset(self):
        return models.Season.objects.all()


class SeasonDetailView(generic.DetailView):
    model = models.Season
    template_name = "seasons/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        season = self.get_object()
        context["tournaments"] = season.tournaments.order_by("-end_date")[:25]
        context["trophies"] = services.trophy.trophies_for_season(season)

        return context


class MatchListView(generic.ListView):
    template_name = "matches/index.html"
    context_object_name = "matches"

    def get_queryset(self):
        return (
            models.Match.objects.filter(ran=True)
            .prefetch_related("game")
            .prefetch_related("player1")
            .prefetch_related("player2")
            .prefetch_related("season")
            .prefetch_related("tournament")
            .order_by("-ran_at")[0:25]
        )


class MatchDetailView(generic.DetailView):
    model = models.Match
    template_name = "matches/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        match = self.get_object()
        time_in_queue = (match.ran_at or timezone.now()) - match.created_at
        context["time_in_queue"] = humanize.precisedelta(time_in_queue)
        return context


class MatchReplayView(generic.DetailView):
    model = models.Match
    template_name = "matches/replay.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match = self.get_object()
        context["replay_js_bundle_url"] = settings.REPLAY_JS_BUNDLE_URL
        context["match_id"] = match.id
        # FIXME: We need to handle failures
        context["match_replay_url"] = utils.get_api_urls_for_pks(
            [match.id],
            "match-replay",
            self.request,
        )[0]
        return context


class TournamentListView(generic.ListView):
    template_name = "tournaments/index.html"
    context_object_name = "tournaments"

    def get_queryset(self):
        return (
            models.Tournament.objects.filter(done=False)
            .prefetch_related("game")
            .prefetch_related("season")
            .order_by("-season__created_at", "game__name", "-created_at")[0:25]
        )


class TournamentDetailView(generic.DetailView):
    model = models.Tournament
    template_name = "tournaments/detail.html"


class UserListView(generic.ListView):
    template_name = "users/index.html"
    context_object_name = "users"

    def get_queryset(self):
        return models.User.objects.order_by("-date_joined")


class UserDetailView(generic.DetailView):
    model = User
    template_name = "users/detail.html"


class UserEditView(generic.UpdateView):
    model = User
    template_name = "users/edit.html"
    form_class = forms.UserForm

    # FIXME: We should redirect to the detail view
    success_url = "/"


class AboutView(generic.TemplateView):
    template_name = "about.html"

    def get_context_data(self, *args, **kwargs):
        context = {}
        context["games_ran_in_the_last_day"] = models.Match.objects.filter(
            ran=True, ran_at__gte=timezone.now() - timedelta(days=1)
        ).count()
        context["games_ran_in_the_last_hour"] = models.Match.objects.filter(
            ran=True, ran_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        context["games_ran_in_the_last_minute"] = models.Match.objects.filter(
            ran=True, ran_at__gte=timezone.now() - timedelta(minutes=1)
        ).count()
        context["n_agents"] = (
            models.Match.objects.filter(
                ran=True, ran_at__gte=timezone.now() - timedelta(days=1)
            )
            .distinct("player1")
            .count()
        )

        return context


def register_request(request):
    if request.method == "POST":
        form = forms.NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect("home")
        messages.error(request, "Unsuccessful registration. Invalid information.")
    form = forms.NewUserForm()
    return render(
        request=request,
        template_name="registration/register.html",
        context={"register_form": form},
    )


class HomeView(generic.TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["matches_1h"] = models.Match.objects.filter(
            ran=True, ran_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        context["matches_24h"] = models.Match.objects.filter(
            ran=True, ran_at__gte=timezone.now() - timedelta(days=1)
        ).count()
        context["active_agent_count"] = (
            models.Match.objects.filter(
                ran=True, ran_at__gte=timezone.now() - timedelta(days=1)
            )
            .distinct("player1")
            .count()
        )
        context["open_tournament_count"] = models.Tournament.objects.filter(
            done=False
        ).count()
        context["current_season_name"] = models.Season.objects.current_season().name
        context["pending_matches"] = models.Match.objects.filter(ran=False).count()

        oldest_pending_match = (
            models.Match.objects.filter(ran=False).order_by("created_at").first()
        )

        context["oldest_pending_match_age"] = "-"
        if oldest_pending_match:
            age = (timezone.now() - oldest_pending_match.created_at).total_seconds()

            if age < constants.ONE_HOUR:
                minimum_unit = "seconds"
            elif age < constants.ONE_DAY:
                minimum_unit = "minutes"
            else:
                minimum_unit = "hours"

            context["oldest_pending_match_age"] = humanize.precisedelta(
                age,
                minimum_unit=minimum_unit,
                format="%0.0f",
            )

        redis = get_redis_connection("default")
        last_heartbeat_bytes = redis.get(settings.CELERY_HEARTBEAT_KEY)
        context["celery_heartbeat"] = "-"
        if last_heartbeat_bytes:
            last_heartbeat = last_heartbeat_bytes.decode()
            last_heartbeat = datetime.fromisoformat(last_heartbeat)
            age = (timezone.now() - last_heartbeat).total_seconds()

            if age < constants.ONE_HOUR:
                minimum_unit = "seconds"
            elif age < constants.ONE_DAY:
                minimum_unit = "minutes"
            else:
                minimum_unit = "hours"

            context["celery_heartbeat"] = (
                humanize.precisedelta(
                    age,
                    minimum_unit=minimum_unit,
                    format="%0.0f",
                )
                + " ago"
            )

        last_heartbeat_bytes = redis.get(settings.COLOSSEUM_HEARTBEAT_KEY)
        context["colosseum_heartbeat"] = "-"
        if last_heartbeat_bytes:
            last_heartbeat = last_heartbeat_bytes.decode()
            last_heartbeat = datetime.fromisoformat(last_heartbeat)
            age = (timezone.now() - last_heartbeat).total_seconds()

            if age < constants.ONE_HOUR:
                minimum_unit = "seconds"
            elif age < constants.ONE_DAY:
                minimum_unit = "minutes"
            else:
                minimum_unit = "hours"

            context["colosseum_heartbeat"] = (
                humanize.precisedelta(
                    age,
                    minimum_unit=minimum_unit,
                    format="%0.0f",
                )
                + " ago"
            )

        return context


# API Views


class PingAPIView(APIView):
    permission_classes = []

    def get(self, _request):
        return Response({"ping": "pong"})


class RedisInfoAPIView(APIView):
    permission_classes = []
    queryset = models.Match.objects.none()

    def get(self, request):
        conn = get_redis_connection("default")
        return Response({"ping": conn.ping(), "info": conn.info()})


class MatchQueueDebugAPIView(APIView):
    permission_classes = []
    queryset = models.Match.objects.none()

    def get(self, request):
        redis = get_redis_connection("default")
        queue_length = redis.llen(settings.MATCH_QUEUE_KEY)
        match_ids = redis.lrange(settings.MATCH_QUEUE_KEY, 0, queue_length)

        return Response({"match_ids": match_ids, "count": len(match_ids)})


class TaintedMatchesDebugAPIView(APIView):
    permission_classes = []
    queryset = models.Match.objects.none()

    def get(self, request):
        tainted_matches_24h = utils.get_api_urls_for_pks(
            models.Match.objects.all()
            .played.tainted.by_ran_at.filter(
                ran_at__gte=timezone.now() - timedelta(days=1)
            )
            .values_list("id", flat=True),
            "match-detail",
            request,
        )

        tainted_matches_1h = utils.get_api_urls_for_pks(
            models.Match.objects.all()
            .played.tainted.by_ran_at.filter(
                ran_at__gte=timezone.now() - timedelta(hours=1)
            )
            .values_list("id", flat=True),
            "match-detail",
            request,
        )

        tainted_matches_15m = utils.get_api_urls_for_pks(
            models.Match.objects.all()
            .played.tainted.by_ran_at.filter(
                ran_at__gte=timezone.now() - timedelta(minutes=15)
            )
            .values_list("id", flat=True),
            "match-detail",
            request,
        )

        return Response(
            {
                "tainted_matches_24h": tainted_matches_24h,
                "tainted_matches_1h": tainted_matches_1h,
                "tainted_matches_15m": tainted_matches_15m,
            }
        )


class NextMatchAPIView(APIView):
    """
    GET returns a next match to be ran. Intended to run multiple tournaments at
    the same time while using a generic worker.

    Current implementation picks a random match from a random tournament to run
    and returns it. In the future this may be improved to better balance
    matches between tournaments.

    Doing a POST to this view checks if there are any tournaments where the
    matches weren't created, and creates new matches accordingly. For timed
    matches this is whenever the pending match count is less or equal to 10,
    otherwise it is when there are no matches for the tournament.
    """

    permission_classes = [permissions.IsAdminUser]
    queryset = models.Match.objects.none()

    def get(self, request):
        metrics.register_get_next_match()

        if match_id := match_queue.get_next():
            return Response({"id": match_id})

        return Response({})

    def post(self, request):
        services.update_tournaments_state()

        return Response()


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUserOrReadOnly]
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer


class AgentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUserOrReadOnly]
    queryset = models.Agent.objects.all()
    serializer_class = serializers.AgentSerializer

    @action(detail=True, methods=["post"])
    def update_hash(self, request, pk=None):
        obj = self.get_object()
        obj.file_hash = utils.hash_file(obj.file)
        obj.save()
        return Response(obj.file_hash, status=status.HTTP_200_OK)


class GameViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUserOrReadOnly]
    queryset = models.Game.objects.all()
    serializer_class = serializers.GameSerializer


class SeasonViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUserOrReadOnly]
    queryset = models.Season.objects.all()
    serializer_class = serializers.SeasonSerializer


class MatchViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUserOrReadOnly]
    queryset = models.Match.objects.all()
    serializer_class = serializers.MatchSerializer

    @action(detail=True, methods=["get"])
    def replay(self, request, pk=None):
        match = self.get_object()
        if not match.ran:
            return Response(status=status.HTTP_404_NOT_FOUND)

        raw_file = requests.get(match.replay.url).content
        decompressed_data = lzma.decompress(raw_file)

        data = [
            json.loads(line)
            for line in decompressed_data.decode("ascii").split("\n")
            if line
        ]

        return Response(data)

    @action(detail=True, methods=["post"])
    def upload_replay(self, request, pk=None):
        match = self.get_object()
        if not match.ran:
            metrics.register_replay_uploaded_for_unplayed_match(match.game.name)
            logger.warning("tryied to upload a match to an unplayed match. Refusing")
            return Response(
                "tryied to upload a match to an unplayed match. Refusing",
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if match.replay:
            metrics.register_replay_being_overwritten(match.game.name)

        file = request.data["file"]
        mime = utils.guess_mime(file)
        replay_file = None

        # A jsonl is a weird format that libmime gets very confused about
        if mime in ("application/json", "application/csv", "text/plain"):
            data_out = lzma.compress(file.read())
            replay_file = ContentFile(data_out)
        elif mime == "application/x-xz":
            replay_file = file
        else:
            logger.warning(
                f"file of type {mime} is invalid. Must be json or xz. Not processing"
            )
            return Response(
                f"file of type {mime} is invalid. Must be json or xz",
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        match.replay.save("replay.jsonl.xz", replay_file)
        match.save()

        metrics.register_replay(match.game.name)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def count(self, request):
        params = request.GET

        filter = {"ran": True}

        if params.get("current_season"):
            current_season = models.Season.objects.current_season()
            filter["season"] = current_season

        if hours_ago := params.get("hours_ago"):
            filter["ran_at__gte"] = timezone.now() - timedelta(hours=int(hours_ago))

        count = models.Match.objects.filter(**filter).count()

        return Response(count)


class TournamentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUserOrReadOnly]
    queryset = models.Tournament.objects.all()
    serializer_class = serializers.TournamentSerializer

    @action(detail=False, methods=["post"])
    def create_automated_tournaments(self, request):
        from .services.automated_tournaments import create_automated_tournaments

        create_automated_tournaments()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AutomatedSeasonsAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = models.Season.objects.none()

    def post(self, request):
        services.update_seasons_state()
        services.create_automated_seasons()
        return Response()


class ColosseumHeartbeatAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = models.Season.objects.none()

    def post(self, request):
        redis = get_redis_connection("default")
        heartbeat_key = settings.COLOSSEUM_HEARTBEAT_KEY
        redis.set(heartbeat_key, timezone.now().isoformat())
        return Response()


# Plots


# We cache one second off the plot update interval to ensure that it won't
# (possibly) have persistent artefacts near the boundaries that are updated
# on the minute.
@cache_page(constants.ONE_MINUTE - 1)
def plot_matches_per_day(request):
    return plots.plot_matches_per_day()


@cache_page(constants.ONE_MINUTE)
def plot_agent_elo(request, pk):
    agent = models.Agent.objects.get(id=pk)
    return plots.plot_agent_elo(agent)
