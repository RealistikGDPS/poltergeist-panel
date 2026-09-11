from dataclasses import dataclass
from datetime import date
from datetime import timedelta

import pandas as pd
import streamlit as st

from app.resources import CreatorRow
from app.resources import DailyCount
from app.resources import LabelCount
from app.resources import ModAction
from app.resources import Totals
from app.services import AbstractContext
from app.utilities import clock
from panel import charts
from panel import components
from panel import labels
from panel import runtime
from panel import theme

_WINDOWS = {"7 days": 7, "30 days": 30, "90 days": 90, "1 year": 365}
_RECENT_EVENTS = 12


@dataclass(frozen=True, slots=True)
class Overview:
    totals: Totals
    registrations: list[DailyCount]
    active: list[DailyCount]
    uploads: list[DailyCount]
    comments: list[DailyCount]
    actions: list[DailyCount]
    hours: list[LabelCount]
    difficulties: list[LabelCount]
    stars: list[LabelCount]
    lengths: list[LabelCount]
    creators: list[CreatorRow]
    events: list[ModAction]
    actor_names: dict[int, str]


@dataclass(frozen=True, slots=True)
class Trend:
    """A series over a window, with the change against the window before."""

    current: list[DailyCount]
    delta: int
    sparkline: list[int]


async def _load(ctx: AbstractContext, days: int) -> Overview:
    events = await ctx.mod_actions.list_recent(
        user_id=None, target_type=None, target_id=None, page=0, size=_RECENT_EVENTS
    )
    actors = await ctx.users.find_many_by_ids(list({event.user_id for event in events}))

    return Overview(
        totals=await ctx.analytics.totals(),
        registrations=await ctx.analytics.registrations_per_day(days * 2),
        active=await ctx.analytics.active_users_per_day(days * 2),
        uploads=await ctx.analytics.uploads_per_day(days * 2),
        comments=await ctx.analytics.comments_per_day(days * 2),
        actions=await ctx.analytics.mod_actions_per_day(days * 2),
        hours=await ctx.analytics.comments_per_hour(days),
        difficulties=await ctx.analytics.difficulty_distribution(),
        stars=await ctx.analytics.stars_distribution(),
        lengths=await ctx.analytics.length_distribution(),
        creators=await ctx.analytics.top_creators(10),
        events=events,
        actor_names={user.id: user.username for user in actors},
    )


def _trend(series: list[DailyCount], days: int) -> Trend:
    """Splits a double-length series into the window and the one before it."""

    today = clock.now().date()
    boundary: date = today - timedelta(days=days)
    current = [row for row in series if row.day > boundary]
    previous = sum(row.count for row in series if row.day <= boundary)
    by_day = {row.day: row.count for row in current}
    sparkline = [
        by_day.get(boundary + timedelta(days=offset), 0)
        for offset in range(1, days + 1)
    ]

    return Trend(
        current=current,
        delta=sum(row.count for row in current) - previous,
        sparkline=sparkline,
    )


def _kpis(overview: Overview, days: int) -> None:
    totals = overview.totals
    registrations = _trend(overview.registrations, days)
    active = _trend(overview.active, days)
    uploads = _trend(overview.uploads, days)
    comments = _trend(overview.comments, days)
    actions = _trend(overview.actions, days)
    row = st.columns(5)
    components.metric(
        row[0],
        "Players",
        f"{totals.users:,}",
        delta=f"{registrations.delta:+,} new vs previous {days}d",
        chart_data=registrations.sparkline,
        chart_type="area",
    )
    components.metric(
        row[1],
        "Seen recently",
        f"{sum(active.sparkline):,}",
        delta=f"{active.delta:+,}",
        chart_data=active.sparkline,
        chart_type="bar",
    )
    components.metric(
        row[2],
        "Levels",
        f"{totals.levels:,}",
        delta=f"{uploads.delta:+,} uploads vs previous {days}d",
        chart_data=uploads.sparkline,
        chart_type="area",
    )
    components.metric(
        row[3],
        "Level comments",
        f"{totals.comments:,}",
        delta=f"{comments.delta:+,}",
        chart_data=comments.sparkline,
        chart_type="area",
    )
    components.metric(
        row[4],
        "Mod actions",
        f"{sum(actions.sparkline):,}",
        delta=f"{actions.delta:+,}",
        delta_color="off",
        chart_data=actions.sparkline,
        chart_type="bar",
    )
    row = st.columns(5)
    components.metric(row[0], "Rated levels", f"{totals.rated_levels:,}")
    components.metric(row[1], "Featured levels", f"{totals.featured_levels:,}")
    components.metric(row[2], "Profile posts", f"{totals.account_comments:,}")
    components.metric(row[3], "Cloud saves", f"{totals.saves:,}")
    components.metric(
        row[4],
        "Active bans",
        f"{totals.active_bans:,}",
        delta_color="inverse",
    )

    return None


