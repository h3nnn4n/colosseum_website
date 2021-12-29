import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "colosseum_website.settings.local")

app = Celery("app")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
)

app.conf.beat_schedule = {
    "refresh_agent_count_cache": {
        "task": "app.tasks.refresh_agent_count_cache",
        "schedule": 5.0,
    },
}

app.autodiscover_tasks()
