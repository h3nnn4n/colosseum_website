from django.contrib.auth.models import User
from django.urls import include, path
from rest_framework import routers, serializers, viewsets

from app import models


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Agent
        fields = [
            "id",
            "name",
            "file",
            "score",
            "wins",
            "loses",
            "draws",
            "elo",
            "owner",
            "games_played",
            "created_at",
            "updated_at",
        ]


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Game
        fields = ["id", "name", "created_at", "updated_at"]


class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Match
        fields = [
            "id",
            "participants",
            "player1",
            "player2",
            "result",
            "data",
            "ran",
            "ran_at",
            "created_at",
            "updated_at",
        ]


class TournamentSerializer(serializers.ModelSerializer):
    started_at = serializers.DateTimeField(required=False)
    finished_at = serializers.DateTimeField(required=False)

    class Meta:
        model = models.Tournament
        fields = [
            "id",
            "name",
            "game",
            "participants",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        participants = validated_data.pop("participants")
        tournament = models.Tournament.objects.create(**validated_data)

        tournament.participants.add(*participants)
        tournament.save()

        return tournament