def page() -> None:
    components.header("Dashboard", "What the server has been up to.")

    with components.toolbar():
        window = st.pills(
            "Window", list(_WINDOWS), default="30 days", selection_mode="single"
        )

    days = _WINDOWS.get(window or "30 days", 30)
    overview = runtime.active().run(lambda ctx: _load(ctx, days))
    _kpis(overview, days)
    st.space("small")

    registrations = _trend(overview.registrations, days).current
    active = _trend(overview.active, days).current
    uploads = _trend(overview.uploads, days).current
    comments = _trend(overview.comments, days).current
    actions = _trend(overview.actions, days).current
    grid = st.columns(2, border=True)
    grid[0].altair_chart(charts.daily(registrations, "Registrations"), width="stretch")
    grid[1].altair_chart(
        charts.daily(active, "Players seen", "#7ee2b0"), width="stretch"
    )
    grid = st.columns(2, border=True)
    grid[0].altair_chart(
        charts.daily(uploads, "Level uploads", "#ffd58a"), width="stretch"
    )
    grid[1].altair_chart(charts.daily(comments, "Comments", "#7cc7ff"), width="stretch")

    grid = st.columns(3, border=True)
    grid[0].altair_chart(
        charts.bars(overview.difficulties, "Difficulty faces", labels.DIFFICULTY),
        width="stretch",
    )
    grid[1].altair_chart(
        charts.bars(overview.stars, "Star ratings", {n: str(n) for n in range(11)}),
        width="stretch",
    )
    grid[2].altair_chart(
        charts.bars(overview.lengths, "Lengths", labels.LENGTH), width="stretch"
    )

    grid = st.columns(2, border=True)
    grid[0].altair_chart(
        charts.hours(overview.hours, "Comments by hour"), width="stretch"
    )
    grid[1].altair_chart(
        charts.daily(actions, "Moderation actions", "#ff9db0"), width="stretch"
    )

    left, right = st.columns([1, 1], border=True)

    with left:
        st.markdown("#### Top creators")
        st.dataframe(
            pd.DataFrame(
                {
                    "id": [row.user_id for row in overview.creators],
                    "creator": [row.username for row in overview.creators],
                    "levels": [row.levels for row in overview.creators],
                    "rated": [row.rated for row in overview.creators],
                    "creator points": [row.creator_points for row in overview.creators],
                }
            ),
            hide_index=True,
            width="stretch",
        )

    with right:
        st.markdown("#### Latest moderation events")
        st.dataframe(
            pd.DataFrame(
                {
                    "when": [
                        components.stamp(event.created_at) for event in overview.events
                    ],
                    "actor": [
                        overview.actor_names.get(event.user_id, f"#{event.user_id}")
                        for event in overview.events
                    ],
                    "action": [event.action for event in overview.events],
                    "target": [
                        f"{event.target_type.value} #{event.target_id}"
                        for event in overview.events
                    ],
                }
            ),
            hide_index=True,
            width="stretch",
        )

    st.markdown(
        theme.muted(f"Server time {clock.now():%Y-%m-%d %H:%M} UTC"),
        unsafe_allow_html=True,
    )
