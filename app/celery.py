from celery import Celery
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
    "refresh_agent_count_cache": {
        "task": "app.tasks.refresh_agent_count_cache",
        "schedule": 5.0,
    },
    "update_tournaments_state": {
        "task": "app.tasks.update_tournaments_state",
        "schedule": 5.0,
    },
}

app.autodiscover_tasks()
