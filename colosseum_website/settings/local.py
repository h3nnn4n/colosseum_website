import os

from .base import *


ENVIRONMENT = "LOCAL"

DEBUG = True

ALLOWED_HOSTS = ["*"]

if os.environ.get("INFLUXDB_DATABASE"):
    INFLUXDB_DATABASE = os.environ.get("INFLUXDB_DATABASE")
else:
    INFLUXDB_DISABLED = True
