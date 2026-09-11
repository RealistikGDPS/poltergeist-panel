from dataclasses import dataclass

import pandas as pd
import streamlit as st
from gdformat.enums import TimelyType

from app.resources import Level
from app.resources import TimelyLevel
from app.services import AbstractContext
from app.services import ServiceError
from app.services import administration
from app.services import timely
from app.utilities import clock
from panel import components
from panel import labels
from panel import runtime
from panel import theme
from panel.auth import current


@dataclass(frozen=True, slots=True)
class Queue:
    entries: list[TimelyLevel]
    levels: dict[int, Level]
    current: TimelyLevel | None


async def _queue(ctx: AbstractContext, timely_type: TimelyType) -> Queue:
    entries = await ctx.timely.list_from(timely_type, 0, components.PAGE_SIZE)
    found = await ctx.levels.find_many_by_ids(
        list({entry.level_id for entry in entries})
    )

    return Queue(
        entries=entries,
        levels={level.id: level for level in found},
        current=await ctx.timely.find_current(timely_type),
    )


def _status(entry: TimelyLevel) -> str:
    now = clock.now()

    if entry.ends_at <= now:
        return "past"

    if entry.starts_at <= now:
        return "live"

    return "queued"


def _type_view(timely_type: TimelyType) -> None:
    operator = current()

    if operator is None:
        return

    actor = operator.user_id
    queue = runtime.active().run(lambda ctx: _queue(ctx, timely_type))
    key = timely_type.name.lower()

    if queue.current is None:
        st.warning("Nothing is being served right now.")
    else:
        level = queue.levels.get(queue.current.level_id)
        name = level.name if level else f"#{queue.current.level_id}"
        remaining = clock.seconds_until(queue.current.ends_at)
        st.markdown(
            theme.card(
                f"Live now: {name}",
                [
                    ("Number", f"#{queue.current.sequence}"),
                    ("Level id", str(queue.current.level_id)),
                    (
                        "Ends",
                        f"{components.stamp(queue.current.ends_at)} "
                        f"({remaining // 3600}h {remaining % 3600 // 60}m left)",
                    ),
                ],
            ),
            unsafe_allow_html=True,
        )

    frame = pd.DataFrame(
        [
            {
                "number": entry.sequence,
                "level": queue.levels[entry.level_id].name
                if entry.level_id in queue.levels
                else f"#{entry.level_id}",
                "level id": entry.level_id,
                "starts": components.stamp(entry.starts_at),
                "ends": components.stamp(entry.ends_at),
                "status": _status(entry),
                "id": entry.id,
            }
            for entry in queue.entries
        ]
    )
    selected = components.table(frame, f"{key}_table")
    chosen = [queue.entries[index] for index in selected]
    left, right = st.columns(2)

    with left, st.form(f"{key}_schedule"):
        level_id = st.number_input("Level id to append", min_value=1, step=1)

        if st.form_submit_button("Schedule", type="primary"):
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

    with right:
        st.markdown(
            theme.muted(
                "Removing an entry keeps its number; later entries keep their windows."
            ),
            unsafe_allow_html=True,
        )

        if chosen and components.confirm("Remove selected", f"{key}_remove"):
            outcomes = runtime.active().run(
                lambda ctx: _remove_many(ctx, actor, [entry.id for entry in chosen])
            )
            components.report_bulk(outcomes, "Removed")
            st.rerun()


async def _remove_many(
    ctx: AbstractContext, actor: int, ids: list[int]
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await administration.remove_timely(
            ctx, actor_user_id=actor, timely_id=timely_id
        )
        for timely_id in ids
    ]


def page() -> None:
    components.header("Timely levels", "Daily, weekly and event queues.")
    tabs = st.tabs([labels.TIMELY[t] for t in TimelyType])

    for tab, timely_type in zip(tabs, TimelyType, strict=True):
        with tab:
            _type_view(timely_type)
