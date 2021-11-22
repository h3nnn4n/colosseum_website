import factory
from factory.fuzzy import FuzzyInteger

from . import models


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.User

    email = factory.Faker("email")
    username = factory.Faker("name")
    password = factory.PostGenerationMethodCall("set_password", "foobar")

    is_staff = False
    is_superuser = False
    is_active = True


class AgentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Agent

    name = factory.Sequence(lambda n: "Agent %03d" % n)

    owner = factory.SubFactory(UserFactory)

    wins = FuzzyInteger(0, 100)
    loses = FuzzyInteger(0, 100)
    draws = FuzzyInteger(0, 100)
    score = factory.LazyAttribute(lambda o: o.wins + o.draws)
    elo = FuzzyInteger(1000, 2000)


class GameFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Game

    name = factory.Sequence(lambda n: "test_game %03d" % n)


class TournamentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Tournament

    name = factory.Sequence(lambda n: "Tournament %03d" % n)
    mode = "ROUND_ROBIN"
    game = factory.SubFactory(GameFactory)


class MatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Match

    tournament = factory.SubFactory(TournamentFactory)
    ran = False
