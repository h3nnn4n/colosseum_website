from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time

from app import factories, models, services
from app.services import ratings


class RatingsServiceTestCase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.season = factories.SeasonFactory()
        self.agent1 = factories.AgentFactory()
        self.agent2 = factories.AgentFactory()

    def test_update(self):
        self.assertEqual(self.agent1.elo, 1500)
        self.assertEqual(self.agent2.elo, 1500)

        ratings.update_record_ratings(self.agent1.id, self.agent2.id, 1)

        self.assertEqual(self.agent1.elo, Decimal("1512"))
        self.assertEqual(self.agent2.elo, Decimal("1488"))

        ratings.update_record_ratings(self.agent1.id, self.agent2.id, 0)

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
