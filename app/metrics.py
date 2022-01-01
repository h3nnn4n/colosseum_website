import logging
from threading import Thread

from django.conf import settings
from django.utils import timezone
from influxdb import InfluxDBClient


logger = logging.getLogger("METRICS")
INFLUXDB_DISABLED = settings.INFLUXDB_DISABLED


def _influxdb():
    return InfluxDBClient(
        settings.INFLUXDB_HOST,
        settings.INFLUXDB_PORT,
        settings.INFLUXDB_USER,
        settings.INFLUXDB_PASSWORD,
        settings.INFLUXDB_DATABASE,
        timeout=settings.INFLUXDB_TIMEOUT,
        ssl=getattr(settings, "INFLUXDB_SSL", False),
        verify_ssl=getattr(settings, "INFLUXDB_VERIFY_SSL", False),
    )


def _push_metric(data):
    if INFLUXDB_DISABLED:
        return

    if not isinstance(data, list):
        data = [data]

    thread = Thread(target=_process_points, args=(data,))
    thread.start()


def _process_points(data):
    try:
        client = _influxdb()
        client.write_points(data)
    except Exception:
        if getattr(settings, "INFLUXDB_FAIL_SILENTLY", True):
            logger.exception(f"Error while writing data points: {data}")
        else:
            raise


def register_replay(game_name):
    _push_metric(
        {
            "fields": {"count": 1},
            "measurement": "replay_uploaded",
            "tags": {"game": game_name},
            "time": timezone.now().isoformat(),
        }
    )


def register_match_played(game_name):
    _push_metric(
        {
            "fields": {"count": 1},
            "measurement": "match_played",
            "tags": {"game": game_name},
            "time": timezone.now().isoformat(),
        }
    )


def register_get_next_match():
    _push_metric(
        {
            "fields": {"count": 1},
            "measurement": "get_next_match",
            "time": timezone.now().isoformat(),
        }
    )


def register_match_duration(match):
    _push_metric(
        {
            "fields": {"value": match.duration},
            "measurement": "match_duration",
            "tags": {
                "game": match.game.name,
                "player1": match.player1.id,
                "player2": match.player2.id,
                "season": match.season.name,
                "tournament": match.tournament.name,
            },
            "time": timezone.now().isoformat(),
        }
    )


def register_match_queue_time(match):
    queue_time = (match.ran_at - match.created_at).total_seconds()

    _push_metric(
        {
            "fields": {"value": queue_time},
            "measurement": "match_queue_time",
            "tags": {
                "game": match.game.name,
                "player1": match.player1.id,
                "player2": match.player2.id,
                "season": match.season.name,
                "tournament": match.tournament.name,
            },
            "time": timezone.now().isoformat(),
        }
    )


def register_get_next_match_from_queue(time, n_attempts):
    _push_metric(
        {
            "fields": {"value": time, "n_attempts": n_attempts},
            "measurement": "get_next_match_from_queue",
            "time": timezone.now().isoformat(),
        }
    )


def register_match_played_twice():
    _push_metric(
        {
            "fields": {"value": 1},
            "measurement": "match_played_twice",
            "time": timezone.now().isoformat(),
        }
    )
