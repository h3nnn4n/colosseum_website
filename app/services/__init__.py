import logging

from django.conf import settings
from django.utils import timezone
from django_redis import get_redis_connection

from app import models, serializers
from app.services.ratings import update_ratings_from_match


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("SERVICES")


def purge_all_played_games():
    models.Agent.objects.all().update(wins=0, loses=0, draws=0, elo=1500, score=0)
    models.Match.objects.all().delete()


def purge_all_tournaments():
    models.Tournament.objects.all().delete()
    models.Match.objects.all().delete()


def update_tournaments_state():
    for tournament in models.Tournament.objects.all():
        update_tournament_state(tournament)


def update_tournament_state(tournament):
    if (
        tournament.mode == "TIMED"
        and tournament.is_active
        and tournament.pending_matches_count <= 10
    ):
        logger.info(
            f"TIMED Tournament {tournament.id} has a low number of matches left: {tournament.pending_matches_count}"
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

    # Ensure that pending tournament matches are enqueued to be played
    pending_match_ids = tournament.matches.filter(ran=False).values_list(
        "id", flat=True
    )
    pending_match_ids = list(map(str, pending_match_ids))
    redis = get_redis_connection("default")
    for id in pending_match_ids:
        redis.sadd(settings.MATCH_QUEUE_KEY, id)


def update_seasons_state():
    for season in models.Season.objects.all():
        update_season_state(season)


def update_season_state(season):
    now = timezone.now()

    if season.end_date < now:
        season.active = False
        season.save(update_fields=["active"])


def create_automated_seasons():
    now = timezone.now()
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = now.replace(hour=23, minute=59, second=59, microsecond=999)
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
    else:
        logger.warning(f'failed to create season "{name}"')


def recalculate_ratings_for_season(season):
    updated_count = 0
    matches_to_update = season.matches.filter(ran=True).count()
    ratings_to_update = season.ratings.count()

    logger = logging.getLogger("RECALCULATE_RATINGS")
    logger.info(f"Recalculating ratings for '{season.name}' '{season.id}'")
    logger.info(f"{ratings_to_update=} {matches_to_update=}")

    for rating in models.AgentRatings.objects.filter(season=season):
        rating.reset()
        rating.save()

    logger.info("Finished resetting ratings")

    for match in season.matches.filter(ran=True).order_by("ran_at"):
        update_ratings_from_match(match)
        match.save()
        updated_count += 1

        if (
            updated_count == 1
            or updated_count % 100 == 0
            or updated_count == matches_to_update
        ):
            logger.info(
                f"updated {updated_count:6d} out of {matches_to_update}  ::  {updated_count / matches_to_update * 100.0:5.2f}%"
            )

    logger.info(f"Finished recalculating rankings for season '{season.name}'")


def enqueue_all_pending_matches():
    redis = get_redis_connection("default")

    for tournament in models.Tournament.objects.all():
        pending_match_ids = tournament.matches.filter(ran=False).values_list(
            "id", flat=True
        )
        pending_match_ids = list(map(str, pending_match_ids))

        if len(pending_match_ids) == 0:
            continue

        logger.info(
            f"'{tournament.name}' had {len(pending_match_ids)} unplayed matches"
        )

        for id in pending_match_ids:
            redis.sadd(settings.MATCH_QUEUE_KEY, id)
