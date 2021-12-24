from django.core.management.base import BaseCommand, CommandError
from django_redis import get_redis_connection


class Command(BaseCommand):
    help = "Manages the get_next_match killswitch"

    def add_arguments(self, parser):
        parser.add_argument(
            "--enable",
            action="store_true",
            help="Disabled the killswitch, allowing new matches to be played.",
        )
        parser.add_argument(
            "--disable",
            action="store_true",
            help="Enables the killswitch, preventing further matches from being played.",
        )

    def handle(self, *args, **options):
        enable = options.get("enable", False)
        disable = options.get("disable", False)

        if enable and disable:
            raise CommandError("Please only use --enable or --disable")

        if not enable and not disable:
            raise CommandError("Please use --enable or --disable or check --help")

        redis = get_redis_connection("default")

        if enable:
            redis.set("disable_next_match_api", 1)

        if disable:
            redis.set("disable_next_match_api", 0)
