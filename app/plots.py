import io
from datetime import timedelta

import matplotlib
from django.db.models import Count
from django.db.models.functions import TruncMinute
from django.http import HttpResponse
from django.utils import timezone

from . import models


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa
import seaborn as sns  # noqa


def plot_matches_per_day(trailing_average_n=15):
    end_date = timezone.now()
    start_date = end_date - timedelta(days=1)

    data = (
        models.Match.objects.filter(ran=True, ran_at__gte=start_date)
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
    y_ta = []
    trailing_average_queue = []

    for i in range(len(x_)):
        date = x_[i]
        count = y_[i]

        # Fill the beginning of the series
        if len(x) == 0:
            gap = (date - start_date).total_seconds()
            missing_minutes = int((gap / 60.0) - 1)

            for missing_minute in range(missing_minutes):
                x.append(start_date + timedelta(minutes=missing_minute))
                y.append(0)

            x.append(date)
            y.append(count)
            continue

        # Fill the mid of the series
        date_ = x_[i - 1]
        gap = (date - date_).total_seconds()
        missing_minutes = int((gap / 60.0) - 1)

        for missing_minute in range(missing_minutes):
            x.append(date_ + timedelta(minutes=missing_minute))
            y.append(0)

        x.append(date)
        y.append(count)

    # Fill end of the series
    last_date = x[-1]
    gap = (end_date - last_date).total_seconds()
    missing_minutes = int((gap / 60.0) - 1)

    for missing_minute in range(missing_minutes):
        x.append(last_date + timedelta(minutes=missing_minute))
        y.append(0)

    for point in y:
        trailing_average_queue.append(point)

        if len(trailing_average_queue) > trailing_average_n:
            trailing_average_queue.pop(0)

        y_ta.append((sum(trailing_average_queue) / len(trailing_average_queue)))

    return _matches_per_day_plot(x, y, y_ta)


def _matches_per_day_plot(x, y, y_ta):
    palette = ["#4cc9f0", "#3f37c9"]
    sns.set_theme(style="whitegrid")
    sns.set_color_codes("pastel")
    sns.axes_style("whitegrid")
    sns.set_palette(palette)

    figure, ax = plt.subplots(figsize=(12, 8))
    sns.lineplot(x=x, y=y, estimator=None)
    sns.lineplot(x=x, y=y_ta, estimator=None)

    sns.despine(top=True, right=True, left=True, bottom=True)

    ax.set_title("Matches in the last 24 hours")
    ax.set_ylabel("Matches per minute")

    figure.tight_layout()

    return _make_response(figure)


def plot_agent_elo(agent):
    elo_key = f"data__elo_after__{agent.id}"

    current_season = models.Season.objects.current_season()

    data = (
        agent.matches.filter(ran=True, season=current_season)
        .values("ran_at", elo_key)
        .order_by("ran_at")
    )

    x = [d["ran_at"] for d in data]
    y = [d[elo_key] for d in data]

    return _agent_elo_plot(x, y)


def _agent_elo_plot(x, y):
    sns.set_theme(style="whitegrid")
    sns.set_color_codes("pastel")

    with sns.axes_style("whitegrid"):
        figure, ax = plt.subplots(figsize=(8, 6))
        sns.lineplot(x=x, y=y, estimator=None)

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
