from collections.abc import Mapping
from collections.abc import Sequence

import altair as alt
import pandas as pd
from poltergeist_core.resources import DailyCount
from poltergeist_core.resources import LabelCount

_ACCENT = "#b48cff"
_PALETTE = [
    "#b48cff",
    "#7cc7ff",
    "#7ee2b0",
    "#ffd58a",
    "#ff9db0",
    "#e0b3ff",
    "#78d9ec",
    "#ff8bcb",
    "#9f8cc9",
    "#ece4ff",
    "#7b3fe4",
    "#4a1d8f",
]


type Figure = alt.Chart | alt.LayerChart


def _base(chart: Figure, title: str) -> Figure:
    return (
        chart.properties(title=title, height=260)
        .configure(background="transparent")
        .configure_view(strokeOpacity=0)
        .configure_axis(
            labelColor="#9f8cc9",
            titleColor="#9f8cc9",
            gridColor="#2c2447",
            domainOpacity=0,
        )
        .configure_title(color="#ece4ff", fontSize=14, anchor="start")
        .configure_legend(labelColor="#9f8cc9", titleColor="#9f8cc9")
    )


def daily(series: Sequence[DailyCount], title: str, colour: str = _ACCENT) -> Figure:
    frame = pd.DataFrame(
        {"day": [row.day for row in series], "count": [row.count for row in series]}
    )

    base = alt.Chart(frame).encode(
        x=alt.X("day:T", title=None),
        y=alt.Y("count:Q", title=None),
        tooltip=["day:T", "count:Q"],
    )
    area = base.mark_area(color=colour, opacity=0.18, interpolate="monotone")
    line = base.mark_line(color=colour, strokeWidth=2, interpolate="monotone")

    layered = alt.layer(area, line)
    assert isinstance(layered, alt.LayerChart)

    return _base(layered, title)


def bars(series: Sequence[LabelCount], title: str, labels: Mapping[int, str]) -> Figure:
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


def hours(series: Sequence[LabelCount], title: str) -> Figure:
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
