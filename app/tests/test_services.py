from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from freezegun import freeze_time

from app import factories, models, services
from app.services import (
    automated_seasons,
    automated_tournaments,
    match_queue,
    ratings,
    trophy,
)


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

        self.agent1 = models.Agent.objects.get(id=self.agent1.id)
        self.agent2 = models.Agent.objects.get(id=self.agent2.id)

        self.assertEqual(self.agent1.elo, Decimal("1512"))
        self.assertEqual(self.agent2.elo, Decimal("1488"))

        self.match2 = models.Match.objects.get(id=self.match2.id)
        ratings.update_ratings_from_match(self.match2)

        self.agent1 = models.Agent.objects.get(id=self.agent1.id)
        self.agent2 = models.Agent.objects.get(id=self.agent2.id)

        self.assertEqual(self.agent1.elo, Decimal("1499"))
        self.assertEqual(self.agent2.elo, Decimal("1501"))


class UpdateSeasonStatesTestCase(TestCase):
    def test_update(self):
        with freeze_time("2021-05-01"):
            self.assertEqual(models.Season.objects.filter(active=True).count(), 0)

            automated_seasons.create_automated_seasons()

            self.assertEqual(models.Season.objects.filter(active=True).count(), 1)

            automated_seasons.update_seasons_state()

            self.assertEqual(models.Season.objects.filter(active=True).count(), 1)

        with freeze_time("2021-06-01"):
            self.assertEqual(models.Season.objects.filter(active=True).count(), 1)

            automated_seasons.update_seasons_state()

            self.assertEqual(models.Season.objects.filter(active=True).count(), 0)


class CreateAutomatedSeasonsTestCase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        factories.AgentFactory(game=self.game)
        factories.AgentFactory(game=self.game)
        factories.AgentFactory(game=self.game)
        factories.AgentFactory(game=self.game)

    def test_create_first_season(self):
        self.assertEqual(models.Season.objects.count(), 0)
        automated_seasons.create_automated_seasons()
        self.assertEqual(models.Season.objects.count(), 1)

    def test_dont_create_new_season_if_there_is_an_active_one(self):
        self.assertEqual(models.Season.objects.count(), 0)
        automated_seasons.create_automated_seasons()
        self.assertEqual(models.Season.objects.count(), 1)
        automated_seasons.create_automated_seasons()
        self.assertEqual(models.Season.objects.count(), 1)

    def test_create_new_season_if_there_isnt_an_active_one(self):
        with freeze_time("2021-05-01"):
            self.assertEqual(models.Season.objects.count(), 0)
            automated_seasons.create_automated_seasons()
            self.assertEqual(models.Season.objects.count(), 1)
            automated_seasons.create_automated_seasons()
            self.assertEqual(models.Season.objects.count(), 1)

        with freeze_time("2021-07-01"):
            automated_seasons.update_seasons_state()

            automated_seasons.create_automated_seasons()
            self.assertEqual(models.Season.objects.count(), 2)

    def test_create_agent_ratings(self):
        self.assertEqual(models.AgentRatings.objects.count(), 0)
        automated_seasons.create_automated_seasons()
        self.assertEqual(models.AgentRatings.objects.count(), 4)


class MatchQueueTestCase(TestCase):
    def test_for_smoke(self):
        automated_seasons.create_automated_seasons()
        automated_tournaments.create_automated_tournaments()
        services.update_tournaments_state()
        match_queue.regenerate_queue()


class TrophyTestCase(TestCase):
    def setUp(self):
        models.Season.objects.all().delete()

        self.game = factories.GameFactory()
        self.season = factories.SeasonFactory()
        self.tournament = factories.TournamentFactory(
            game=self.game, season=self.season
        )
        self.agent1 = factories.AgentFactory(game=self.game)
        self.agent2 = factories.AgentFactory(game=self.game)
        self.agent3 = factories.AgentFactory(game=self.game)

        self.match1 = factories.MatchFactory(
            player1=self.agent1,
            player2=self.agent2,
            season=self.season,
            tournament=self.tournament,
            game=self.game,
            result=1,
            ran=True,
        )
        self.match2 = factories.MatchFactory(
            player1=self.agent2,
            player2=self.agent3,
            season=self.season,
            tournament=self.tournament,
            game=self.game,
            result=1,
            ran=True,
        )
        self.match3 = factories.MatchFactory(
            player1=self.agent1,
            player2=self.agent3,
            season=self.season,
            tournament=self.tournament,
            game=self.game,
            result=1,
            ran=True,
        )

    def test_for_smoke(self):
        # This calls create tournament internally
        services.update_tournaments_state()
        self.tournament.refresh_from_db()

        self.assertEqual(self.agent1.trophies.first().type, "FIRST")
        self.assertEqual(self.agent2.trophies.first().type, "SECOND")
        self.assertEqual(self.agent3.trophies.first().type, "THIRD")

        self.assertEqual(self.tournament.trophies.count(), 3)

    def test_trophy_regen(self):
        services.update_tournaments_state()
        self.tournament.refresh_from_db()

        self.tournament.trophies.first().delete()  # Simulate failed trophy gen
        self.assertEqual(self.tournament.trophies.count(), 2)

        trophy.create_trophies(self.tournament)

        self.assertEqual(self.agent1.trophies.first().type, "FIRST")
        self.assertEqual(self.agent2.trophies.first().type, "SECOND")
        self.assertEqual(self.agent3.trophies.first().type, "THIRD")

        self.assertEqual(self.tournament.trophies.count(), 3)

    def test_tie(self):
        self.agent4 = factories.AgentFactory(game=self.game)
        for a1, a2 in [
            (self.agent3, self.agent4),
            (self.agent4, self.agent3),
            (self.agent2, self.agent4),
            (self.agent1, self.agent2),
        ]:
            factories.MatchFactory(
                player1=a1,
                player2=a2,
                season=self.season,
                tournament=self.tournament,
                game=self.game,
                result=1,
                ran=True,
            )

        services.update_tournaments_state()
        self.tournament.refresh_from_db()
        trophy.create_trophies(self.tournament)

        self.assertEqual(self.agent1.trophies.first().type, "FIRST")
        self.assertEqual(self.agent2.trophies.first().type, "SECOND")
        self.assertEqual(self.agent3.trophies.first().type, "THIRD")
        self.assertEqual(self.agent4.trophies.first().type, "THIRD")

        self.assertEqual(self.tournament.trophies.count(), 4)


class PrettifyTimeDelta(TestCase):
    def setUp(self):
        pass

    def test_multiple_values(self):
        self.assertEqual(
            "1 day",
            services.prettify_time_delta(timedelta(days=1).total_seconds()),
        )

        self.assertEqual(
            "1 day and 2 hours",
            services.prettify_time_delta(
                timedelta(days=1, seconds=60 * 60 * 2 + 25).total_seconds()
            ),
        )
