import logging
from uuid import UUID

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from rest_framework import exceptions, serializers

from app import metrics, models

from .services.ratings import update_ratings_from_match


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("APP")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Game
        fields = [
            "id",
            "name",
            "short_description",
            "description",
            "created_at",
            "updated_at",
        ]


class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Season
        fields = [
            "id",
            "name",
            "is_automated",
            "automated_number",
            "start_date",
            "end_date",
            "created_at",
            "updated_at",
        ]


class AgentNoAuthSerializer(serializers.ModelSerializer):
    game = GameSerializer(read_only=True)

    class Meta:
        model = models.Agent
        fields = [
            "id",
            "name",
            "game",
            "file_hash",
            "owner",
            "games_played_count",
            "created_at",
            "updated_at",
        ]


class AgentSerializer(serializers.ModelSerializer):
    game = GameSerializer(read_only=True)

    class Meta:
        model = models.Agent
        fields = [
            "id",
            "name",
            "game",
            "file",
            "file_hash",
            "owner",
            "games_played_count",
            "created_at",
            "updated_at",
        ]


class MatchSerializer(serializers.ModelSerializer):
    game = GameSerializer(read_only=True)

    class Meta:
        model = models.Match
        fields = [
            "id",
            "participants",
            "player1",
            "player2",
            "result",
            "game",
            "outcome",
            "raw_result",
            "end_reason",
            "data",
            "outcome",
            "end_reason",
            "ran",
            "ran_at",
            "duration",
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

        update_ratings_from_match(instance)
        instance.save()

        return instance

    def update(self, instance, validated_data):
        if (
            validated_data.get("ran_at")
            and instance.ran_at
            and instance.ran_at != validated_data["ran_at"]
        ):
            metrics.register_match_played_twice(instance.game.name)

        # Never change a match result
        if not instance.ran:
            super(MatchSerializer, self).update(instance, validated_data)

        # If it ran but data is empty, we need to update the player ratings
        if instance.ran and not instance.data:
            with transaction.atomic():
                update_ratings_from_match(instance)
                instance.save()

            metrics.register_match_played(instance.game.name)
            metrics.register_match_duration(instance)
            metrics.register_match_queue_time(instance)

            if instance.tainted:
                metrics.register_tainted_match(instance)

        return instance


class TournamentSerializer(serializers.ModelSerializer):
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    participants = serializers.PrimaryKeyRelatedField(
        queryset=models.Agent.objects.all(), many=True, required=False
    )
    game = GameSerializer(read_only=True)
    game_id = serializers.CharField(max_length=255, write_only=True)
    season_id = serializers.CharField(max_length=255, write_only=True, required=False)

    class Meta:
        model = models.Tournament
        fields = [
            "id",
            "name",
            "game",
            "game_id",
            "season_id",
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

    def validate_participants(self, data):
        game_id = self.initial_data["game_id"]
        for agent in data:
            if agent.game_id != UUID(game_id):
                raise exceptions.ValidationError(
                    f"participant {agent.id} game {agent.game_id} doesn't match tournament game {game_id}"
                )

        return data

    def validate_season_id(self, value):
        if not models.Season.objects.get(id=value):
            raise exceptions.ValidationError(f"season with id {value} does not exist")

        return value

    def validate(self, data):
        if not data.get("participants"):
            logger.info(
                "tournament is being created with no participants, defaulting to all"
            )
            game_id = data["game_id"]
            data["participants"] = list(
                models.Agent.objects.filter(game_id=game_id, active=True).values_list(
                    "id", flat=True
                )
            )

        if not data.get("season_id"):
            season = models.Season.objects.get(active=True, main=True)
            data["season_id"] = str(season.id)

        return data

    def create(self, validated_data):
        participants = validated_data.pop("participants")

        tournament = models.Tournament.objects.create(**validated_data)
        tournament.participants.add(*participants)
        tournament.save()
        tournament.create_matches()

        return tournament
