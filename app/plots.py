import base64
import io
from datetime import timedelta

import matplotlib
import numpy as np
from django.db.models import Count, F, FloatField, Sum
from django.db.models.functions import Cast, TruncHour, TruncMinute
from django.http import HttpResponse
from django.utils import timezone

from . import models


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa
import seaborn as sns  # noqa


def matches_per_day():
    sns.set_theme(style="whitegrid")
    sns.set_color_codes("pastel")

    data = (
        models.Match.objects.filter(
            ran=True, ran_at__gte=timezone.now() - timedelta(days=1)
        )
        .annotate(date=TruncMinute("ran_at"))
        .values("date")
        .annotate(count=Count("date"))
        .values("date", "count")
        .order_by("date")
    )

    x_ = [d["date"] for d in data]
    y_ = [d["count"] for d in data]
    x = []
    y = []

    for i in range(len(x_)):
        date = x_[i]
        count = y_[i]

        if len(x) == 0:
            x.append(date)
            y.append(count)
            continue

        date_ = x_[i - 1]
        gap = (date - date_).total_seconds()
        missing_minutes = int((gap / 60.0) - 1)

        for missing_minute in range(missing_minutes):
            x.append(date_ + timedelta(minutes=missing_minute))
            y.append(count)

        x.append(date)
        y.append(count)

    with sns.axes_style("whitegrid"):
        figure, ax = plt.subplots(figsize=(12, 8))
        sns.lineplot(x=x, y=y)

    sns.despine(top=True, right=True, left=True, bottom=True)

    ax.set_title("Matches in the last 24 hours")
    ax.set_ylabel("Matches per minute")

    figure.tight_layout()

    return _make_response(figure)


def agent_elo_plot(agent):
    sns.set_theme(style="whitegrid")
    sns.set_color_codes("pastel")

    elo_key = f"data__elo_after__{agent.id}"

    data = (
        agent.matches.filter(ran=True)
        .annotate(
            date=TruncHour("ran_at"), elo=Cast(F(elo_key), output_field=FloatField())
        )
        .values("date", elo_key)
        .annotate(mean_elo=Sum("elo") / Count("date"))
        .values("date", "mean_elo")
        .order_by("date")
    )

    x = [d["date"] for d in data]
    y = [d["mean_elo"] for d in data]

    with sns.axes_style("whitegrid"):
        figure, ax = plt.subplots(figsize=(8, 6))
        sns.lineplot(x=x, y=y)

    sns.despine(top=True, right=True, left=True, bottom=True)

    ax.set_title("Agent Elo")
    ax.set_ylabel("Elo")

    figure.tight_layout()

    return _make_response(figure)


def _make_response(fig):
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    buf = io.BytesIO()
    canvas = FigureCanvasAgg(fig)
    canvas.print_png(buf)
    response = HttpResponse(buf.getvalue(), content_type="image/png")
    fig.clear()
    response["Content-Length"] = str(len(response.content))
    return response
