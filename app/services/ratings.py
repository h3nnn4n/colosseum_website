from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist

from app.models import AgentRatings

from .elo import compute_updated_ratings


def update_ratings_from_match(match):
    """
    Takes a match and atomically update the participants ratings
    """
    update_elo_change_before(match)

    player1 = match.player1
    player2 = match.player2

    player1_id = str(player1.name)
    player2_id = str(player2.name)

    elos = {player1_id: float(player1.elo), player2_id: float(player2.elo)}
    match_result = {(player1_id, player2_id): float(match.result)}

    updated_elos = compute_updated_ratings(elos, match_result)

    # HACK: Not gonna lie, idk if this is even safe. Seems to be prone to race
    # conditions and record duplication because of that. Ideally we would
    # ensure that all agent / season pair have a respective AgentRating
    try:
        p1_ratings = match.player1.ratings.select_for_update().get(season=match.season)
    except ObjectDoesNotExist:
        p1_ratings = AgentRatings.objects.create(
            season=match.season, agent=match.player1, game=match.game
        )

    try:
        p2_ratings = match.player2.ratings.select_for_update().get(season=match.season)
    except ObjectDoesNotExist:
        p2_ratings = AgentRatings.objects.create(
            season=match.season, agent=match.player2, game=match.game
        )

    if match.result == 1:
        p1_ratings.wins += 1
        p1_ratings.score += 1

        p2_ratings.loses += 1
    elif match.result == 0.5:
        p1_ratings.draws += 1
        p1_ratings.score += Decimal("0.5")

        p2_ratings.draws += 1
        p2_ratings.score += Decimal("0.5")
    if match.result == 0:
        p1_ratings.loses += 1

        p2_ratings.wins += 1
        p2_ratings.score += 1

    p1_ratings.elo = updated_elos[player1_id]
    p2_ratings.elo = updated_elos[player2_id]

    p1_ratings.save()
    p2_ratings.save()

    update_elo_change_after(match)


def update_elo_change_before(match):
    match.player1.refresh_from_db()
    match.player2.refresh_from_db()

    # HACK: This is here to make sure we always have a ratings object
    match.player1.current_ratings
    match.player2.current_ratings

    p1_ratings = match.player1.ratings.get(season=match.season)
    p2_ratings = match.player2.ratings.get(season=match.season)

    player1_id = str(match.player1.id)
    player2_id = str(match.player2.id)

    match.data = {}
    match.data["elo_before"] = {}
    match.data["elo_before"][player1_id] = float(p1_ratings.elo)
    match.data["elo_before"][player2_id] = float(p2_ratings.elo)


def update_elo_change_after(match):
    match.player1.refresh_from_db()
    match.player2.refresh_from_db()

    p1_ratings = match.player1.ratings.get(season=match.season)
    p2_ratings = match.player2.ratings.get(season=match.season)

    player1_id = str(match.player1.id)
    player2_id = str(match.player2.id)

    match.data["elo_after"] = {}
    match.data["elo_after"][player1_id] = float(p1_ratings.elo)
    match.data["elo_after"][player2_id] = float(p2_ratings.elo)

    match.data["elo_change"] = {}
    match.data["elo_change"][player1_id] = (
        match.data["elo_after"][player1_id] - match.data["elo_before"][player1_id]
    )
    match.data["elo_change"][player2_id] = (
        match.data["elo_after"][player2_id] - match.data["elo_before"][player2_id]
    )
