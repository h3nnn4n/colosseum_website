import logging

from django.conf import settings
from django.utils import timezone
from django_redis import get_redis_connection

from app import metrics, models, services
from app.celery import app as celery
from app.services import automated_seasons, automated_tournaments, match_queue


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("TASKS")


@celery.task
def _push_metric(data):
    from app import metrics

    metrics._process_points(data)


@celery.task
def push_metric(data):
    from app import metrics

    metrics.push_metric(data)


@celery.task
def automated_manager():
    """
    Creates things automatically
    """
    automated_seasons.update_seasons_state()
    automated_seasons.create_automated_seasons()
    automated_tournaments.create_automated_tournaments()

    for tournament in models.Tournament.objects.filter(done=False):
        services.update_tournament_state(tournament)


@celery.task
def metrics_logger():
    """
    Periodically collect and send some metrics to influxdb
    """
    metrics.push_metric(
        {
            "fields": {"value": int(match_queue.queue_size())},
            "measurement": "match_queue_size",
            "time": timezone.now().isoformat(),
        }
    )

    unplayed_matches_count = models.Match.objects.filter(ran=False).count()
    metrics.push_metric(
        {
            "fields": {"value": int(unplayed_matches_count)},
            "measurement": "unplayed_matches_count",
            "time": timezone.now().isoformat(),
        }
    )

    oldest_unplayed_match = (
        models.Match.objects.filter(ran=False).order_by("created_at").first()
    )
    oldest_unplayed_match_age = 0.0
    if oldest_unplayed_match:
        oldest_unplayed_match_age = (
            timezone.now() - oldest_unplayed_match.created_at
        ).total_seconds()

    metrics.push_metric(
        {
            "fields": {"value": float(oldest_unplayed_match_age)},
            "measurement": "oldest_unplayed_match_age",
            "time": timezone.now().isoformat(),
        }
    )

    time_since_last_celery_heartbeat = services.get_time_since_last_celery_heartbeat()
    time_since_last_colosseum_heartbeat = (
        services.get_time_since_last_colosseum_heartbeat()
    )

    if time_since_last_celery_heartbeat is not None:
        metrics.push_metric(
            {
                "fields": {"value": time_since_last_celery_heartbeat},
                "measurement": "time_since_last_celery_heartbeat",
            },
        )

    if time_since_last_colosseum_heartbeat is not None:
        metrics.push_metric(
            {
                "fields": {"value": time_since_last_colosseum_heartbeat},
                "measurement": "time_since_last_colosseum_heartbeat",
            },
        )


@celery.task
def regenerate_queue():
    match_queue.regenerate_queue()


@celery.task
def heartbeat():
    """
    Simple heart beat for celery. Stores the time at which this function runs
    on redis, so we can check later if redis is running.
    """
    redis = get_redis_connection("default")
    heartbeat_key = settings.CELERY_HEARTBEAT_KEY
    redis.set(heartbeat_key, timezone.now().isoformat())


@celery.task
def create_trophies(tournament_id):
    tournament = models.Tournament.objects.get(id=tournament_id)
    logger.info(f"Creating trophies for {tournament.id} {tournament.name}")
    services.trophy.create_trophies(tournament)
