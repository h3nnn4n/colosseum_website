import datetime

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, force_authenticate

from .. import factories, models


class TournamentViewSetTestCase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.agent1 = factories.AgentFactory()
        self.agent2 = factories.AgentFactory()
        self.agent3 = factories.AgentFactory()

        self.admin_user = factories.UserFactory(is_staff=True)
        self.api_client = APIClient()

    def test_create_tournament_with_all_participants(self):
        self.api_client.force_authenticate(user=self.admin_user)
        response = self.api_client.post(
            "/api/tournaments/",
            {"name": "foo", "game": self.game.id, "mode": "ROUND_ROBIN"},
        )
        self.assertEqual(response.status_code, 201)

        id = response.json()["id"]
        tournament = models.Tournament.objects.get(id=id)
        self.assertEqual(tournament.participants.count(), 3)

    def test_create_tournament_with_explicit_participants(self):
        self.api_client.force_authenticate(user=self.admin_user)
        response = self.api_client.post(
            "/api/tournaments/",
            {
                "name": "foo",
                "game": self.game.id,
                "mode": "ROUND_ROBIN",
                "participants": [self.agent1.id, self.agent2.id],
            },
        )
        self.assertEqual(response.status_code, 201)

        id = response.json()["id"]
        tournament = models.Tournament.objects.get(id=id)
        self.assertEqual(tournament.participants.count(), 2)

    def test_create_tournament_without_auth(self):
        response = self.api_client.post(
            "/api/tournaments/",
            {
                "name": "foo",
                "game": self.game.id,
                "mode": "ROUND_ROBIN",
                "participants": [self.agent1.id, self.agent2.id],
            },
        )
        self.assertEqual(response.status_code, 401)
