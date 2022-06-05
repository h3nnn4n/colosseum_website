import logging
from collections import defaultdict

from django.conf import settings
from django.db import IntegrityError
from django.db.models import Count

from app import tasks
from app.models import SeasonTrophies, Tournament, Trophy


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("TROPHY_SERVICE")


PLACE_TO_TROPHY_TYPE = {
    1: "FIRST",
    2: "SECOND",
    3: "THIRD",
}


TROPHY_TYPE_TO_PLACE = {
    "FIRST": 1,
    "SECOND": 2,
    "THIRD": 3,
}


def trophies_for_season(season):
    data = {}

    for trophy in season.trophies.all():
        if trophy.agent_id not in data.keys():
            data[trophy.agent_id] = SeasonTrophies(trophy.agent)

        match trophy.type:
            case "FIRST":
                data[trophy.agent_id].first_places += 1
            case "SECOND":
                data[trophy.agent_id].second_places += 1
            case "THIRD":
                data[trophy.agent_id].third_places += 1

    rankings = sorted((data.values()), reverse=True, key=lambda t: t.trophy_score)

    return rankings


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

    if tournament.trophies.count() > 0:
        logger.warning(
            f"Tournament {tournament.id} had {tournament.trophies.count()} trophies. Recreating them"
        )
        tournament.trophies.all().delete()

    results = tournament.ratings
    top_3_scores = sorted([result.score for result in set(results)], reverse=True)[:3]
    rankings = defaultdict(list)

    for result in results:
        rankings[result.score].append(result.agent)

    for place, score in enumerate(top_3_scores):
        trophy_type = PLACE_TO_TROPHY_TYPE[place + 1]

        for agent in rankings[score]:
            try:
                Trophy.objects.create(
                    agent=agent,
                    game=tournament.game,
                    season=tournament.season,
                    tournament=tournament,
                    type=trophy_type,
                )
            except IntegrityError as e:
                logger.warning(
                    f"failed to generate trophy for {agent.id=} {tournament.id=} with error: {e}"
                )


def backfill_missing_trophies():
    tournaments = (
        Tournament.objects.filter(done=True)
        .annotate(stuff=Count("trophies__id"))
        .only("id")
        .filter(stuff=0)
    )

    count = tournaments.count()

    print(f"backfilling {count} tournaments with trophies")

    for index, tournament in enumerate(tournaments):
        try:
            create_trophies(tournament)
            print(f"{index} / {count} : {tournament.id=}")
        except ValueError as e:
            print(
                f"failed to create trophies for tournament {tournament} with error: {e}"
            )


def regen_all_trophies():
    for tournament in Tournament.objects.filter(done=True).iterator():
        tasks.create_trophies.delay(tournament.id)
