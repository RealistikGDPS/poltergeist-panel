from dataclasses import dataclass

import pandas as pd
import streamlit as st
from gdformat.enums import TimelyType
from poltergeist_core.resources import Level
from poltergeist_core.resources import TimelyLevel
from poltergeist_core.services import AbstractContext
from poltergeist_core.services import ServiceError
from poltergeist_core.services import administration
from poltergeist_core.services import timely
from poltergeist_core.utilities import clock

from panel import components
from panel import labels
from panel import runtime
from panel import theme
from panel.auth import current

_ROWS = 20


@dataclass(frozen=True, slots=True)
class Queue:
    entries: list[TimelyLevel]
    levels: dict[int, Level]
    current: TimelyLevel | None


async def _queue(ctx: AbstractContext, timely_type: TimelyType) -> Queue:
    entries = await ctx.timely.list_from(timely_type, 0, _ROWS)
    found = await ctx.levels.find_many_by_ids(
        list({entry.level_id for entry in entries})
    )

    return Queue(
        entries=entries,
        levels={level.id: level for level in found},
        current=await ctx.timely.find_current(timely_type),
    )


async def _remove_many(
    ctx: AbstractContext, actor: int, ids: list[int]
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await administration.remove_timely(
            ctx, actor_user_id=actor, timely_id=timely_id
        )
        for timely_id in ids
    ]


def _status(entry: TimelyLevel) -> str:
    now = clock.now()

    if entry.ends_at <= now:
        return "past"

    if entry.starts_at <= now:
        return "live"

    return "queued"


def _type_view(timely_type: TimelyType, actor: int) -> None:
    key = timely_type.name.lower()
    queue = runtime.active().run(lambda ctx: _queue(ctx, timely_type))
    st.markdown(f"#### {labels.TIMELY[timely_type]}")

    if queue.current is None:
        st.metric("Live now", "nothing", border=True)
    else:
        level = queue.levels.get(queue.current.level_id)
        remaining = clock.seconds_until(queue.current.ends_at)
        st.metric(
            f"Live now · #{queue.current.sequence}",
            level.name if level else f"#{queue.current.level_id}",
            delta=f"{remaining // 3600}h {remaining % 3600 // 60}m left",
            delta_color="off",
            border=True,
        )

    frame = pd.DataFrame(
        [
            {
                "no.": entry.sequence,
                "level": queue.levels[entry.level_id].name
                if entry.level_id in queue.levels
                else f"#{entry.level_id}",
                "starts": components.stamp(entry.starts_at),
                "status": _status(entry),
                "id": entry.id,
            }
            for entry in queue.entries
        ]
    )
    selected = components.table(frame, f"{key}_table")
    chosen = [queue.entries[index] for index in selected]

    with st.form(f"{key}_schedule", border=False):
        level_id = st.number_input("Level id to append", min_value=1, step=1)

        if st.form_submit_button("Schedule", type="primary", width="stretch"):
            components.report(
                runtime.active().run(
                    lambda ctx: timely.schedule(
                        ctx,
                        actor_user_id=actor,
                        timely_type=timely_type,
                        level_id=int(level_id),
                    )
                ),
                "Scheduled.",
            )
            st.rerun()

    if chosen and components.confirm("Remove selected", f"{key}_remove"):
        outcomes = runtime.active().run(
            lambda ctx: _remove_many(ctx, actor, [entry.id for entry in chosen])
        )
        components.report_bulk(outcomes, "Removed")
        st.rerun()


def page() -> None:
    components.header("Timely levels", "Daily, weekly and event queues side by side.")
    operator = current()

    if operator is None:
        return

    grid = st.columns(3, border=True)

    for column, timely_type in zip(grid, TimelyType, strict=True):
        with column:
            _type_view(timely_type, operator.user_id)

    st.markdown(
        theme.muted(
            "A new entry starts when the previous one ends, or right away when nothing "
            "valid is live. Removing an entry keeps its number."
        ),
        unsafe_allow_html=True,
    )
