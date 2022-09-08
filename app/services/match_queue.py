import logging
from random import randint, random
from time import time

from django.conf import settings
from django_redis import get_redis_connection

from app import metrics, models


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger("MATCH_QUEUE")


def queue_size():
    redis = get_redis_connection("default")
    return redis.llen(settings.MATCH_QUEUE_KEY)


def get_next(game_name=None):
    RANDOM_MATCH_ENABLED = settings.RANDOM_MATCH_ENABLED
    RANDOM_MATCH_RATIO = settings.RANDOM_MATCH_RATIO
    use_random = RANDOM_MATCH_ENABLED and RANDOM_MATCH_RATIO > random()
    logger.info(f"get_next {RANDOM_MATCH_ENABLED=} {RANDOM_MATCH_RATIO=} {use_random=}")

    t_start = time()
    return_value = None
    n_attempts = 0

    redis = get_redis_connection("default")
    queue_length = redis.llen(settings.MATCH_QUEUE_KEY)

    while queue_length > 0:
        if redis.get("disable_next_match_api") == b"1":
            break

        queue_length = redis.llen(settings.MATCH_QUEUE_KEY)

        if use_random:
            random_index = randint(0, queue_length)
            match_id = redis.lindex(settings.MATCH_QUEUE_KEY, random_index)
            if match_id:
                redis.lrem(settings.MATCH_QUEUE_KEY, 1, match_id)
        else:
            match_id = redis.lpop(settings.MATCH_QUEUE_KEY)

        n_attempts += 1

        # Queue is empty. Nothing to do
        if not match_id:
            logger.info("queue is empty. No pending matches")
            break

        match_id = match_id.decode()

        if models.Match.objects.filter(id=match_id, ran=False).exists():
            if not game_name:
                return_value = match_id
                break
            else:
                try:
                    match_game = models.Match.objects.filter(id=match_id).values(
                        "game__name"
                    )[0]["game__name"]
                    if match_game == game_name:
                        return_value = match_id
                        break
                    else:
                        redis.rpush(settings.MATCH_QUEUE_KEY, match_id)
                except Exception as e:
                    logger.info(f"failed to verify the match game name with {e}")

    logger.info(f"took {n_attempts=} to get match")

    t_end = time()
    duration = t_end - t_start
    metrics.register_get_next_match_from_queue(duration, n_attempts)

    return return_value


def add(value):
    redis = get_redis_connection("default")
    redis.rpush(settings.MATCH_QUEUE_KEY, str(value))


def add_many(values):
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
    logger.info(f"regenerate_queue will add {len(values)} new records, had {old_size}")
    if values:
        redis.delete(queue_key)
        redis.rpush(queue_key, *values)
