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

from app import models, serializers

from . import plots
from .forms import NewAgentForm, NewUserForm
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


class AgentUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = models.Agent
    template_name = "agents/edit.html"
    fields = ["name", "active", "file"]
    success_url = "/agents/"


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
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect("home")
        messages.error(request, "Unsuccessful registration. Invalid information.")
    form = NewUserForm()
    return render(
        request=request,
        template_name="registration/register.html",
        context={"register_form": form},
    )


def index(request):
    return render(request, "home.html")


def wip(request):
    return render(request, "wip.html")


# FIXME: This is obviously temporary
@login_required()
def upload(request):
    if request.method == "POST":
        form = NewAgentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("/agent/upload_success/")
    else:
        form = NewAgentForm()
    return render(request, "new_agent.html", {"form": form})


def upload_success(request):
    return render(request, "new_agent_success.html", {})


# API Views


class NextMatchAPIView(APIView):
    """
    Returns a next match to be ran. Intended to run multiple tournaments at the
    same time while using a generic worker.

    Current implementation picks a random match from a random tournament to run
    and returns it. In the future this may be improved to better balance
    matches between tournaments.
    """

    def get(self, request):
        # FIXME: This wont work for very long, specially on a high traffic and
        # mission critical endpoint like this one.
        tournaments = models.Tournament.objects.all()

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

        match_ids = models.Match.objects.filter(ran=False).values_list("id", flat=True)
        if not match_ids:
            return Response({})

        match_id = choice(list(match_ids))

        return Response({"id": match_id})


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer


class AgentViewSet(viewsets.ModelViewSet):
    queryset = models.Agent.objects.all()
    serializer_class = serializers.AgentSerializer


class GameViewSet(viewsets.ModelViewSet):
    queryset = models.Game.objects.all()
    serializer_class = serializers.GameSerializer


class MatchViewSet(viewsets.ModelViewSet):
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
