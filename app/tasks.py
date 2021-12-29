from celery import shared_task

from app import models


@shared_task
def refresh_agent_count_cache():
    """
    This task refreshes the cache for "games_played_count" to stay warm.  This
    significantly improves response times for the agent api and index view.
    """
    for agent in models.Agent.objects.all():
        agent.games_played_count
