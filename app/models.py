import itertools
import logging
import uuid
from collections import defaultdict
from datetime import timedelta
from math import ceil

import humanize
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import F, QuerySet
from django.utils import timezone
from django.utils.functional import cached_property

from . import utils


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("APP")


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(null=True)


class AgentQuerySet(QuerySet):
    def active(self):
        return self.filter(active=True)

    def by_elo(self):
        return (
            self.filter(ratings__season__active=True, ratings__season__main=True)
            .annotate(elo_rating=F("ratings__elo"))
            .order_by("-elo_rating")
        )


class Agent(BaseModel):
    name = models.CharField(max_length=64, unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="agents")
    file = models.FileField(null=True, upload_to=utils.agent_filepath)
    file_hash = models.CharField(max_length=128, null=True)
    active = models.BooleanField(default=True)

    game = models.ForeignKey("Game", on_delete=models.CASCADE, related_name="agents")

    objects = AgentQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["file_hash"]),
            models.Index(fields=["game"]),
            models.Index(fields=["name"]),
            models.Index(fields=["owner"]),
        ]

    @cached_property
    def current_ratings(self):
        # FIXME: We shouldn't be creating stuff on a getter
        # TODO: Cache this so we are not querrying the database all the time.
        # We might also use a try except instead, since the excep path is much
        # more unlikely to get executed anyways. It might mess up transactions
        # thought, so idk if it is worth it.
        if not self.ratings.filter(season__active=True, season__main=True).exists():
            season = Season.objects.get(active=True, main=True)
            AgentRatings.objects.create(season=season, agent=self, game=self.game)

        return self.ratings.get(season__active=True, season__main=True)

    @property
    def win_ratio(self):
        if self.games_played_count == 0:
            return 0
        return self.wins / self.games_played_count

    @property
    def pretty_win_ratio(self):
        return f"{self.win_ratio * 100.0:.2f}"

    @property
    def games_played_count(self):
        return int(self.wins + self.loses + self.draws)

    @property
    def games_played(self):
        Season = apps.get_model("app", "Season")
        current_season = Season.objects.get(active=True, main=True)
        return self.matches.filter(ran=True, season=current_season)

    @property
    def most_recent_match(self):
        return self.matches.filter(ran=True).order_by("-ran_at").first()

    @property
    def download_url(self):
        if self.file:
            return self.file.url
        return None

    @property
    def wins(self):
        return self.current_ratings.wins

    @property
    def loses(self):
        return self.current_ratings.loses

    @property
    def draws(self):
        return self.current_ratings.draws

    @property
    def score(self):
        return self.current_ratings.score

    @property
    def elo(self):
        return self.current_ratings.elo


class AgentRatings(BaseModel):
    agent = models.ForeignKey("Agent", on_delete=models.CASCADE, related_name="ratings")
    game = models.ForeignKey("Game", on_delete=models.CASCADE)
    season = models.ForeignKey(
        "Season", on_delete=models.CASCADE, related_name="ratings"
    )

    wins = models.IntegerField(default=0)
    loses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    score = models.DecimalField(default=0, decimal_places=2, max_digits=10)
    elo = models.DecimalField(default=1500, decimal_places=2, max_digits=10)

    class Meta:
        unique_together = ("agent", "game", "season")
        indexes = [
            models.Index(fields=["agent"]),
            models.Index(fields=["season"]),
            models.Index(fields=["game"]),
        ]

    def reset(self, save=True):
        self.wins = 0
        self.loses = 0
        self.draws = 0
        self.score = 0
        self.elo = 1500

        if save:
            self.save(update_fields=["wins", "loses", "draws", "score", "elo"])


class SeasonQuerySet(QuerySet):
    def current_season(self):
        return self.get(active=True, main=True)


class Season(BaseModel):
    name = models.CharField(max_length=64, unique=True)
    active = models.BooleanField(default=True)
    main = models.BooleanField(default=True)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)

    is_automated = models.BooleanField(null=True, default=False)
    automated_number = models.IntegerField(null=True)

    objects = SeasonQuerySet.as_manager()

    class Meta:
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return f"{self.name} ({self.id})"

    @property
    def duration(self):
        return self.end_date - self.start_date

    @property
    def duration_humanized(self):
        duration = ceil(self.duration.total_seconds())
        return humanize.precisedelta(
            duration,
            format="%0.0f",
        )

    @property
    def time_left(self):
        now = timezone.now()
        if self.end_date < now:
            return timedelta()

        return self.end_date - now

    @property
    def time_left_humanized(self):
        if self.time_left.total_seconds() <= 0:
            return "-"

        return humanize.precisedelta(
            self.time_left,
            format="%0.0f",
        )

    @cached_property
    def matches_count(self):
        return self.matches.count()

    @cached_property
    def matches_pending_count(self):
        return self.matches.filter(ran=False).count()

    @cached_property
    def matches_played_count(self):
        return self.matches.filter(ran=True).count()

    @cached_property
    def tournaments_count(self):
        return self.tournaments.count()


