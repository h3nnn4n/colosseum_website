import itertools
import logging
import uuid
from collections import defaultdict

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from . import utils


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("APP")


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Agent(BaseModel):
    name = models.CharField(max_length=64, unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(null=True, upload_to=utils.agent_filepath)
    file_hash = models.CharField(max_length=128, null=True)
    active = models.BooleanField(default=True)

    wins = models.IntegerField(default=0)
    loses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    score = models.DecimalField(default=0, decimal_places=2, max_digits=10)
    elo = models.DecimalField(default=1500, decimal_places=2, max_digits=10)

    class Meta:
        indexes = [
            models.Index(fields=["elo"]),
            models.Index(fields=["file_hash"]),
            models.Index(fields=["name"]),
            models.Index(fields=["owner"]),
        ]

    @property
    def win_ratio(self):
        if self.games_played == 0:
            return 0
        return self.wins / self.games_played

    @property
    def pretty_win_ratio(self):
        if self.games_played == 0:
            return "0"
        return f"{(self.wins / self.games_played) * 100.0:.2f}"

    @property
    def games_played(self):
        return self.matches.filter(ran=True).count()

    @property
    def most_recent_match(self):
        return self.matches.filter(ran=True).order_by("-ran_at").first()

    @property
    def download_url(self):
        if self.file:
            return self.file.url
        return None


class Game(BaseModel):
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        indexes = [models.Index(fields=["name"])]


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
    tournament = models.ForeignKey(
        "Tournament", on_delete=models.CASCADE, related_name="matches"
    )
    result = models.DecimalField(default=-1, decimal_places=1, max_digits=3)
    data = models.JSONField(default=dict)
    errors = models.JSONField(default=dict)
    replay = models.FileField(null=True, upload_to=utils.replay_filepath)

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


class Tournament(BaseModel):
    MODES = [
        ("ROUND_ROBIN", "Round Robin"),
        ("DOUBLE_ROUND_ROBIN", "Double Round Robin"),
        ("TRIPLE_ROUND_ROBIN", "Triple Round Robin"),
        ("TIMED", "Timed"),
    ]

    name = models.CharField(max_length=64, unique=True)
    game = models.ForeignKey("Game", on_delete=models.CASCADE)
    participants = models.ManyToManyField(Agent, related_name="tournaments")

    mode = models.CharField(max_length=64, choices=MODES)

    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)

    is_automated = models.BooleanField(null=True, default=False)
    automated_number = models.IntegerField(null=True)

    class Meta:
        indexes = [models.Index(fields=["name"]), models.Index(fields=["game"])]

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
    def pending_matches(self):
        return self.matches.filter(ran=False).count()

    @property
    def ratings(self):
        score = defaultdict(int)

        for match in self.matches.all():
            if match.result == 0:
                score[match.player2.name] += 1
            if match.result == 0.5:
                score[match.player1.name] += 0.5
                score[match.player2.name] += 0.5
            if match.result == 1:
                score[match.player1.name] += 1

        sorted_score = sorted(score.items(), key=lambda x: x[1], reverse=True)

        return [TournamentResult(name, score) for name, score in sorted_score]

    def create_matches(self):
        logger.info(
            f"Creating matches for tournament {self.id} {self.name} {self.mode} with {self.pending_matches} matches"
        )
        n_rounds = 1

        if self.mode == "DOUBLE_ROUND_ROBIN":
            n_rounds = 2

        if self.mode == "TRIPLE_ROUND_ROBIN":
            n_rounds = 3

        participants = list(self.participants.all())
        for _ in range(n_rounds):
            for bracket in itertools.combinations(participants, 2):
                bracket = list(bracket)
                match = Match.objects.create(
                    player1=bracket[0],
                    player2=bracket[1],
                    ran=False,
                    ran_at=None,
                    tournament=self,
                )
                match.participants.add(*bracket)
                match.save()

        logger.info(
            f"Tournament {self.id} {self.name} {self.mode} has {self.pending_matches} matches now"
        )


# Non ORM models.  Just stuff to make passing data around easier, but
# that is ephemeral and not persisted on the database.
class TournamentResult:
    def __init__(self, name, score):
        self.name = name
        self.score = score
