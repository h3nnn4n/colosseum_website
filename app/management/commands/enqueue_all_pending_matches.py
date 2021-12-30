from django.core.management.base import BaseCommand

from app import services


class Command(BaseCommand):
    help = "Enqueue all unplayed matches to run. Duplicates are handled automatically."

    def handle(self, *args, **options):
        services.enqueue_all_pending_matches()
