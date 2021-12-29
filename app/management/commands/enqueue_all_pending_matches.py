import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django_redis import get_redis_connection

from app import models


logger = logging.getLogger("COMMAND")


class Command(BaseCommand):
    help = "Enqueue all unplayed matches to run. Duplicates are handled automatically."

    def handle(self, *args, **options):
        redis = get_redis_connection("default")

        for tournament in models.Tournament.objects.all():
            pending_match_ids = tournament.matches.filter(ran=False).values_list(
                "id", flat=True
            )
            pending_match_ids = list(map(str, pending_match_ids))

            if len(pending_match_ids) == 0:
                continue

            logger.info(
                f"'{tournament.name}' had {len(pending_match_ids)} unplayed matches"
            )

            for id in pending_match_ids:
                redis.sadd(settings.MATCH_QUEUE_KEY, id)
