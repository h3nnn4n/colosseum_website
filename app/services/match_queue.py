import logging
from time import time

from django.conf import settings
from django_redis import get_redis_connection

from app import metrics, models


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("MATCH_QUEUE")


def queue_size():
    redis = get_redis_connection("default")
    return redis.llen(settings.MATCH_QUEUE_KEY)


def get_next():
    t_start = time()
    return_value = None

    redis = get_redis_connection("default")
    while True:
        if redis.get("disable_next_match_api") == b"1":
            break

        match_id = redis.lpop(settings.MATCH_QUEUE_KEY)

        # Queue is empty. Nothing to do
        if not match_id:
            break

        match_id = match_id.decode()

        if models.Match.objects.filter(id=match_id, ran=False).exists():
            return_value = match_id

    t_end = time()
    duration = t_end - t_start
    metrics.register_get_next_match_from_queue(duration)

    return return_value


def add(value):
    redis = get_redis_connection("default")
    redis.rpush(settings.MATCH_QUEUE_KEY, str(value))


def add_many(*values):
    if values:
        redis = get_redis_connection("default")
        redis.rpush(settings.MATCH_QUEUE_KEY, *list(map(str, values)))


def regenerate_queue():
    """
    Gets all unplayed matches from the database, sort them by age and overrides
    the current queue with it. Since the queue is supposed to only have
    unplayed matches, this shouldn't result in any lost records.
    """
    redis = get_redis_connection("default")
    queue_key = settings.MATCH_QUEUE_KEY
    old_size = queue_size()

    pending_records_ids = (
        models.Match.objects.filter(ran=False)
        .order_by("created_at")
        .values_list("id", flat=True)
    )

    values = list(map(str, pending_records_ids))
    logger.info(
        f"regenerate_queue will add {len(values)} new records. previously has {old_size}"
    )
    if values:
        redis.delete(queue_key)
        redis.rpush(queue_key, *values)
