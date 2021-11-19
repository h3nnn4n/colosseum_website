import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import include, path
from rest_framework import routers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from app import models, serializers

from .forms import NewAgentForm, NewUserForm
from .services.ratings import update_ratings, update_record_ratings


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("APP")


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
    agents = models.Agent.objects.filter(owner=request.user)
    context = {"agents": agents}
    return render(request, "home.html", context)


# FIXME: This is obviously temporary
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

    def create(self, request, *args, **kwargs):
        data = request.data

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if len(data["participants"]) != 2:
            return Response(
                dict(error="Only 2 participants are supported at this moment"),
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        self.perform_create(serializer)

        update_record_ratings(
            data["participants"][0], data["participants"][1], data["result"]
        )

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class TournamentViewSet(viewsets.ModelViewSet):
    queryset = models.Tournament.objects.all()
    serializer_class = serializers.TournamentSerializer
