from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from app import factories, models
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
