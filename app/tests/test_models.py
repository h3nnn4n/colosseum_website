from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time

from app import factories, models


class AgentTestCase(TestCase):
    def setUp(self):
        factories.SeasonFactory()

    def test_score(self):
        agent = factories.AgentFactory()
        self.assertEqual(agent.wins + agent.draws, agent.score)

    def test_games_played_count(self):
        agent = factories.AgentFactory()
        self.assertEqual(agent.games_played_count, 0)


class MatchTestCase(TestCase):
    def setUp(self):
        pass

    def test_something(self):
        self.assertTrue(True)


class TournamentTestCase(TestCase):
    def test_is_active_round_robin(self):
        tournament = factories.TournamentFactory(mode="ROUND_ROBIN")
        self.assertFalse(tournament.is_active)

        match = factories.MatchFactory(tournament=tournament, ran=False)
        self.assertTrue(tournament.is_active)

        match.ran = True
        match.save()

        self.assertFalse(tournament.is_active)

    @freeze_time("2021-05-14")
    def test_is_active_timed(self):
        tournament = factories.TournamentFactory(
            mode="TIMED",
            start_date=timezone.now() - timedelta(hours=1),
            end_date=timezone.now() + timedelta(hours=1),
        )
        self.assertTrue(tournament.is_active)

        tournament = factories.TournamentFactory(
            mode="TIMED",
            start_date=timezone.now() - timedelta(hours=2),
            end_date=timezone.now() - timedelta(hours=1),
        )
        self.assertFalse(tournament.is_active)

    def test_create_matches(self):
        agents = [factories.AgentFactory() for x in range(5)]
        tournament = factories.TournamentFactory(mode="ROUND_ROBIN")
        tournament.participants.set(agents)

        self.assertEqual(
            models.Match.objects.filter(tournament_id=tournament.id).count(), 0
        )
        tournament.create_matches()
        self.assertEqual(
            models.Match.objects.filter(tournament_id=tournament.id).count(), 10
        )
