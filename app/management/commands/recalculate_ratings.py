from django.core.management.base import BaseCommand

from app import models
from app.services import recalculate_ratings_for_season


class Command(BaseCommand):
    help = "Recalculatings ratings for a season from the played matches"

    def add_arguments(self, parser):
        parser.add_argument(
            "season_id", type=str, help="Id of the season to recalculate ratings for"
        )

    def handle(self, *args, **options):
        season_id = options.get("season_id")
        season = models.Season.objects.get(id=season_id)
        recalculate_ratings_for_season(season)
