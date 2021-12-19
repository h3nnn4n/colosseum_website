import logging

from django.conf import settings

from .. import models


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("APP")


def purge_all_played_games():
    models.Agent.objects.all().update(wins=0, loses=0, draws=0, elo=1500, score=0)
    models.Match.objects.all().delete()


def purge_all_tournaments():
    models.Tournament.objects.all().delete()
    models.Match.objects.all().delete()


def update_tournament_state(tournament):
    if (
        tournament.mode == "TIMED"
        and tournament.is_active
        and tournament.pending_matches <= 10
    ):
        logger.info(
            f"TIMED Tournament {tournament.id} has a low number of matches left: {tournament.pending_matches}"
        )
        tournament.create_matches()
    elif tournament.matches.count() == 0:
        logger.info(
            f"{tournament.mode} Tournament {tournament.id} is missing matches. Creating"
        )
        tournament.create_matches()

    if not tournament.is_active:
        tournament.done = True
        tournament.save(update_fields=["done"])
        logger.info(
            f"{tournament.mode} Tournament {tournament.id} was set to done=true"
        )
