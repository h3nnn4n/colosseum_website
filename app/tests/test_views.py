import datetime
from datetime import timedelta
from uuid import UUID

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.test import APIClient, force_authenticate

from .. import factories, models


class NextMatchAPIViewTestCase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.agent1 = factories.AgentFactory()
        self.agent2 = factories.AgentFactory()
        self.agent3 = factories.AgentFactory()

        self.admin_user = factories.UserFactory(is_staff=True)
        self.api_client = APIClient()

    def test_without_a_tournament(self):
        self.api_client.force_authenticate(user=self.admin_user)
        response = self.api_client.get("/api/next_match/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})

    def test_without_a_match(self):
        self.api_client.force_authenticate(user=self.admin_user)

        factories.TournamentFactory()
        response = self.api_client.get("/api/next_match/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})

    def test_no_match_active_timed_tournament(self):
        self.api_client.force_authenticate(user=self.admin_user)

        tournament = factories.TournamentFactory(
            mode="TIMED",
            start_date=timezone.now() - timedelta(hours=1),
            end_date=timezone.now() + timedelta(hours=1),
        )
        tournament.participants.set([self.agent1.id, self.agent2.id, self.agent3.id])
        response = self.api_client.get("/api/next_match/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})

    def test_no_match_active_timed_tournament_with_post(self):
        self.api_client.force_authenticate(user=self.admin_user)

        tournament = factories.TournamentFactory(
            mode="TIMED",
            start_date=timezone.now() - timedelta(hours=1),
            end_date=timezone.now() + timedelta(hours=1),
        )
        tournament.participants.set([self.agent1.id, self.agent2.id, self.agent3.id])
        response = self.api_client.post("/api/next_match/")
        response = self.api_client.get("/api/next_match/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            UUID(response.json()["id"]), tournament.matches.values_list("id", flat=True)
        )

    def test_without_auth(self):
        response = self.api_client.get("/api/next_match/")
        self.assertEqual(response.status_code, 401)

    def test_mark_completed_tournaments_as_done(self):
        self.api_client.force_authenticate(user=self.admin_user)

        tournament = factories.TournamentFactory(
            mode="ROUND_ROBIN",
            start_date=timezone.now() - timedelta(hours=1),
            end_date=timezone.now() + timedelta(hours=1),
        )
        tournament.participants.set([self.agent1.id, self.agent2.id, self.agent3.id])
        self.api_client.post("/api/next_match/")
        self.api_client.get("/api/next_match/")
        tournament.refresh_from_db()
        self.assertFalse(tournament.done)

        tournament.matches.update(ran=True)

        self.api_client.post("/api/next_match/")
        tournament.refresh_from_db()
        self.assertTrue(tournament.done)


class TournamentViewSetTestCase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.game2 = factories.GameFactory()

        self.agent1 = factories.AgentFactory(game=self.game)
        self.agent2 = factories.AgentFactory(game=self.game)
        self.agent3 = factories.AgentFactory(game=self.game)
        self.agent4 = factories.AgentFactory(game=self.game2)
        self.agent5 = factories.AgentFactory(game=self.game2)

        self.admin_user = factories.UserFactory(is_staff=True)
        self.api_client = APIClient()

    def test_create_tournament_with_all_participants(self):
        self.api_client.force_authenticate(user=self.admin_user)
        response = self.api_client.post(
            "/api/tournaments/",
            {"name": "foo", "game_id": self.game.id, "mode": "ROUND_ROBIN"},
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
                "game_id": self.game.id,
                "mode": "ROUND_ROBIN",
                "participants": [self.agent1.id, self.agent2.id],
            },
        )
        self.assertEqual(response.status_code, 201)

        id = response.json()["id"]
        tournament = models.Tournament.objects.get(id=id)
        self.assertEqual(tournament.participants.count(), 2)

    def test_create_tournament_with_participants_of_wrong_game(self):
        self.api_client.force_authenticate(user=self.admin_user)
        response = self.api_client.post(
            "/api/tournaments/",
            {
                "name": "foo",
                "game_id": self.game.id,
                "mode": "ROUND_ROBIN",
                "participants": [
                    self.agent1.id,
                    self.agent2.id,
                    self.agent3.id,
                    self.agent4.id,
                ],
            },
        )
        self.assertEqual(response.status_code, 400)

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

    def test_get_tournament(self):
        self.api_client.force_authenticate(user=self.admin_user)
        response = self.api_client.post(
            "/api/tournaments/",
            {
                "name": "foo",
                "game_id": self.game.id,
                "mode": "ROUND_ROBIN",
                "participants": [self.agent1.id, self.agent2.id],
            },
        )
        self.assertEqual(response.status_code, 201)

        data = response.json()
        self.assertFalse(data["done"])
