import logging

from django.conf import settings
from django.utils import timezone

from app import models, tasks
from app.services.ratings import update_ratings_from_match
from app.services.trophy import create_trophies


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("SERVICES")


def purge_all_agents():
    models.Agent.objects.all().delete()


def purge_all_played_games():
    for agent in models.Agent.objects.all():
        agent.current_ratings.delete()

    models.Match.objects.all().delete()


def purge_all_tournaments():
    models.Tournament.objects.all().delete()
    models.Match.objects.all().delete()


def update_tournaments_state():
    for tournament in models.Tournament.objects.all():
        update_tournament_state(tournament)

    tasks.regenerate_queue.delay()


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

    if tournament.done and not tournament.has_pending_matches:
        """
        This is important for timed tournaments, since they may be "done", in
        the sense that the time window for it has passed, but there may be
        pending matches to be played.  These matches were created before the
        tournament was marked as done.
        """
        create_trophies(tournament)


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


def metrics_api_handler(payload):
    """
    Parses an api request to push a metric
    """
    # FIXME: Accepting just single items for now. Needs to support multiple
    # ones too
    if not isinstance(payload, dict):
        raise TypeError(f"Payload must be a dict. Was {type(payload)}")

    if not payload.get("time"):
        payload["time"] = timezone.now().isoformat()

    if not payload.get("tags"):
        payload["tags"] = {}

    payload["tags"]["metric_api"] = True

    tasks.push_metric.delay([payload])
