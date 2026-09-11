from dataclasses import dataclass

import pandas as pd
import streamlit as st

from app.resources import CreatorRow
from app.resources import DailyCount
from app.resources import LabelCount
from app.resources import ModAction
from app.resources import Totals
from app.services import AbstractContext
from panel import charts
from panel import components
from panel import labels
from panel import runtime

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


async def _load(ctx: AbstractContext, days: int) -> Overview:
    events = await ctx.mod_actions.list_recent(
        user_id=None, target_type=None, target_id=None, page=0, size=_RECENT_EVENTS
    )
    actors = await ctx.users.find_many_by_ids(list({event.user_id for event in events}))

    return Overview(
        totals=await ctx.analytics.totals(),
        registrations=await ctx.analytics.registrations_per_day(days),
        active=await ctx.analytics.active_users_per_day(days),
        uploads=await ctx.analytics.uploads_per_day(days),
        comments=await ctx.analytics.comments_per_day(days),
        actions=await ctx.analytics.mod_actions_per_day(days),
        hours=await ctx.analytics.comments_per_hour(days),
        difficulties=await ctx.analytics.difficulty_distribution(),
        stars=await ctx.analytics.stars_distribution(),
        lengths=await ctx.analytics.length_distribution(),
        creators=await ctx.analytics.top_creators(10),
        events=events,
        actor_names={user.id: user.username for user in actors},
    )


def page() -> None:
    components.header("Dashboard", "What the server has been up to.")
    window = st.pills(
        "Window", list(_WINDOWS), default="30 days", selection_mode="single"
    )
    days = _WINDOWS.get(window or "30 days", 30)
    overview = runtime.active().run(lambda ctx: _load(ctx, days))
    totals = overview.totals

    first, second, third, fourth, fifth = st.columns(5)
    first.metric("Players", f"{totals.users:,}")
    second.metric("Levels", f"{totals.levels:,}")
    third.metric("Rated", f"{totals.rated_levels:,}")
    fourth.metric("Featured", f"{totals.featured_levels:,}")
    fifth.metric("Active bans", f"{totals.active_bans:,}")
    first, second, third, fourth, fifth = st.columns(5)
    first.metric("Level comments", f"{totals.comments:,}")
    second.metric("Profile posts", f"{totals.account_comments:,}")
    third.metric("Messages", f"{totals.messages:,}")
    fourth.metric("Songs", f"{totals.songs:,}")
    fifth.metric("Cloud saves", f"{totals.saves:,}")

    left, right = st.columns(2)
    left.altair_chart(
        charts.daily(overview.registrations, "Registrations"), width="stretch"
    )
    right.altair_chart(
        charts.daily(overview.active, "Players seen", "#7ee2b0"), width="stretch"
    )
    left, right = st.columns(2)
    left.altair_chart(
        charts.daily(overview.uploads, "Level uploads", "#ffd58a"), width="stretch"
    )
    right.altair_chart(
        charts.daily(overview.comments, "Comments", "#7cc7ff"), width="stretch"
    )

    left, middle, right = st.columns(3)
    left.altair_chart(
        charts.bars(overview.difficulties, "Difficulty faces", labels.DIFFICULTY),
        width="stretch",
    )
    middle.altair_chart(
        charts.bars(overview.stars, "Star ratings", {n: str(n) for n in range(11)}),
        width="stretch",
    )
    right.altair_chart(
        charts.bars(overview.lengths, "Lengths", labels.LENGTH), width="stretch"
    )

    left, right = st.columns(2)
    left.altair_chart(charts.hours(overview.hours, "Comments by hour"), width="stretch")
    right.altair_chart(
        charts.daily(overview.actions, "Moderation actions", "#ff9db0"), width="stretch"
    )

    left, right = st.columns([1, 1])

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
