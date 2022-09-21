from .base import *  # noqa


ENVIRONMENT = "CODECON"

ALLOWED_HOSTS = ["*"]

DEBUG = False

# This shouldn't be hardcoded, but such is life
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
