from decimal import Decimal

from django.test import TestCase
from freezegun import freeze_time

from app import factories, models, services
from app.services import ratings


class RatingsServiceTestCase(TestCase):
    def setUp(self):
        models.Season.objects.all().delete()

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

    def test_update(self):
        self.assertEqual(self.agent1.elo, 1500)
        self.assertEqual(self.agent2.elo, 1500)

        ratings.update_ratings_from_match(self.match1)

        self.assertEqual(self.agent1.elo, Decimal("1512"))
        self.assertEqual(self.agent2.elo, Decimal("1488"))

        ratings.update_ratings_from_match(self.match2)

        self.assertEqual(self.agent1.elo, Decimal("1499"))
        self.assertEqual(self.agent2.elo, Decimal("1501"))


class UpdateSeasonStatesTestCase(TestCase):
    def test_update(self):
        with freeze_time("2021-05-14"):
            self.assertEqual(models.Season.objects.filter(active=True).count(), 0)

            services.create_automated_seasons()

            self.assertEqual(models.Season.objects.filter(active=True).count(), 1)

            services.update_seasons_state()

            self.assertEqual(models.Season.objects.filter(active=True).count(), 1)

        with freeze_time("2021-05-15"):
            self.assertEqual(models.Season.objects.filter(active=True).count(), 1)

            services.update_seasons_state()

            self.assertEqual(models.Season.objects.filter(active=True).count(), 0)


class CreateAutomatedSeasonsTestCase(TestCase):
    def test_create_first_season(self):
        self.assertEqual(models.Season.objects.count(), 0)
        services.create_automated_seasons()
        self.assertEqual(models.Season.objects.count(), 1)

    def test_dont_create_new_season_if_there_is_an_active_one(self):
        self.assertEqual(models.Season.objects.count(), 0)
        services.create_automated_seasons()
        self.assertEqual(models.Season.objects.count(), 1)
        services.create_automated_seasons()
        self.assertEqual(models.Season.objects.count(), 1)

    def test_create_new_season_if_there_isnt_an_active_one(self):
        with freeze_time("2021-05-14"):
            self.assertEqual(models.Season.objects.count(), 0)
            services.create_automated_seasons()
            self.assertEqual(models.Season.objects.count(), 1)
            services.create_automated_seasons()
            self.assertEqual(models.Season.objects.count(), 1)

        with freeze_time("2021-05-15"):
            services.update_seasons_state()

            services.create_automated_seasons()
            self.assertEqual(models.Season.objects.count(), 2)
