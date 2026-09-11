from collections.abc import Mapping
from collections.abc import Sequence

import altair as alt
import pandas as pd

from app.resources import DailyCount
from app.resources import LabelCount

_ACCENT = "#b48cff"
_PALETTE = [
    "#b48cff",
    "#7b3fe4",
    "#ff9db0",
    "#7ee2b0",
    "#ffd58a",
    "#7cc7ff",
    "#f3ecff",
    "#c58cff",
    "#ff5c78",
    "#48c78e",
    "#ffbe50",
    "#4a1d8f",
]


def _base(chart: alt.Chart, title: str) -> alt.Chart:
    return (
        chart.properties(title=title, height=260)
        .configure(background="transparent")
        .configure_view(strokeOpacity=0)
        .configure_axis(
            labelColor="#b9a6e6",
            titleColor="#b9a6e6",
            gridColor="#2a2040",
            domainOpacity=0,
        )
        .configure_title(color="#ece4ff", fontSize=14, anchor="start")
        .configure_legend(labelColor="#b9a6e6", titleColor="#b9a6e6")
    )


def daily(series: Sequence[DailyCount], title: str, colour: str = _ACCENT) -> alt.Chart:
    frame = pd.DataFrame(
        {"day": [row.day for row in series], "count": [row.count for row in series]}
    )

    area = (
        alt.Chart(frame)
        .mark_area(
            line={"color": colour},
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color=colour, offset=0),
                    alt.GradientStop(color="#0b0716", offset=1),
                ],
                x1=1,
                x2=1,
                y1=1,
                y2=0,
            ),
            opacity=0.75,
            interpolate="monotone",
        )
        .encode(
            x=alt.X("day:T", title=None),
            y=alt.Y("count:Q", title=None),
            tooltip=["day:T", "count:Q"],
        )
    )

    return _base(area, title)


def bars(
    series: Sequence[LabelCount], title: str, labels: Mapping[int, str]
) -> alt.Chart:
    frame = pd.DataFrame(
        {
            "label": [labels.get(row.label, str(row.label)) for row in series],
            "count": [row.count for row in series],
        }
    )
    order = list(frame["label"])

    chart = (
        alt.Chart(frame)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("label:N", title=None, sort=order),
            y=alt.Y("count:Q", title=None),
            color=alt.Color(
                "label:N", legend=None, scale=alt.Scale(range=_PALETTE), sort=order
            ),
            tooltip=["label:N", "count:Q"],
        )
    )

    return _base(chart, title)


def hours(series: Sequence[LabelCount], title: str) -> alt.Chart:
    counts = {row.label: row.count for row in series}

    frame = pd.DataFrame(
        {"hour": list(range(24)), "count": [counts.get(hour, 0) for hour in range(24)]}
    )

    chart = (
        alt.Chart(frame)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=_ACCENT)
        .encode(
            x=alt.X("hour:O", title="hour (UTC)"),
            y=alt.Y("count:Q", title=None),
            tooltip=["hour:O", "count:Q"],
        )
    )

    return _base(chart, title)
