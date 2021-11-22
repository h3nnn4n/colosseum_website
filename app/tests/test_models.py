from django.test import TestCase

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
