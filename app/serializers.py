from django.contrib.auth.models import User
from django.urls import include, path
from rest_framework import routers, serializers, viewsets

from app import models


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class AgentRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Agent
        fields = [
            "id",
            "agent",
            "wins",
            "loses",
            "draws",
            "elo",
            "created_at",
            "updated_at",
        ]


class AgentSerializer(serializers.ModelSerializer):
    ratings = AgentRatingSerializer(read_only=True)

    class Meta:
        model = models.Agent
        fields = ["id", "name", "file", "ratings", "owner", "created_at", "updated_at"]


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Game
        fields = ["id", "name", "created_at", "updated_at"]


class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Match
        fields = [
            "id",
            "name",
            "participants",
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
