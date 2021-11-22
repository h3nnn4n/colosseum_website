import json
import logging
from random import choice

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import include, path
from django.views import generic
from django.views.generic.edit import FormView
from rest_framework import routers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from app import models, serializers

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
    fields = ["name", "file"]
    success_url = "/agents/"


class MatchListView(generic.ListView):
    template_name = "matches/index.html"
    context_object_name = "matches"

    def get_queryset(self):
        return models.Match.objects.filter(ran=True).order_by("-ran_at")[0:25]


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
        tournaments = [t for t in models.Tournament.objects.all() if t.is_active]
        tournament = choice(tournaments)
        logger.info(
            f"Selected tournament {tournament.id} {tournament.name} {tournament.mode} from {len(tournaments)} tournaments"
        )

        response = {}
        if tournament.mode == "TIMED" and tournament.pending_matches <= 10:
            logger.info(
                f"TIMED Tournament {tournament.id} has a low number of matches left: {tournament.pending_matches}"
            )
            tournament.create_matches()

        # In case something goes wrong and no matches were created we return
        # nothing and let the consumer handle it (possibly with a retry)
        if not tournament.matches.exists():
            return Response({})

        match_id = choice(list(tournament.matches.all().values_list("id", flat=True)))
        response["id"] = match_id

        return Response(response)


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


class TournamentViewSet(viewsets.ModelViewSet):
    queryset = models.Tournament.objects.all()
    serializer_class = serializers.TournamentSerializer

    def perform_create(self, serializer):
        return serializer.save()

    # FIXME: This should be in the serializer
    def create(self, request, *args, **kwargs):
        if not request.data.get("participants"):
            # TODO: We should probably filter by only active agents or something
            participant_ids = list(
                models.Agent.objects.all().values_list("id", flat=True)
            )
            logger.info(
                "tournament is being created with no participants, defaulting to all"
            )
            request.data["participants"] = participant_ids

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tournament = self.perform_create(serializer)
        tournament.create_matches()

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )
