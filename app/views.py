import json
import logging
import lzma
from collections import defaultdict
from datetime import timedelta

import humanize
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
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
        context["games"] = models.Game.objects.active().with_agents().order_by("name")
        return context

    def get_queryset(self):
        return (
            models.Agent.objects.all()
            .annotate(
                elo_rating=F("ratings__elo"),
                owner_username=F("owner__username"),
            )
            .filter(active=True)
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["base_url"] = self.request.build_absolute_uri("/")
        return context

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["base_url"] = self.request.build_absolute_uri("/")
        return context

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
        context["context_object_name"] = "seasons"
        return context

    def get_queryset(self):
        season_list = models.Season.objects.all().order_by("-end_date")
        season_page_number = utils.validate_page_number(
            self.request.GET.get("page"), len(season_list), 25
        )

        return Paginator(season_list, 25).page(season_page_number)


class SeasonDetailView(generic.DetailView):
    model = models.Season
    template_name = "seasons/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        season = self.get_object()
        context["tournaments"] = season.tournaments.order_by("-end_date")[:25]
        trophies = services.trophy.trophies_for_season(season)

        trophies_by_game = defaultdict(list)
        for trophy in trophies:
            game = str(trophy.agent.game_id)
            trophies_by_game[game].append(trophy)

        context["game_name_by_id"] = {
            str(game.id): game.pretty_name for game in season.games
        }
        context["trophies_by_game"] = dict(trophies_by_game)
        context["agent_elo"] = {
            rating.agent_id: rating.elo for rating in season.ratings.order_by("-elo")
        }

        return context


class SeasonWinnersView(generic.DetailView):
    model = models.Season
    template_name = "seasons/winners.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        season = self.get_object()
        context["ratings"] = season.ratings.all().order_by("-elo")
        context["ranking"] = {}

        owner_list = set(
            models.User.objects.filter(is_superuser=True).values_list("id", flat=True)
        )

        ranking = 1
        for rating in context["ratings"]:
            if rating.agent.owner.id not in owner_list:
                context["ranking"][rating.agent_id] = ranking
                owner_list.add(rating.agent.owner.id)
                ranking += 1
            else:
                context["ranking"][rating.agent_id] = ""

        return context


class MatchListView(generic.ListView):
    template_name = "matches/index.html"
    context_object_name = "matches"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["context_object_name"] = "matches"
        return context

    def get_queryset(self):
        match_list = (
            models.Match.objects.filter(ran=True)
            .prefetch_related("game")
            .prefetch_related("player1")
            .prefetch_related("player2")
            .prefetch_related("season")
            .prefetch_related("tournament")
            .order_by("-ran_at")
        )[:25]

        # FIXME: This times out, probably because of something dumb at the
        # database. Git blame this message for the old code.

        return match_list


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["context_object_name"] = "tournaments"
        return context

    def get_queryset(self):
        tournament_list = (
            models.Tournament.objects.filter(done=False)
            .prefetch_related("game")
            .prefetch_related("season")
            .order_by("-season__created_at", "game__name", "-created_at")[0:25]
        )

        tournament_page_number = utils.validate_page_number(
            self.request.GET.get("page"), len(tournament_list), 25
        )

        return Paginator(tournament_list, 25).page(tournament_page_number)


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
        context={
            "register_form": form,
            "base_url": request.build_absolute_uri("/"),
        },
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

        try:
            context["current_season_name"] = models.Season.objects.current_season().name
        except Exception:
            context["current_season_name"] = "-"

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

        context["celery_heartbeat"] = "-"
        time_since_last_celery_heartbeat = (
            services.get_time_since_last_celery_heartbeat()
        )
        if time_since_last_celery_heartbeat is not None:
            context["celery_heartbeat"] = (
                services.prettify_time_delta(time_since_last_celery_heartbeat) + " ago"
            )

        context["colosseum_heartbeat"] = "-"
        time_since_last_colosseum_heartbeat = (
            services.get_time_since_last_colosseum_heartbeat()
        )
        if time_since_last_colosseum_heartbeat is not None:
            context["colosseum_heartbeat"] = (
                services.prettify_time_delta(time_since_last_colosseum_heartbeat)
                + " ago"
            )

        return context


# Debug Views


class DebugListView(generic.TemplateView):
    template_name = "debug/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["context_object_name"] = "debug"
        context["endpoint_list"] = [
            {"name": "Match Queue", "url": "match_queue_debug_view"},
            {"name": "Tainted Matches", "url": "tainted_matches_debug"},
            {"name": "Redis Info", "url": "redis_info"},
            {"name": "Ping", "url": "ping"},
        ]

        return context


class MatchQueueDebugDetailView(generic.TemplateView):
    template_name = "debug/match_queue.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["context_object_name"] = "match_queue"
        context["title"] = "Match Queue Debug Api"
        context["matches"] = []

        redis = get_redis_connection("default")
        queue_length = redis.llen(settings.MATCH_QUEUE_KEY)
        match_ids = redis.lrange(settings.MATCH_QUEUE_KEY, 0, queue_length)

        for match_id in match_ids:
            match_id = match_id.decode("utf-8")

            try:
                match = models.Match.objects.get(id=match_id)
                context["matches"].append(match)
            except ObjectDoesNotExist:
                # TODO: We should find a way to handle this not silently
                pass

        context["count"] = len(match_ids)

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

        params = request.query_params
        game_name = params.get("game")

        if match_id := match_queue.get_next(game_name=game_name):
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
    unauth_serializer_class = serializers.AgentNoAuthSerializer

    def get_serializer_class(self, *args, **kwargs):
        if self.request.user and (
            self.request.user.is_staff or self.request.user.is_superuser
        ):
            return self.serializer_class
        return self.unauth_serializer_class

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
        services.automated_seasons.update_seasons_state()
        services.automated_seasons.create_automated_seasons()
        return Response()


class ColosseumHeartbeatAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = models.Season.objects.none()

    def post(self, request):
        redis = get_redis_connection("default")
        heartbeat_key = settings.COLOSSEUM_HEARTBEAT_KEY
        redis.set(heartbeat_key, timezone.now().isoformat())
        return Response()


class MetricsAPIView(APIView):
    """
    Endpoint to push metrics. While this means that if the api goes down, so
    goes any metrics going through here, it also simplify infra and worker
    architecture a lot.

    Payload example:
    {
        "fields": {"value": 123},
        "measurement": "foo_bar",
        "time": "2022-07-12T00:04:56.147601+00:00"  # e.g. timezone.now().isoformat(),
    }
    """

    permission_classes = [permissions.IsAdminUser]
    queryset = models.Season.objects.none()

    def post(self, request):
        services.metrics_api_handler(request.data)
        return Response(status=status.HTTP_201_CREATED)


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


@cache_page(constants.ONE_MINUTE)
def plot_game_season_elo(request, game_pk, season_pk):
    game = models.Game.objects.get(id=game_pk)
    season = models.Season.objects.get(id=season_pk)
    return plots.plot_game_season_elo(game, season)