class GameQuerySet(QuerySet):
    def active(self):
        return self.filter(active=True)


class Game(BaseModel):
    name = models.CharField(max_length=64, unique=True)
    active = models.BooleanField(default=True)

    short_description = models.TextField(default="")
    description = models.TextField(default="")

    wiki_url = models.TextField(null=True)

    objects = GameQuerySet.as_manager()

    class Meta:
        indexes = [models.Index(fields=["name"])]

    @property
    def pretty_name(self):
        return " ".join(self.name.split("_")).capitalize()

    @property
    def open_tournaments(self):
        return self.tournaments.filter(done=False)


class MatchQuerySet(QuerySet):
    @property
    def played(self):
        return self.filter(ran=True)

    @property
    def tainted(self):
        return self.filter(outcome__termination="TAINTED")

    @property
    def by_ran_at(self):
        return self.order_by("-ran_at")

    def top_n(self, n=25):
        return self[:n]


class Match(BaseModel):
    participants = models.ManyToManyField(Agent, related_name="matches")
    player1 = models.ForeignKey(
        Agent, null=True, related_name="+", on_delete=models.CASCADE
    )
    player2 = models.ForeignKey(
        Agent, null=True, related_name="+", on_delete=models.CASCADE
    )
    ran_at = models.DateTimeField(null=True)
    ran = models.BooleanField(default=False)
    duration = models.DecimalField(decimal_places=20, max_digits=25, null=True)
    tournament = models.ForeignKey(
        "Tournament", on_delete=models.CASCADE, related_name="matches"
    )
    result = models.DecimalField(default=-1, decimal_places=1, max_digits=3)
    data = models.JSONField(default=dict)
    replay = models.FileField(null=True, upload_to=utils.replay_filepath)

    end_reason = models.CharField(
        null=True,
        max_length=255,
        choices=[
            ("RULES", "Rules"),
            ("TAINTED", "Tainted"),
        ],
    )
    outcome = models.JSONField(default=dict)
    raw_result = models.JSONField(default=dict)

    game = models.ForeignKey("Game", on_delete=models.CASCADE, related_name="matches")
    season = models.ForeignKey(
        "Season", on_delete=models.CASCADE, related_name="matches"
    )

    objects = MatchQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["game"]),
            models.Index(fields=["player1"]),
            models.Index(fields=["player2"]),
            models.Index(fields=["ran"]),
            models.Index(fields=["ran_at"]),
            models.Index(fields=["season"]),
            models.Index(fields=["tournament"]),
        ]

    @property
    def pretty_end_reason(self):
        if not self.end_reason:
            return "-"

        pretty_str = self.end_reason

        if outcome := self.outcome.get("termination"):
            if outcome == "TAINTED":
                tainted_reason = self.outcome.get("tainted_reason", outcome)
                pretty_str += f" [{tainted_reason}]"
            else:
                pretty_str += f" [{outcome}]"

        return pretty_str

    @property
    def pretty_result(self):
        if not self.ran:
            return "-"

        if self.result == 0:
            return "0 - 1"
        if self.result == 1:
            return "1 - 0"
        if self.result > 0 and self.result < 1:
            return "0.5 - 0.5"
        raise ValueError(
            f"Only 0, 1, or 0.5 are valid results. Got {self.result} instead"
        )

    @property
    def player1_elo_change(self):
        try:
            player1_id = str(self.player1.id)
            return self.data["elo_change"][player1_id]
        except KeyError:
            return None

    @property
    def player2_elo_change(self):
        try:
            player2_id = str(self.player2.id)
            return self.data["elo_change"][player2_id]
        except KeyError:
            return None

    @property
    def tainted(self):
        return self.outcome.get("termination") == "TAINTED"


