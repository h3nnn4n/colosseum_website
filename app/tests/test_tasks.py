from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from app import factories, models, tasks


class AutomatedManagerTestcase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.season = factories.SeasonFactory(
            start_date=timezone.now() - timedelta(hours=2),
            end_date=timezone.now() - timedelta(hours=1),
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
        self.assertEqual(models.Tournament.objects.count(), 4)

    def test_creates_matches(self):
        self.assertEqual(models.Match.objects.filter(ran=False).count(), 0)
        tasks.automated_manager()
        self.assertEqual(models.Match.objects.filter(ran=False).count(), 6)


class MetricsLoggerTestCase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.season = factories.SeasonFactory(
            start_date=timezone.now() - timedelta(hours=2),
            end_date=timezone.now() - timedelta(hours=1),
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
