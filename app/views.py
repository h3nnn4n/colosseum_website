from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import include, path
from rest_framework import routers, viewsets

from app import models, serializers

from .forms import NewUserForm


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
    context = {}
    return render(request, "home.html", context)


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


class TournamentViewSet(viewsets.ModelViewSet):
    queryset = models.Tournament.objects.all()
    serializer_class = serializers.TournamentSerializer
