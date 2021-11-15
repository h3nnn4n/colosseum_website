from django.contrib.auth.models import User
from django.urls import include, path
from rest_framework import routers, serializers, viewsets

from app import models


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username"]


class AgentSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Agent
        fields = ["name", "owner", "created_at", "updated_at"]


class GameSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Game
        fields = ["name", "created_at", "updated_at"]


class MatchSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Match
        fields = ["name", "participants", "ran", "ran_at", "created_at", "updated_at"]


class TournamentSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Tournament
        fields = [
            "name",
            "game",
            "participants",
            "matches",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]
