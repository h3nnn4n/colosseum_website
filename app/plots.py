import base64
import io
from datetime import timedelta

import matplotlib
import numpy as np
from django.db.models import Count
from django.db.models.functions import TruncMinute
from django.http import HttpResponse
from django.utils import timezone

from . import models


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa
import seaborn as sns  # noqa


# https://stackoverflow.com/a/27681394
# def running_mean(x, N):
# cumsum = np.cumsum(np.insert(x, 0, 0))
# return (cumsum[N:] - cumsum[:-N]) / float(N)


def running_mean(data, size):
    new_data = []

    for i in range(len(data)):
        if i < size:
            x = sum(data[0:i]) / size
        else:
            x = sum(data[i - size : i]) / size
        new_data.append(x)

    return new_data


def matches_per_day():
    sns.set_theme(style="whitegrid")
    sns.set_color_codes("pastel")

    data = (
        models.Match.objects.filter(
            ran=True, ran_at__gte=timezone.now() - timedelta(days=1, hours=1)
        )
        .annotate(date=TruncMinute("ran_at"))
        .values("date")
        .annotate(count=Count("date"))
        .values("date", "count")
        .order_by("date")
    )

    # HACK: This is hacky and slow and I dont like it, but it works (for now)
    window_size = 30
    x = [d["date"] for d in data][window_size:-1]
    raw_values = [d["count"] for d in data]
    tailing_avg_values = running_mean(raw_values, window_size)[window_size:-1]
    raw_values = raw_values[window_size:-1]

    with sns.axes_style("whitegrid"):
        figure, ax = plt.subplots(figsize=(12, 8))
        sns.lineplot(x=x, y=raw_values)
        sns.lineplot(x=x, y=tailing_avg_values)

    sns.despine(top=True, right=True, left=True, bottom=True)

    ax.set_title("Matches in the last 24 hours")
    ax.set_ylabel("Matches per minute")

    figure.tight_layout()

    return _make_response(figure)


def agent_elo_plot(agent):
    sns.set_theme(style="whitegrid")
    sns.set_color_codes("pastel")

    elo_key = f"data__elo_after__{agent.id}"
    data = agent.matches.filter(ran=True).order_by("ran_at").values("ran_at", elo_key)

    # HACK: This is hacky and slow and I dont like it, but it works (for now)
    window_size = 250
    x = [d["ran_at"] for d in data][window_size:-1]
    raw_values = [d[elo_key] for d in data]
    tailing_avg_values = running_mean(raw_values, window_size)[window_size:-1]
    raw_values = raw_values[window_size:-1]

    with sns.axes_style("whitegrid"):
        figure, ax = plt.subplots(figsize=(8, 6))
        sns.lineplot(x=x, y=raw_values)
        sns.lineplot(x=x, y=tailing_avg_values)

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
