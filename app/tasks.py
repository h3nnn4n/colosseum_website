from celery import shared_task

from app import models, services


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
    services.automated_tournaments.create_automated_tournaments()

    for tournament in models.Tournament.objects.filter(done=False):
        services.update_tournament_state(tournament)
