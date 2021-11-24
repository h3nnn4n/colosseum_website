from django.utils import timezone

from .. import models, serializers


def create_automated_tournaments():
    _create_automated_tournament("Automated Daily Tournament #{}", "TIMED")
    _create_automated_tournament("Automated Round Robin Tournament #{}", "ROUND_ROBIN")
    _create_automated_tournament(
        "Automated Double Round Robin Tournament #{}", "DOUBLE_ROUND_ROBIN"
    )
    _create_automated_tournament(
        "Automated Triple Round Robin Tournament #{}", "TRIPLE_ROUND_ROBIN"
    )


def _create_automated_tournament(name, mode):
    """
    Creates an automated tournament. If such a tournament already exists it
    does nothing, otherwise it creates a new one.
    """
    # FIXME: This should not be hardcoded
    game = models.Game.objects.first().id

    now = timezone.now()
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = now.replace(hour=23, minute=59, second=59, microsecond=999)

    last_automated_tournament = (
        models.Tournament.objects.filter(mode=mode, is_automated=True)
        .order_by("-automated_number")
        .first()
    )

    if last_automated_tournament:
        next_number = last_automated_tournament.automated_number + 1
    else:
        next_number = 1

    if last_automated_tournament and last_automated_tournament.is_active:
        return {"status": "active tournament already exists"}

    name = name.format(next_number)

    data = {
        "mode": mode,
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
