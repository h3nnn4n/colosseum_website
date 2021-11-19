from django.db import transaction
from django.shortcuts import get_object_or_404
from simple_elo import compute_updated_ratings

from .. import models


def update_record_ratings(player1_id, player2_id, result):
    """
    Takes two player ids and a match result and update the player ratings
    accordingly.
    """

    # Flip around so the first player is always the winner
    if result == 0:
        return update_record_ratings(player2_id, player1_id, 1)

    with transaction.atomic():
        player1 = get_object_or_404(models.Agent, pk=player1_id)
        player2 = get_object_or_404(models.Agent, pk=player2_id)
        update_ratings(player1, player2, result)
        player1.save()
        player2.save()


def update_ratings(player1, player2, result):
    """
    Takes two player and a match result and update the player ratings
    accordingly.
    """

    # Flip around so the first player is always the winner
    if result == 0:
        return update_ratings(player2, player1, 1)

    player1_id = str(player1.name)
    player2_id = str(player2.name)

    elos = {player1_id: float(player1.elo), player2_id: float(player2.elo)}
    match_result = {(player1_id, player2_id): result}

    updated_elos = compute_updated_ratings(elos, match_result)

    if result == 1:
        player1.wins += 1
        player1.score += 1
        player2.loses += 1
    elif result == 0.5:
        player1.wins += 0.5
        player1.score += 0.5
        player2.wins += 0.5
        player2.score += 0.5

    player1.elo = updated_elos[player1_id]
    player2.elo = updated_elos[player2_id]
