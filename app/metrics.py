import logging
from threading import Thread

from django.conf import settings
from django.utils import timezone
from influxdb import InfluxDBClient

from app import models


logger = logging.getLogger("METRICS")


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
    thread = Thread(target=_process_points, args=(data,))
    thread.start()


def _process_points(client, data):
    try:
        client = _influxdb()
        client.write_points(data)
    except Exception:
        if getattr(settings, "INFLUXDB_FAIL_SILENTLY", True):
            logger.exception("Error while writing data points")
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
            "fields": {"value": 1},
            "measurement": "get_next_match",
            "time": timezone.now().isoformat(),
        }
    )
