import logging
import lzma
from datetime import timedelta

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
            .annotate(elo_rating=F("ratings__elo"))
            .filter(ratings__season__active=True, ratings__season__main=True)
            .order_by("-elo_rating")
        )


class AgentDetailView(generic.DetailView):
    model = models.Agent
    template_name = "agents/detail.html"


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


def index(request):
    return render(request, "home.html")


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
        redis = get_redis_connection("default")
        if redis.get("disable_next_match_api") == b"1":
            return Response({"_state": "killswitch engaged"})

        while True:
            match_id = redis.spop(settings.MATCH_QUEUE_KEY)

            # Queue is empty. Nothing to do
            if not match_id:
                break

            match_id = match_id.decode()

            if models.Match.objects.filter(id=match_id, ran=False).exists():
                return Response({"id": match_id})

        return Response({})

    def post(self, request):
        tournaments = models.Tournament.objects.filter(done=False)

        for tournament in tournaments:
            services.update_tournament_state(tournament)

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

    @action(detail=True, methods=["post"])
    def upload_replay(self, request, pk=None):
        match = self.get_object()
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
            logger.warn(
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


# Plots


# We cache one second off the plot update interval to ensure that it won't
# (possibly) have persistent artefacts near the boundaries that are updated
# on the minute.
@cache_page(constants.ONE_MINUTE - 1)
def plot_matches_per_day(request):
    return plots.plot_matches_per_day()


@cache_page(constants.TEN_MINUTES)
def plot_agent_elo(request, pk):
    agent = models.Agent.objects.get(id=pk)
    return plots.plot_agent_elo(agent)
