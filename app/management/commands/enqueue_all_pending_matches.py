from django.core.management.base import BaseCommand

from app.services import match_queue


class Command(BaseCommand):
    help = "Enqueue all unplayed matches to run. Duplicates are handled automatically."

    def handle(self, *args, **options):
        match_queue.regenerate_queue()
