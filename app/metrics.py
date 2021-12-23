import influxdb_metrics
from django.utils import timezone

from app import models


def _push_metric(data):
    # influxdb_metrics.utils.write_points([data])
    pass


def register_replay():
    _push_metric(
        {
            "measurement": "replay_uploaded",
            "time": timezone.now().isoformat(),
            "fields": {"count": 1},
        }
    )


def register_match_played():
    _push_metric(
        {
            "measurement": "match_played",
            "time": timezone.now().isoformat(),
            "fields": {"count": 1},
        }
    )
