from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django_redis import get_redis_connection

from app import metrics, models, services
from app.services import automated_tournaments


@shared_task
def refresh_agent_count_cache():
    """
    This task refreshes the cache for "games_played_count" to stay warm.  This
    significantly improves response times for the agent api and index view.
    """
    for agent in models.Agent.objects.all():
        agent.games_played_count


@shared_task
def automated_manager():
    """
    Creates things automatically
    """
    services.update_seasons_state()
    services.create_automated_seasons()
    automated_tournaments.create_automated_tournaments()

    for tournament in models.Tournament.objects.filter(done=False):
        services.update_tournament_state(tournament)


@shared_task
def metrics_logger():
    """
    Periodically collect and send some metrics to influxdb
    """
    redis = get_redis_connection("default")
    queue_size = redis.scard(settings.MATCH_QUEUE_KEY)
    metrics._push_metric(
        {
            "fields": {"value": queue_size},
            "measurement": "match_queue_size",
            "time": timezone.now().isoformat(),
        }
    )

    unplayed_matches_count = models.Match.objects.filter(ran=False).count()
    metrics._push_metric(
        {
            "fields": {"value": unplayed_matches_count},
            "measurement": "unplayed_matches_count",
            "time": timezone.now().isoformat(),
        }
    )
