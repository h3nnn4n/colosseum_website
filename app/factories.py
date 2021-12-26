import factory

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


class SeasonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Season

    name = factory.Sequence(lambda n: "test_season %03d" % n)


class GameFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Game

    name = factory.Sequence(lambda n: "test_game %03d" % n)


class AgentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Agent

    name = factory.Sequence(lambda n: "Agent %03d" % n)

    owner = factory.SubFactory(UserFactory)
    game = factory.SubFactory(GameFactory)


class TournamentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Tournament

    name = factory.Sequence(lambda n: "Tournament %03d" % n)
    mode = "ROUND_ROBIN"
    game = factory.SubFactory(GameFactory)
    season = factory.SubFactory(SeasonFactory)


class MatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Match

    tournament = factory.SubFactory(TournamentFactory)
    game = factory.SubFactory(GameFactory)
    season = factory.SubFactory(SeasonFactory)

    ran = False
