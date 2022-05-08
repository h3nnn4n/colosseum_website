from collections import defaultdict

from django.db.models import Count

from app.models import Tournament, Trophy


PLACE_TO_TROPHY_TYPE = {
    1: "FIRST",
    2: "SECOND",
    3: "THIRD",
}


def trophies_for_agent(agent):
    trophies = (
        agent.trophies.values("type").annotate(total=Count("type")).order_by("total")
    )

    data = {
        "FIRST": 0,
        "SECOND": 0,
        "THIRD": 0,
    }

    for trophy in trophies:
        trophy_type = trophy["type"]
        data[trophy_type] = trophy["total"]

    return data


def create_trophies(tournament):
    if not tournament.done:
        raise ValueError(
            f"Tournament {tournament.id} is not done. "
            "Can only create trophies for tournaments that are complete"
        )

    if tournament.pending_matches_count > 0:
        raise ValueError(f"Complete tournament {tournament.id} has pending matches")

    results = tournament.ratings
    top_3_scores = sorted([result.score for result in results], reverse=True)[:3]
    rankings = defaultdict(list)

    for result in results:
        rankings[result.score].append(result.agent)

    for place, score in enumerate(top_3_scores):
        trophy_type = PLACE_TO_TROPHY_TYPE[place + 1]

        for agent in rankings[score]:
            Trophy.objects.create(
                agent=agent,
                game=tournament.game,
                season=tournament.season,
                tournament=tournament,
                type=trophy_type,
            )


def backfill_missing_trophies():
    tournaments = (
        Tournament.objects.filter(done=True)
        .annotate(stuff=Count("trophies__id"))
        .only("id")
        .filter(stuff=0)
    )

    print(f"backfilling {tournaments.count()} tournaments with trophies")

    for tournament in tournaments:
        try:
            create_trophies(tournament)
        except ValueError as e:
            print(
                f"failed to create trophies for tournament {tournament} with error: {e}"
            )
