import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import include, path
from django.utils import timezone
from rest_framework import exceptions, routers, serializers, viewsets

from app import metrics, models

from .services.ratings import (
    update_elo_change_after,
    update_elo_change_before,
    update_ratings,
    update_record_ratings,
)


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("APP")


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
            "game",
            "file",
            "file_hash",
            "score",
            "wins",
            "loses",
            "draws",
            "elo",
            "owner",
            "games_played_count",
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
            "game",
            "errors",
            "data",
            "ran",
            "ran_at",
            "replay",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        if data.get("ran") and not data.get("ran_at"):
            data["ran_at"] = timezone.now()

        return data

    # FIXME: We need to properly validate that we only have 2 participants
    def create(self, validated_data):
        participants = validated_data["participants"]
        validated_data["player1"] = participants[0]
        validated_data["player2"] = participants[1]

        if len(participants) != 2:
            raise exceptions.ValidationError(
                f"Only matches with 2 participants are supported at this point. received {len(participants)}"
            )

        instance = super(MatchSerializer, self).create(validated_data)

        update_elo_change_before(instance)
        update_record_ratings(instance.player1.id, instance.player2.id, instance.result)
        update_elo_change_after(instance)
        instance.save()

        return instance

    def update(self, instance, validated_data):
        # Never change a match result
        if not instance.ran:
            super(MatchSerializer, self).update(instance, validated_data)

        # If it ran but data is empty, we need to update the player ratings
        if instance.ran and not instance.data:
            update_elo_change_before(instance)
            update_record_ratings(
                instance.player1.id, instance.player2.id, instance.result
            )
            update_elo_change_after(instance)
            instance.save()
            metrics.register_match_played()

        return instance


class TournamentSerializer(serializers.ModelSerializer):
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    participants = serializers.PrimaryKeyRelatedField(
        queryset=models.Agent.objects.all(), many=True, required=False
    )

    class Meta:
        model = models.Tournament
        fields = [
            "id",
            "name",
            "game",
            "mode",
            "is_automated",
            "automated_number",
            "participants",
            "start_date",
            "end_date",
            "done",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        if not data.get("participants"):
            logger.info(
                "tournament is being created with no participants, defaulting to all"
            )
            data["participants"] = list(
                models.Agent.objects.all().values_list("id", flat=True)
            )

        return data

    def create(self, validated_data):
        participants = validated_data.pop("participants")

        tournament = models.Tournament.objects.create(**validated_data)
        tournament.participants.add(*participants)
        tournament.save()
        tournament.create_matches()

        return tournament
