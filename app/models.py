import uuid

from django.contrib.auth.models import User
from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Agent(BaseModel):
    name = models.CharField(max_length=64, unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        indexes = [models.Index(fields=["name"]), models.Index(fields=["owner"])]


class Game(BaseModel):
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        indexes = [models.Index(fields=["name"])]


class Match(BaseModel):
    participants = models.ManyToManyField(Agent)
    ran_at = models.DateTimeField(auto_now=True)
    ran = models.BooleanField(default=False)


class Tournament(BaseModel):
    name = models.CharField(max_length=64, unique=True)
    game = models.ForeignKey("Game", on_delete=models.CASCADE)
    participants = models.ManyToManyField(Agent)
    matches = models.ManyToManyField(Match)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=["name"]), models.Index(fields=["game"])]
