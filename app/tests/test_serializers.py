from django.test import TestCase

from app import factories, serializers


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

    def test_tournament_dont_include_inactive_agents(self):
        agent_active1 = factories.AgentFactory(game=self.game)
        agent_active2 = factories.AgentFactory(game=self.game)
        agent_inactive = factories.AgentFactory(game=self.game, active=False)

        serializer = self.serializer(
            data={
                "name": "test inactive agents",
                "game_id": str(self.game.id),
                "mode": "ROUND_ROBIN",
                "season_id": str(self.season.id),
            }
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        self.assertEqual(2, instance.participants.count())
        self.assertIn(
            agent_active1.id, (instance.participants.values_list("id", flat=True))
        )
        self.assertIn(
            agent_active2.id, (instance.participants.values_list("id", flat=True))
        )
        self.assertNotIn(
            agent_inactive.id, (instance.participants.values_list("id", flat=True))
        )


class SeasonSerializerTestCase(TestCase):
    def setUp(self):
        self.serializer = serializers.SeasonSerializer

    def test_create(self):
        serializer = self.serializer(data={"name": "foo"})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        self.assertIsNotNone(instance)
