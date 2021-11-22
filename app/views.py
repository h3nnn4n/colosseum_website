import json
import logging

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
        return models.Match.objects.order_by("-created_at")[0:25]


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

    def perform_create(self, serializer):
        return serializer.save()

    def create(self, request, *args, **kwargs):
        data = dict(request.data)
        participants = data["participants"]
        data["player1"] = participants[0]
        data["player2"] = participants[1]
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        if len(participants) != 2:
            logging.info(
                f"dropped match because it didnt have 2 participants! It had {len(participants)} {participants}. payload: {data}"
            )
            return Response(
                dict(error="Only 2 participants are supported at this moment"),
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        match = self.perform_create(serializer)

        # HACK: Tbh I have no idea why or how this is happening, but this fixes it
        result = data["result"]
        if isinstance(result, (list, tuple)):
            result = float(result[0])

        update_elo_change_before(match)
        update_record_ratings(data["participants"][0], data["participants"][1], result)
        update_elo_change_after(match)
        match.save()

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class TournamentViewSet(viewsets.ModelViewSet):
    queryset = models.Tournament.objects.all()
    serializer_class = serializers.TournamentSerializer

    def perform_create(self, serializer):
        return serializer.save()

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
