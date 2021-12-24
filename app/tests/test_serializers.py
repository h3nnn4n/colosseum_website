from django.test import TestCase
from django.utils import timezone

from app import factories, models, serializers


class TournamentSerializerTestCase(TestCase):
    def setUp(self):
        self.serializer = serializers.TournamentSerializer
        self.game = factories.GameFactory()
        self.season = factories.SeasonFactory()

    def test_create_tournament_with_season(self):
        serializer = self.serializer(
            data={
                "name": "test 1",
                "game_id": str(self.game.id),
                "mode": "ROUND_ROBIN",
                "season_id": str(self.season.id),
            }
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        self.assertIsNotNone(instance)

    def test_create_tournament_without_season(self):
        serializer = self.serializer(
            data={"name": "test 1", "game_id": str(self.game.id), "mode": "ROUND_ROBIN"}
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        self.assertIsNotNone(instance)
