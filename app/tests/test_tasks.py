from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from app import factories, models, tasks


class RefreshAgentCountCacheTestCase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.season = factories.SeasonFactory()
        self.tournament = factories.TournamentFactory(
            game=self.game, season=self.season
        )
        self.agent1 = factories.AgentFactory(game=self.game)
        self.agent2 = factories.AgentFactory(game=self.game)
        self.match1 = factories.MatchFactory(
            player1=self.agent1,
            player2=self.agent2,
            season=self.season,
            tournament=self.tournament,
            game=self.game,
            result=1,
        )
        self.match2 = factories.MatchFactory(
            player1=self.agent1,
            player2=self.agent2,
            season=self.season,
            tournament=self.tournament,
            game=self.game,
            result=0,
        )

    def test_for_smoke(self):
        """
        Basic smoke test, so we don't have any bad surprises
        """
        tasks.refresh_agent_count_cache()


class AutomatedManagerTestcase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.season = factories.SeasonFactory(
            end_date=timezone.now() - timedelta(hours=1)
        )
        self.tournament = factories.TournamentFactory(
            game=self.game, season=self.season
        )
        self.agent1 = factories.AgentFactory(game=self.game)
        self.agent2 = factories.AgentFactory(game=self.game)

    def test_updates_season(self):
        self.assertTrue(self.season.active)
        tasks.automated_manager()
        self.season.refresh_from_db()
        self.assertFalse(self.season.active)

    def test_creates_new_season(self):
        self.assertEqual(models.Season.objects.count(), 1)
        tasks.automated_manager()
        self.assertEqual(models.Season.objects.count(), 2)

        self.assertIsNotNone(models.Season.objects.current_season())

    def test_creates_automated_tournaments(self):
        self.assertEqual(models.Tournament.objects.count(), 1)
        tasks.automated_manager()
        self.assertEqual(models.Tournament.objects.count(), 5)

    def test_creates_matches(self):
        self.assertEqual(models.Match.objects.filter(ran=False).count(), 0)
        tasks.automated_manager()
        self.assertEqual(models.Match.objects.filter(ran=False).count(), 8)


class MetricsLoggerTestCase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.season = factories.SeasonFactory(
            end_date=timezone.now() - timedelta(hours=1)
        )
        self.tournament = factories.TournamentFactory(
            game=self.game, season=self.season
        )
        self.agent1 = factories.AgentFactory(game=self.game)
        self.agent2 = factories.AgentFactory(game=self.game)

    def test_smoke(self):
        tasks.metrics_logger()
        tasks.automated_manager()  # This creates some data
        tasks.metrics_logger()
