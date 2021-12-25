from decimal import Decimal

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
        update_ratings(player1, player2, result, save=True)


def update_ratings(player1, player2, result, save=False):
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
    match_result = {(player1_id, player2_id): float(result)}

    updated_elos = compute_updated_ratings(elos, match_result)
    p1_ratings = player1.current_ratings
    p2_ratings = player2.current_ratings

    if result == 1:
        p1_ratings.wins += 1
        p1_ratings.score += 1
        p2_ratings.loses += 1
    elif result == 0.5:
        p1_ratings.draws += 1
        p1_ratings.score += Decimal("0.5")
        p2_ratings.draws += 1
        p2_ratings.score += Decimal("0.5")

    p1_ratings.elo = updated_elos[player1_id]
    p2_ratings.elo = updated_elos[player2_id]

    if save:
        p1_ratings.save()
        p2_ratings.save()


def update_elo_change_before(match):
    match.player1.refresh_from_db()
    match.player2.refresh_from_db()

    player1_id = str(match.player1.id)
    player2_id = str(match.player2.id)

    match.data = {}
    match.data["elo_before"] = {}
    match.data["elo_before"][player1_id] = float(match.player1.elo)
    match.data["elo_before"][player2_id] = float(match.player2.elo)


def update_elo_change_after(match):
    match.player1.refresh_from_db()
    match.player2.refresh_from_db()

    player1_id = str(match.player1.id)
    player2_id = str(match.player2.id)

    match.data["elo_after"] = {}
    match.data["elo_after"][player1_id] = float(match.player1.elo)
    match.data["elo_after"][player2_id] = float(match.player2.elo)

    match.data["elo_change"] = {}
    match.data["elo_change"][player1_id] = (
        match.data["elo_after"][player1_id] - match.data["elo_before"][player1_id]
    )
    match.data["elo_change"][player2_id] = (
        match.data["elo_after"][player2_id] - match.data["elo_before"][player2_id]
    )
