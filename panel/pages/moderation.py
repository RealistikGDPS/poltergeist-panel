import json
from dataclasses import dataclass

import pandas as pd
import streamlit as st

from app.resources import BanType
from app.resources import ModAction
from app.resources import ModTarget
from app.resources import User
from app.resources import UserBan
from app.services import AbstractContext
from app.services import ServiceError
from app.services import moderation
from panel import components
from panel import labels
from panel import runtime
from panel.auth import current


@dataclass(frozen=True, slots=True)
class EventListing:
    events: list[ModAction]
    users: dict[int, User]
    total: int


@dataclass(frozen=True, slots=True)
class BanListing:
    bans: list[UserBan]
    users: dict[int, User]
    total: int


async def _events(
    ctx: AbstractContext,
    actor: int | None,
    target_type: ModTarget | None,
    target_id: int | None,
    page: int,
) -> EventListing:
    events = await ctx.mod_actions.list_recent(
        user_id=actor,
        target_type=target_type,
        target_id=target_id,
        page=page,
        size=components.PAGE_SIZE,
    )
    users = await ctx.users.find_many_by_ids(list({event.user_id for event in events}))

    return EventListing(
        events=events,
        users={user.id: user for user in users},
        total=await ctx.mod_actions.count_recent(
            user_id=actor, target_type=target_type, target_id=target_id
        ),
    )


async def _bans(ctx: AbstractContext, page: int) -> BanListing:
    bans = await ctx.bans.list_all_active(page, components.PAGE_SIZE)
    ids = {ban.user_id for ban in bans} | {
        ban.issued_by_user_id for ban in bans if ban.issued_by_user_id is not None
    }
    users = await ctx.users.find_many_by_ids(list(ids))

    return BanListing(
        bans=bans,
        users={user.id: user for user in users},
        total=await ctx.bans.count_all_active(),
    )


async def _unban_many(
    ctx: AbstractContext, actor: int, bans: list[UserBan]
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await moderation.unban(
            ctx, actor_user_id=actor, target_user_id=ban.user_id, ban_type=ban.type
        )
        for ban in bans
    ]


def _event_log() -> None:
    first, second, third = st.columns(3)
    actor_text = first.text_input("Actor id")
    target_label = second.selectbox(
        "Target type", ["Any", *[t.value for t in ModTarget]]
    )
    target_text = third.text_input("Target id")
    actor = int(actor_text) if actor_text.strip().isdecimal() else None
    target_type = None if target_label in (None, "Any") else ModTarget(target_label)
    target_id = int(target_text) if target_text.strip().isdecimal() else None

    total = runtime.active().run(
        lambda ctx: ctx.mod_actions.count_recent(
            user_id=actor, target_type=target_type, target_id=target_id
        )
    )
    page_index = components.paginator("events", total)
    listing = runtime.active().run(
        lambda ctx: _events(ctx, actor, target_type, target_id, page_index)
    )
    frame = pd.DataFrame(
        [
            {
                "when": components.stamp(event.created_at),
                "actor": listing.users[event.user_id].username
                if event.user_id in listing.users
                else f"#{event.user_id}",
                "action": event.action,
                "target": f"{event.target_type.value} #{event.target_id}",
                "details": json.dumps(event.details) if event.details else "",
            }
            for event in listing.events
        ]
    )
    st.dataframe(frame, hide_index=True, width="stretch")


def _bans_view() -> None:
    operator = current()

    if operator is None:
        return

    actor = operator.user_id
    total = runtime.active().run(lambda ctx: ctx.bans.count_all_active())
    page_index = components.paginator("bans", total)
    listing = runtime.active().run(lambda ctx: _bans(ctx, page_index))
    frame = pd.DataFrame(
        [
            {
                "user": listing.users[ban.user_id].username
                if ban.user_id in listing.users
                else f"#{ban.user_id}",
                "user id": ban.user_id,
                "type": labels.BAN[ban.type],
                "reason": ban.reason,
                "issued by": listing.users[ban.issued_by_user_id].username
                if ban.issued_by_user_id in listing.users
                else "import",
                "since": components.stamp(ban.created_at),
                "expires": "never"
                if ban.expires_at is None
                else components.stamp(ban.expires_at),
            }
            for ban in listing.bans
        ]
    )
    selected = components.table(frame, "bans_table")
    chosen = [listing.bans[index] for index in selected]

    if chosen and st.button("Lift selected bans", type="primary"):
        components.report_bulk(
            runtime.active().run(lambda ctx: _unban_many(ctx, actor, chosen)), "Lifted"
        )
        st.rerun()

    st.markdown("#### Ban by id")

    with st.form("ban_by_id"):
        first, second, third = st.columns(3)
        user_id = first.number_input("User id", min_value=1, step=1)
        with second:
            ban_type = components.choose("Type", list(BanType), lambda b: labels.BAN[b])
        days = third.number_input(
            "Days (0 = permanent)", min_value=0, max_value=3650, value=7
        )
        reason = st.text_input("Reason", max_chars=255)

        if st.form_submit_button("Ban", type="primary"):
            components.report(
                runtime.active().run(
                    lambda ctx: moderation.ban(
                        ctx,
                        actor_user_id=actor,
                        target_user_id=int(user_id),
                        ban_type=ban_type,
                        days=int(days) or None,
                        reason=reason,
                    )
                ),
                "Banned.",
            )


def page() -> None:
    components.header("Moderation", "Every action leaves a trace here.")
    log_tab, bans_tab = st.tabs(["Event log", "Active bans"])

    with log_tab:
        _event_log()

    with bans_tab:
        _bans_view()
