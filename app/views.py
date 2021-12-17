import json
import logging
import lzma
from datetime import timedelta
from random import choice

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import include, path
from django.utils import timezone
from django.views import generic
from django.views.generic.edit import FormView
from rest_framework import routers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from app import forms, models, permissions, serializers, utils

from . import plots
from .services.ratings import (
    update_elo_change_after,
    update_elo_change_before,
    update_ratings,
    update_record_ratings,
)


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("APP")


class AgentListView(generic.ListView):
    template_name = "agents/index.html"
    context_object_name = "agents"

    def get_queryset(self):
        return models.Agent.objects.order_by("-elo")


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
        return models.Match.objects.filter(ran=True).order_by("-ran_at")[0:25]


class TournamentListView(generic.ListView):
    template_name = "tournaments/index.html"
    context_object_name = "tournaments"

    def get_queryset(self):
        return models.Tournament.objects.order_by("-created_at")[0:25]


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


class RedisInfoAPIView(APIView):
    permission_classes = []
    queryset = models.Match.objects.none()

    def get(self, request):
        from django_redis import get_redis_connection

        con = get_redis_connection("default")
        data = con.ping()
        return Response({"foo": data})


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
        match_ids = models.Match.objects.filter(ran=False).values_list("id", flat=True)
        if not match_ids:
            return Response({})

        match_id = choice(list(match_ids))

        return Response({"id": match_id})

    def post(self, request):
        # FIXME: This won't work for very long, specially on a high traffic and
        # mission critical endpoint like this one.
        tournaments = models.Tournament.objects.filter(done=False)

        for tournament in tournaments:
            if (
                tournament.mode == "TIMED"
                and tournament.is_active
                and tournament.pending_matches <= 10
            ):
                logger.info(
                    f"TIMED Tournament {tournament.id} has a low number of matches left: {tournament.pending_matches}"
                )
                tournament.create_matches()
            elif tournament.matches.count() == 0:
                logger.info(
                    f"{tournament.mode} Tournament {tournament.id} is missing matches. Creating"
                )
                tournament.create_matches()

            if not tournament.is_active:
                tournament.done = True
                tournament.save(update_fields=["done"])
                logger.info(
                    f"{tournament.mode} Tournament {tournament.id} was set to done=true"
                )

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


class MatchViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUserOrReadOnly]
    queryset = models.Match.objects.all()
    serializer_class = serializers.MatchSerializer

    @action(detail=True, methods=["post"])
    def upload_replay(self, request, pk=None):
        match = self.get_object()
        file = request.data["file"]
        data_out = lzma.compress(file.read())
        match.replay.save("replay.jsonl.xz", ContentFile(data_out))
        match.save()
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


# Plots


def plot_matches_per_day(request):
    return plots.matches_per_day()


def plot_agent_elo(request, pk):
    agent = models.Agent.objects.get(id=pk)
    return plots.agent_elo_plot(agent)
