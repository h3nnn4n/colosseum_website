"""
Django settings for colosseum_website project.

Generated by 'django-admin startproject' using Django 3.2.9.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

import os
import socket
import sys
from pathlib import Path

import dj_database_url
import sentry_sdk
from decouple import config
from dotenv import load_dotenv
from sentry_sdk.integrations.django import DjangoIntegration


load_dotenv()


sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True,
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

sys.modules["fontawesome_free"] = __import__("fontawesome-free")

DEFAULT_KEY = "django-insecure-y5lc8xiuknt^u=x8ugmo9!5xwoug!m9^b1-)+mx08i&e9jfj$x"
SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_KEY)

DEBUG = False

ALLOWED_HOSTS = []

SITE_ID = 1

_BASE_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "bootstrap4",
    "rest_framework",
    "rest_framework.authtoken",
    "crispy_forms",
    "django_extensions",
    "memoize",
    "debug_toolbar",
    "fontawesome_free",
    "app",
]

_WIKI_APPS = [
    "django.contrib.sites.apps.SitesConfig",
    "django.contrib.humanize.apps.HumanizeConfig",
    "django_nyt.apps.DjangoNytConfig",
    "mptt",
    "sekizai",
    "sorl.thumbnail",
    "wiki.apps.WikiConfig",
    "wiki.plugins.attachments.apps.AttachmentsConfig",
    "wiki.plugins.notifications.apps.NotificationsConfig",
    "wiki.plugins.images.apps.ImagesConfig",
    "wiki.plugins.macros.apps.MacrosConfig",
]

INSTALLED_APPS = _BASE_APPS + _WIKI_APPS

MIDDLEWARE = [
    "app.middleware.InfluxDBRequestMiddleware",
    "django_cprofile_middleware.middleware.ProfilerMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = "colosseum_website.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            str(BASE_DIR.joinpath("templates")),
            str(BASE_DIR.joinpath("app/templates")),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.contrib.messages.context_processors.messages",
                "sekizai.context_processors.sekizai",
            ]
        },
    }
]

TEMPLATE_DIRS = (os.path.join(BASE_DIR, "templates"),)

WSGI_APPLICATION = "colosseum_website.wsgi.application"


DATABASES = {
    "default": dj_database_url.config(
        default="postgres://postgres:postgres@localhost/postgres"
    )
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"
STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = "/static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


LOGIN_REDIRECT_URL = "/home/"
LOGOUT_REDIRECT_URL = "/home/"


CRISPY_TEMPLATE_PACK = "bootstrap4"


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication"
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAdminUser"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"": {"handlers": ["console"], "level": "INFO"}},
}


SHELL_PLUS = "ipython"

DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME")
AWS_REGION = os.environ.get("AWS_REGION", "eu-east-1")

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

INTERNAL_IPS = ["127.0.0.1"]


# InfluxDB settings
INFLUXDB_HOST = os.environ.get("INFLUXDB_HOST")
INFLUXDB_PORT = os.environ.get("INFLUXDB_PORT")
INFLUXDB_USER = os.environ.get("INFLUXDB_USER")
INFLUXDB_PASSWORD = os.environ.get("INFLUXDB_PASSWORD")
INFLUXDB_DATABASE = os.environ.get("INFLUXDB_DATABASE")
INFLUXDB_TAGS_HOST = socket.gethostname()
INFLUXDB_TIMEOUT = os.environ.get("INFLUXDB_TIMEOUT", 5)
INFLUXDB_DISABLED = config("INFLUXDB_DISABLED", default=False, cast=bool)
INFLUXDB_USE_CELERY = config("INFLUXDB_USE_CELERY", default=True, cast=bool)
INFLUXDB_USE_THREADING = config("INFLUXDB_USE_THREADING", default=False, cast=bool)


RANDOM_MATCH_ENABLED = os.environ.get("RANDOM_MATCH_ENABLED") == "true"
RANDOM_MATCH_RATIO = float(os.environ.get("RANDOM_MATCH_RATIO", 0.5))
MATCH_QUEUE_KEY = "match_queue"


DJANGO_CPROFILE_MIDDLEWARE_REQUIRE_STAFF = False

DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda r: False}

WIKI_ACCOUNT_SIGNUP_ALLOWED = False

# Celery stuff
CELERY_TASK_ALWAYS_EAGER = False
CELERY_WORKER_CONCURRENCY = config("CELERY_WORKER_CONCURRENCY", 2, cast=int)
CELERY_WORKER_PREFETCH_MULTIPLIER = config(
    "CELERY_WORKER_PREFETCH_MULTIPLIER", 1, cast=int
)
CELERY_BROKER_URL = os.environ.get("CELERY_REDIS_URL")
