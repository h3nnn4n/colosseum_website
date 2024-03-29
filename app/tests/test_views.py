from datetime import timedelta
from uuid import UUID

from django.test import Client, TestCase
from django.utils import timezone
from django_redis import get_redis_connection
from rest_framework.test import APIClient

from .. import factories, models


class AgentListViewTestCase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.agent1 = factories.AgentFactory()
        self.agent2 = factories.AgentFactory()
        self.season = factories.SeasonFactory()

        self.admin_user = factories.UserFactory(is_staff=True)
        self.client = Client()

    def test_get(self):
        response = self.client.get("/agents/")
        self.assertEqual(response.status_code, 200)


class AgentDetailViewTestCase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.agent = factories.AgentFactory(game=self.game)
        self.season = factories.SeasonFactory()

        self.client = Client()

    def test_get(self):
        response = self.client.get(f"/agents/{self.agent.id}/")
        self.assertEqual(response.status_code, 200)


class AgentApiViewTestCase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.agent = factories.AgentFactory(game=self.game)
        self.season = factories.SeasonFactory()

        self.admin_user = factories.UserFactory(is_staff=True)
        self.client = APIClient()

    def test_get(self):
        response = self.client.get(f"/api/agents/{self.agent.id}/")
        self.assertEqual(response.status_code, 200)

    def test__file__no_auth(self):
        response = self.client.get(f"/api/agents/{self.agent.id}/")
        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("file", data.keys())

    def test__file__admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f"/api/agents/{self.agent.id}/")
        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertIn("file", data.keys())


class NextMatchAPIViewTestCase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.agent1 = factories.AgentFactory()
        self.agent2 = factories.AgentFactory()
        self.agent3 = factories.AgentFactory()

        self.admin_user = factories.UserFactory(is_staff=True)
        self.api_client = APIClient()

        redis = get_redis_connection("default")
        redis.delete("disable_next_match_api")

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

    def test_killswitch(self):
        self.api_client.force_authenticate(user=self.admin_user)

        redis = get_redis_connection("default")
        redis.set("disable_next_match_api", 1)

        tournament = factories.TournamentFactory(
            mode="TIMED",
            start_date=timezone.now() - timedelta(hours=1),
            end_date=timezone.now() + timedelta(hours=1),
        )
        tournament.participants.set([self.agent1.id, self.agent2.id, self.agent3.id])
        response = self.api_client.post("/api/next_match/")
        response = self.api_client.get("/api/next_match/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json().get("id"))

        redis.set("disable_next_match_api", 0)

        response = self.api_client.get("/api/next_match/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            UUID(response.json()["id"]), tournament.matches.values_list("id", flat=True)
        )


class TournamentViewSetTestCase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.game2 = factories.GameFactory()
        self.season = factories.SeasonFactory()

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


class MatchViewSetTestCase(TestCase):
    def setUp(self):
        self.game = factories.GameFactory()
        self.agent1 = factories.AgentFactory(game=self.game)
        self.agent2 = factories.AgentFactory(game=self.game)
        self.season = factories.SeasonFactory()
        self.season_old = factories.SeasonFactory(active=False)
        self.tournament = factories.TournamentFactory(
            game=self.game, season=self.season
        )

        self.admin_user = factories.UserFactory(is_staff=True)
        self.api_client = APIClient()

    def test_match_count(self):
        response = self.api_client.get("/api/matches/count/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 0)

        factories.MatchFactory(ran=False)
        factories.MatchFactory(ran=True)
        factories.MatchFactory(ran=True)
        factories.MatchFactory(ran=True)

        response = self.api_client.get("/api/matches/count/")
        self.assertEqual(response.data, 3)

    def test_match_count_current_season(self):
        factories.MatchFactory(
            ran=True, season=self.season_old, tournament=self.tournament
        )
        factories.MatchFactory(ran=True, season=self.season, tournament=self.tournament)
        factories.MatchFactory(ran=True, season=self.season, tournament=self.tournament)

        response = self.api_client.get("/api/matches/count/?current_season=true")
        self.assertEqual(response.data, 2)

    def test_match_count_hours_ago(self):
        factories.MatchFactory(ran=True, ran_at=timezone.now())
        factories.MatchFactory(ran=True, ran_at=timezone.now() - timedelta(hours=1))
        factories.MatchFactory(ran=True, ran_at=timezone.now() - timedelta(hours=6))
        factories.MatchFactory(ran=True, ran_at=timezone.now() - timedelta(hours=12))
        factories.MatchFactory(ran=True, ran_at=timezone.now() - timedelta(hours=32))

        response = self.api_client.get("/api/matches/count/?hours_ago=1")
        self.assertEqual(response.data, 1)

        response = self.api_client.get("/api/matches/count/?hours_ago=16")
        self.assertEqual(response.data, 4)

        response = self.api_client.get("/api/matches/count/?hours_ago=48")
        self.assertEqual(response.data, 5)

    def test_match_update(self):
        match = models.Match.objects.create(
            game=self.game,
            tournament=self.tournament,
            player1=self.agent1,
            player2=self.agent2,
            season=self.season,
        )

        self.api_client.force_authenticate(user=self.admin_user)
        response = self.api_client.patch(
            f"/api/matches/{match.id}/",
            {"ran": True, "ran_at": timezone.now(), "result": 1},
        )
        self.assertEqual(response.status_code, 200)

        match.refresh_from_db()

        self.assertEqual(match.data["elo_before"][str(self.agent1.id)], 1500)
        self.assertEqual(match.data["elo_before"][str(self.agent2.id)], 1500)

        self.assertEqual(match.data["elo_after"][str(self.agent1.id)], 1512)
        self.assertEqual(match.data["elo_after"][str(self.agent2.id)], 1488)

        self.assertEqual(match.data["elo_change"][str(self.agent1.id)], 12)
        self.assertEqual(match.data["elo_change"][str(self.agent2.id)], -12)


class SeasonDetailViewTestCase(TestCase):
    def setUp(self):
        self.season = factories.SeasonFactory(
            start_date=timezone.now() - timedelta(hours=1),
            end_date=timezone.now() + timedelta(hours=1),
        )
        self.season_old = factories.SeasonFactory(
            start_date=timezone.now() - timedelta(hours=2),
            end_date=timezone.now() - timedelta(hours=1),
        )

        self.client = Client()

    def test_get_active_season(self):
        response = self.client.get(f"/seasons/{self.season.id}/")
        self.assertEqual(response.status_code, 200)

    def test_get_old_season(self):
        response = self.client.get(f"/seasons/{self.season_old.id}/")
        self.assertEqual(response.status_code, 200)
