from django.core.management.base import BaseCommand

from app.services.trophy import regen_all_trophies


class Command(BaseCommand):
    help = "Recreate trophies for all tournaments. Runs async using celery"

    def handle(self, *args, **options):
        regen_all_trophies()
