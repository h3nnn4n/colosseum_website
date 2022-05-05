from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv


load_dotenv()


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
    "heartbeat": {
        "task": "app.tasks.heartbeat",
        "schedule": 1.0,
    },
    "automated_manager": {
        "task": "app.tasks.automated_manager",
        "schedule": 10.0,
    },
    "metrics_logger": {
        "task": "app.tasks.metrics_logger",
        "schedule": 5.0,
    },
    "regenerate_queue": {
        "task": "app.tasks.regenerate_queue",
        "schedule": crontab(minute="*/5"),  # Every 5th minute
    },
}

app.autodiscover_tasks()
