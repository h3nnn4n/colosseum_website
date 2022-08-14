from .base import *  # noqa


ENVIRONMENT = "TESTING"

DEBUG = False

INFLUXDB_DISABLED = True
INFLUXDB_USE_CELERY = False
INFLUXDB_USE_THREADING = True
CELERY_TASK_ALWAYS_EAGER = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO",
        }
    },
}
