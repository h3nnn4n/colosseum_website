import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from app import models, serializers


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("SERVICES")


def update_seasons_state():
    for season in models.Season.objects.all():
        update_season_state(season)


def update_season_state(season):
    now = timezone.now()

    if season.end_date < now:
        season.active = False
        season.save(update_fields=["active"])

    if season.start_date >= now and not season.active:
        season.active = True
        season.save(update_fields=["active"])


def create_automated_seasons():
    if not settings.ENABLE_AUTOMATED_SEASONS:
        return

    now = timezone.now()
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = now.replace(
        hour=23, minute=59, second=59, microsecond=999999
    ) + timedelta(days=6)
    last_automated_season = (
        models.Season.objects.filter(is_automated=True)
        .order_by("-automated_number")
        .first()
    )

    if last_automated_season:
        next_number = last_automated_season.automated_number + 1
    else:
        next_number = 1

    if last_automated_season and last_automated_season.active:
        return {"status": "active season already exists"}

    name = f"Automated Season {next_number}"

    data = {
        "name": name,
        "is_automated": True,
        "automated_number": next_number,
        "start_date": start_date,
        "end_date": end_date,
    }
    serializer = serializers.SeasonSerializer(data=data)
    if serializer.is_valid():
        logger.info(f'creating automated season "{name}"')
        serializer.save()

        create_ratings_for_season(serializer.instance)
    else:
        logger.warning(f'failed to create season "{name}"')


def create_ratings_for_season(season):
    for agent in models.Agent.objects.active().all():
        models.AgentRatings.objects.create(season=season, agent=agent, game=agent.game)
