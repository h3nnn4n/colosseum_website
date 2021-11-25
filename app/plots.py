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

    with sns.axes_style("whitegrid"):
        figure, ax = plt.subplots(figsize=(12, 8))
        sns.lineplot(x=[d["date"] for d in data], y=[d["count"] for d in data])

    sns.despine(top=True, right=True, left=True, bottom=True)

    ax.set_title("Matches in the last 24 hours")
    ax.set_ylabel("Matches per minute")

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