class Tournament(BaseModel):
    MODES = [
        ("ROUND_ROBIN", "Round Robin"),
        ("DOUBLE_ROUND_ROBIN", "Double Round Robin"),
        ("TRIPLE_ROUND_ROBIN", "Triple Round Robin"),
        ("TIMED", "Timed"),
    ]

    name = models.CharField(max_length=64, unique=True)
    game = models.ForeignKey(
        "Game", on_delete=models.CASCADE, related_name="tournaments"
    )
    season = models.ForeignKey(
        "Season", on_delete=models.CASCADE, related_name="tournaments"
    )
    participants = models.ManyToManyField(Agent, related_name="tournaments")

    mode = models.CharField(max_length=64, choices=MODES)

    # For timed tournaments, this is when they start and end at
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)

    is_automated = models.BooleanField(null=True, default=False)
    automated_number = models.IntegerField(null=True)

    done = models.BooleanField(null=True, default=False)

    class Meta:
        indexes = [
            models.Index(fields=["done"]),
            models.Index(fields=["game"]),
            models.Index(fields=["is_automated"]),
            models.Index(fields=["mode"]),
            models.Index(fields=["name"]),
            models.Index(fields=["season"]),
        ]

    @property
    def is_active(self):
        if self.mode == "TIMED":
            now = timezone.now()
            return self.start_date <= now and now <= self.end_date

        return self.has_pending_matches

    @property
    def has_pending_matches(self):
        return self.matches.filter(ran=False).exists()

    @property
    def pending_matches_count(self):
        return self.matches.filter(ran=False).count()

    @property
    def played_matches_count(self):
        return self.matches.filter(ran=True).count()

    @property
    def ratings(self):
        score = defaultdict(int)
        wins = defaultdict(int)
        loses = defaultdict(int)
        draws = defaultdict(int)
        player_map = {}

        for match in self.matches.all():
            # Dumb way to have an id -> Object mapping without extra queries
            player_map[match.player1.id] = match.player1
            player_map[match.player2.id] = match.player2

            if match.result == 0:
                score[match.player1.id] += 0
                score[match.player2.id] += 1
                wins[match.player2.id] += 1
                loses[match.player1.id] += 1
            if match.result == 0.5:
                score[match.player1.id] += 0.5
                score[match.player2.id] += 0.5
                draws[match.player1.id] += 1
                draws[match.player2.id] += 1
            if match.result == 1:
                score[match.player1.id] += 1
                score[match.player2.id] += 0
                wins[match.player1.id] += 1
                loses[match.player2.id] += 1

        sorted_score = sorted(score.items(), key=lambda x: x[1], reverse=True)

        results = []
        for id, _ in sorted_score:
            results.append(
                TournamentResult(
                    agent=player_map[id],
                    score=score[id],
                    wins=wins[id],
                    loses=loses[id],
                    draws=draws[id],
                )
            )
        return results

    def pending_matches(self, limit=25):
        return self.matches.filter(ran=False).order_by("created_at")[0:limit]

    def played_matches(self, limit=25):
        return self.matches.filter(ran=True).order_by("-ran_at")[0:limit]

    def create_matches(self):
        from app.services import match_queue

        logger.info(
            f"Creating matches for tournament {self.id} {self.name} {self.mode} with {self.pending_matches_count} matches"
        )
        n_rounds = 1

        if self.mode == "DOUBLE_ROUND_ROBIN":
            n_rounds = 2

        if self.mode == "TRIPLE_ROUND_ROBIN":
            n_rounds = 3

        participants = list(self.participants.all())
        new_match_ids = []
        for _ in range(n_rounds):
            for bracket in itertools.combinations(participants, 2):
                bracket = list(bracket)
                match = Match.objects.create(
                    player1=bracket[0],
                    player2=bracket[1],
                    ran=False,
                    ran_at=None,
                    tournament=self,
                    game=self.game,
                    season=self.season,
                )
                match.participants.add(*bracket)
                match.save()
                new_match_ids.append(match.id)

        match_queue.add_many(new_match_ids)

        logger.info(
            f"Tournament {self.id} {self.name} {self.mode} has {self.pending_matches_count} matches now"
        )


class Trophy(BaseModel):
    TYPE_CHOICES = [
        ("FIRST", "First Place"),
        ("SECOND", "Second Place"),
        ("THIRD", "Third Place"),
    ]

    game = models.ForeignKey("Game", on_delete=models.CASCADE, related_name="trophies")
    season = models.ForeignKey(
        "Season", on_delete=models.CASCADE, related_name="trophies"
    )
    tournament = models.ForeignKey(
        "Tournament", on_delete=models.CASCADE, related_name="trophies"
    )
    agent = models.ForeignKey(
        "Agent", on_delete=models.CASCADE, related_name="trophies"
    )
    type = models.CharField(
        max_length=255,
        choices=TYPE_CHOICES,
    )

    class Meta:
        indexes = [
            models.Index(fields=["agent"]),
            models.Index(fields=["game"]),
            models.Index(fields=["season"]),
            models.Index(fields=["tournament"]),
            models.Index(fields=["type"]),
        ]


# Non ORM models.  Just stuff to make passing data around easier. Not that this
# is ephemeral and not persisted on the database.
class TournamentResult:
    def __init__(self, *, agent, score, wins, loses, draws):
        self.agent = agent
        self.name = agent.name
        self.id = agent.id
        self.score = score
        self.wins = wins
        self.loses = loses
        self.draws = draws

    @property
    def win_ratio(self):
        return self.wins / self.games_played_count

    @property
    def pretty_win_ratio(self):
        return f"{self.win_ratio * 100.0:.2f}"

    @property
    def games_played_count(self):
        return self.loses + self.draws + self.wins
