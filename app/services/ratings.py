from simple_elo import compute_updated_ratings


def update_ratings(player1, player2, result):
    """
    Takes two player and a match result and update the player ratings
    accordingly. The first player is always the winner (except for draws).
    """
    elos = {player1.id: player1.elo, player2.id: player2.elo}
    match_result = {(player1.id, player2.id): result}
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

    player1.elo = updated_elos[player1.id]
    player2.elo = updated_elos[player2.id]
