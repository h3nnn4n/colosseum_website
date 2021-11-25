import base64
import io
from datetime import timedelta

import matplotlib
import numpy as np
from django.db.models import Count
from django.db.models.functions import TruncHour
from django.http import HttpResponse
from django.utils import timezone

from . import models


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa


def matches_per_day():
    data = (
        models.Match.objects.filter(
            ran=True, ran_at__gte=timezone.now() - timedelta(days=1)
        )
        .annotate(date=TruncHour("ran_at"))
        .values("date")
        .annotate(count=Count("date"))
        .values("date", "count")
        .order_by("date")
    )

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.plot([d["date"] for d in data], [d["count"] for d in data])

    # fig.autofmt_xdate()
    ax.set_title("Matches in the last 24 hours")
    ax.set_ylabel("Count")
    ax.set_xlabel("Date")
    ax.grid(linestyle="--", linewidth=0.5, color=".25", zorder=-10)

    return _make_response(fig)


def _make_response(fig):
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    buf = io.BytesIO()
    canvas = FigureCanvasAgg(fig)
    canvas.print_png(buf)
    response = HttpResponse(buf.getvalue(), content_type="image/png")
    fig.clear()
    response["Content-Length"] = str(len(response.content))
    return response
