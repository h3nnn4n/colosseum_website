from django.utils import timezone

from .. import models, serializers


def create_automated_tournaments():
    create_daily_tournament()


def create_daily_tournament():
    """
    Creates a timed tournament that lasts for one day. If such a tournament
    already exists it does nothing, otherwise it creates a new one.
    """
    # FIXME: This should not be hardcoded
    game = models.Game.objects.first().id

    now = timezone.now()
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = now.replace(hour=23, minute=59, second=59, microsecond=999)

    last_automated_daily_tournament = (
        models.Tournament.objects.filter(mode="TIMED", is_automated=True)
        .order_by("-automated_number")
        .first()
    )

    if last_automated_daily_tournament:
        next_number = last_automated_daily_tournament.automated_number + 1
    else:
        next_number = 1

    if last_automated_daily_tournament and last_automated_daily_tournament.is_active:
        return {"status": "active daily tournament already exists"}

    name = f"Automated Daily Tournament #{next_number}"

    data = {
        "mode": "TIMED",
        "start_date": start_date,
        "end_date": end_date,
        "game": game,
        "name": name,
        "is_automated": True,
        "automated_number": next_number,
    }
    serializer = serializers.TournamentSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
