from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time

from app import factories, models


class AgentTestCase(TestCase):
    def test_score(self):
        agent = factories.AgentFactory()
        self.assertEqual(agent.wins + agent.draws, agent.score)


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
