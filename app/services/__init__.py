from .. import models


def purge_all_played_games():
    models.Agent.objects.all().update(wins=0, loses=0, draws=0, elo=1500, score=0)
    models.Match.objects.all().delete()


def purge_all_tournaments():
    models.Tournament.objects.all().delete()
    models.Match.objects.all().delete()
