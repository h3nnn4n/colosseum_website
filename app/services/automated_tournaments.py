import logging

from django.conf import settings
from django.utils import timezone

from .. import models, serializers


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("AUTOMATED_TOURNAMENTS")


def create_automated_tournaments():
    if not models.Season.objects.filter(active=True).exists():
        logger.info("There are no active seasons. Doing nothing")
        return

    for game in models.Game.objects.filter(active=True):
        if game.agents.count() < 2:
            logger.info(
                f"'{game.name}' '{game.id}' doesn't have enough agents for a tournament"
            )
            continue

        # _create_automated_tournament("Daily {} Tournament #{}", "TIMED", game)
        _create_automated_tournament("{} Tournament #{}", "ROUND_ROBIN", game)
        _create_automated_tournament(
            "{} Double RR Tournament #{}", "DOUBLE_ROUND_ROBIN", game
        )
        _create_automated_tournament(
            "{} Triple RR Tournament #{}", "TRIPLE_ROUND_ROBIN", game
        )


def _create_automated_tournament(name, mode, game):
    """
    Creates an automated tournament. If such a tournament already exists it
    does nothing, otherwise it creates a new one.
    """
    now = timezone.now()
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = now.replace(hour=23, minute=59, second=59, microsecond=999)

    last_automated_tournament = (
        models.Tournament.objects.filter(mode=mode, is_automated=True, game=game)
        .order_by("-automated_number")
        .first()
    )

    if last_automated_tournament:
        next_number = last_automated_tournament.automated_number + 1
    else:
        next_number = 1

    if last_automated_tournament and last_automated_tournament.is_active:
        return {"status": "active tournament already exists"}

    name = name.format(game.pretty_name, next_number)

    data = {
        "mode": mode,
        "start_date": start_date,
        "end_date": end_date,
        "game_id": str(game.id),
        "name": name,
        "is_automated": True,
        "automated_number": next_number,
    }
    serializer = serializers.TournamentSerializer(data=data)
    if serializer.is_valid():
        logger.info(f'creating automated tournament "{name}"')
        serializer.save()
    else:
        logger.warning(f'failed to create tournamend "{name}"')
