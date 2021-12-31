from django.conf import settings
from django_redis import get_redis_connection

from app import models


def queue_size():
    redis = get_redis_connection("default")
    return redis.scard(settings.MATCH_QUEUE_KEY)


def get_next():
    redis = get_redis_connection("default")
    if redis.get("disable_next_match_api") == b"1":
        return

    while True:
        match_id = redis.spop(settings.MATCH_QUEUE_KEY)

        # Queue is empty. Nothing to do
        if not match_id:
            return

        match_id = match_id.decode()

        if models.Match.objects.filter(id=match_id, ran=False).exists():
            return match_id


def add(value):
    redis = get_redis_connection("default")
    redis.sadd(settings.MATCH_QUEUE_KEY, str(value))


def add_many(*values):
    redis = get_redis_connection("default")
    for value in values:
        redis.sadd(settings.MATCH_QUEUE_KEY, str(value))
