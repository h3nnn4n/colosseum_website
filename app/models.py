import uuid

from django.contrib.auth.models import User
from django.db import models

from . import utils


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Agent(BaseModel):
    name = models.CharField(max_length=64, unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    file_path = models.CharField(max_length=255, unique=True, null=True)
    file = models.FileField(null=True, upload_to=utils.agent_filepath)

    class Meta:
        indexes = [models.Index(fields=["name"]), models.Index(fields=["owner"])]

    @property
    def download_url(self):
        if self.file:
            return self.file.url
        return None


class AgentRating(BaseModel):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    wins = models.IntegerField(default=0)
    loses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    score = models.DecimalField(default=0, decimal_places=2, max_digits=10)
    elo = models.DecimalField(default=1500, decimal_places=2, max_digits=10)


class Game(BaseModel):
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        indexes = [models.Index(fields=["name"])]


class Match(BaseModel):
    participants = models.ManyToManyField(Agent, related_name="matches")
    ran_at = models.DateTimeField(auto_now=True)
    ran = models.BooleanField(default=False)
    tournament = models.ForeignKey("Tournament", null=True, on_delete=models.CASCADE)


class Tournament(BaseModel):
    name = models.CharField(max_length=64, unique=True)
    game = models.ForeignKey("Game", on_delete=models.CASCADE)
    participants = models.ManyToManyField(Agent, related_name="tournaments")
    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)

    class Meta:
        indexes = [models.Index(fields=["name"]), models.Index(fields=["game"])]
