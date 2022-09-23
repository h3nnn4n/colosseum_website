import csv

from django.core.management.base import BaseCommand

from app import models


class Command(BaseCommand):
    help = "List all participants from a season, by ratings"

    def add_arguments(self, parser):
        parser.add_argument(
            "season_id", type=str, help="Season ID to list the ratings for"
        )

    def handle(self, *args, **options):
        season_id = options.get("season_id")
        season = models.Season.objects.get(id=season_id)

        filename = f"{season.name}_rankings.csv"
        self.stdout.write(
            f"Listing ratings for season {season.name} {season.id} to {filename=}"
        )

        ratings = season.ratings.all().order_by("-elo")

        with open(filename, "wt") as f:
            writer = csv.writer(f)

            writer.writerow(
                [
                    "elo",
                    "name",
                    "agent_id",
                    "agent_created_at",
                    "username",
                    "email",
                    "user_id",
                    "is_admin",
                ]
            )

            for rating in ratings:
                writer.writerow(
                    [
                        rating.elo,
                        rating.agent.name,
                        rating.agent.id,
                        rating.agent.created_at,
                        rating.agent.owner.username,
                        rating.agent.owner.email,
                        rating.agent.owner.id,
                        rating.agent.owner.is_staff or rating.agent.owner.is_superuser,
                    ]
                )

        self.stdout.write("Done")
