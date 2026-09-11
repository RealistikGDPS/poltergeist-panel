from dataclasses import dataclass
from datetime import timedelta

import pandas as pd
import streamlit as st

from app.resources import BanType
from app.resources import Device
from app.resources import Role
from app.resources import User
from app.resources import UserBan
from app.resources import UserStats
from app.services import AbstractContext
from app.services import ServiceError
from app.services import administration
from app.services import auth
from app.services import moderation
from app.services import roles
from app.utilities import clock
from panel import components
from panel import labels
from panel import runtime
from panel import theme
from panel.auth import current

_ORDERS = {
    "Newest": "newest",
    "Oldest": "oldest",
    "Recently seen": "recently_seen",
    "Name": "name",
}


@dataclass(frozen=True, slots=True)
class Listing:
    users: list[User]
    stats: dict[int, UserStats]
    roles: dict[int, list[Role]]
    bans: dict[int, list[UserBan]]
    total: int
    all_roles: list[Role]


@dataclass(frozen=True, slots=True)
class Detail:
    user: User
    stats: UserStats | None
    roles: list[Role]
    bans: list[UserBan]
    devices: list[Device]
    levels: int
    has_password: bool


async def _listing(ctx: AbstractContext, query: str, order: str, page: int) -> Listing:
    users = await ctx.users.list_page(
        query=query, order=order, page=page, size=components.PAGE_SIZE
    )
    ids = [user.id for user in users]
    stats = {
        entry.user_id: entry for entry in await ctx.stats.find_many_by_user_ids(ids)
    }

    return Listing(
        users=users,
        stats=stats,
        roles={user.id: await ctx.roles.list_by_user(user.id) for user in users},
        bans={user.id: await ctx.bans.list_active(user.id) for user in users},
        total=await ctx.users.count_page(query=query),
        all_roles=await ctx.roles.list_all(),
    )


async def _detail(ctx: AbstractContext, user_id: int) -> Detail | None:
    user = await ctx.users.find_by_id(user_id)

    if user is None:
        return None

    credential = await ctx.credentials.find_by_user_id(user_id)

    return Detail(
        user=user,
        stats=await ctx.stats.find_by_user_id(user_id),
        roles=await ctx.roles.list_by_user(user_id),
        bans=await ctx.bans.list_active(user_id),
        devices=await ctx.devices.list_by_user(user_id),
        levels=await ctx.levels.count_by_user(user_id),
        has_password=credential is not None and credential.gjp2_bcrypt is not None,
    )


def _frame(listing: Listing) -> pd.DataFrame:
    rows = []

    for user in listing.users:
        stats = listing.stats.get(user.id)

        rows.append(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "stars": stats.stars if stats else 0,
                "demons": stats.demons if stats else 0,
                "creator points": stats.creator_points if stats else 0,
                "roles": ", ".join(role.name for role in listing.roles[user.id]),
                "bans": ", ".join(ban.type.value for ban in listing.bans[user.id]),
                "registered": components.stamp(user.registered_at),
                "last seen": components.age(user.last_seen_at),
            }
        )

    return pd.DataFrame(rows)


def _bulk(selected: list[User], all_roles: list[Role]) -> None:
    operator = current()

    if operator is None:
        return

    actor = operator.user_id
    ids = [user.id for user in selected]
    st.markdown(f"#### Bulk actions · {len(selected)} selected")
    ban_tab, unban_tab, role_tab, session_tab = st.tabs(
        ["Ban", "Unban", "Roles", "Sessions"]
    )

    with ban_tab, st.form("bulk_ban"):
        ban_type = components.choose("Type", list(BanType), lambda b: labels.BAN[b])
        permanent = st.checkbox("Permanent", value=False)
        days = st.number_input("Days", min_value=1, max_value=3650, value=7)
        reason = st.text_input("Reason", max_chars=255)

        if st.form_submit_button("Ban selected", type="primary"):
            banned = runtime.active().run(
                lambda ctx: _ban_many(
                    ctx, actor, ids, ban_type, None if permanent else int(days), reason
                )
            )
            components.report_bulk(banned, "Banned")

    with unban_tab, st.form("bulk_unban"):
        lift_type = components.choose(
            "Type", list(BanType), lambda b: labels.BAN[b], key="unban_type"
        )

        if st.form_submit_button("Lift selected", type="primary"):
            lifted = runtime.active().run(
                lambda ctx: _unban_many(ctx, actor, ids, lift_type)
            )
            components.report_bulk(lifted, "Unbanned")

    with role_tab, st.form("bulk_roles"):
        role = st.selectbox("Role", all_roles, format_func=lambda r: r.name)
        grant = st.radio("Action", ["Assign", "Revoke"], horizontal=True)

        if (
            st.form_submit_button("Apply to selected", type="primary")
            and role is not None
        ):
            outcomes = runtime.active().run(
                lambda ctx: _roles_many(ctx, actor, ids, role.name, grant == "Assign")
            )
            components.report_bulk(
                outcomes, grant + "ed" if grant == "Revoke" else "Assigned"
            )

    with session_tab:
        st.markdown(
            theme.muted("Forces the selected accounts to verify their password again."),
            unsafe_allow_html=True,
        )

        if st.button("Revoke sessions", key="bulk_sessions"):
            outcomes = runtime.active().run(lambda ctx: _revoke_many(ctx, actor, ids))
            components.report_bulk(outcomes, "Revoked")


async def _ban_many(
    ctx: AbstractContext,
    actor: int,
    ids: list[int],
    ban_type: BanType,
    days: int | None,
    reason: str,
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await moderation.ban(
            ctx,
            actor_user_id=actor,
            target_user_id=user_id,
            ban_type=ban_type,
            days=days,
            reason=reason,
        )
        for user_id in ids
    ]


async def _unban_many(
    ctx: AbstractContext, actor: int, ids: list[int], ban_type: BanType
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await moderation.unban(
            ctx, actor_user_id=actor, target_user_id=user_id, ban_type=ban_type
        )
        for user_id in ids
    ]


async def _roles_many(
    ctx: AbstractContext, actor: int, ids: list[int], role_name: str, grant: bool
) -> list[ServiceError.OnSuccess[object]]:
    outcomes: list[ServiceError.OnSuccess[object]] = []

    for user_id in ids:
        if grant:
            outcomes.append(
                await roles.assign(
                    ctx,
                    actor_user_id=actor,
                    target_user_id=user_id,
                    role_name=role_name,
                    expires_at=None,
                )
            )
        else:
            outcomes.append(
                await roles.revoke(
                    ctx,
                    actor_user_id=actor,
                    target_user_id=user_id,
                    role_name=role_name,
                )
            )

    return outcomes


async def _revoke_many(
    ctx: AbstractContext, actor: int, ids: list[int]
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await administration.revoke_sessions(ctx, actor_user_id=actor, user_id=user_id)
        for user_id in ids
    ]


def _detail_view(user_id: int) -> None:
    operator = current()
    detail = runtime.active().run(lambda ctx: _detail(ctx, user_id))

    if detail is None or operator is None:
        st.warning("That account no longer exists.")

        return

    user = detail.user
    stats = detail.stats
    actor = operator.user_id
    st.markdown(
        f"#### {user.username} <span class='pg-muted'>#{user.id}</span>",
        unsafe_allow_html=True,
    )
    flags = [role.name for role in detail.roles]
    st.markdown(
        components.pills(flags)
        + components.pills([f"{ban.type.value} ban" for ban in detail.bans], "bad")
        + ("" if detail.has_password else theme.pill("legacy password", "warn")),
        unsafe_allow_html=True,
    )
    left, middle, right = st.columns(3)

    with left:
        st.markdown(
            theme.card(
                "Account",
                [
                    ("Email", user.email),
                    ("Registered", components.stamp(user.registered_at)),
                    ("Last seen", components.age(user.last_seen_at)),
                    ("Levels", str(detail.levels)),
                    ("Messages", user.message_privacy.name.title()),
                    ("Requests", user.friend_request_privacy.name.title()),
                    ("History", user.comment_history_privacy.name.title()),
                ],
            ),
            unsafe_allow_html=True,
        )

    with middle:
        st.markdown(
            theme.card(
                "Progress",
                [
                    ("Stars", str(stats.stars if stats else 0)),
                    ("Moons", str(stats.moons if stats else 0)),
                    ("Demons", str(stats.demons if stats else 0)),
                    ("Diamonds", str(stats.diamonds if stats else 0)),
                    ("Secret coins", str(stats.secret_coins if stats else 0)),
                    ("User coins", str(stats.user_coins if stats else 0)),
                    ("Creator points", str(stats.creator_points if stats else 0)),
                ],
            ),
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            theme.card(
                "Devices",
                [
                    (
                        device.platform.name.title(),
                        f"{device.udid[:18]}… {components.age(device.last_seen_at)}",
                    )
                    for device in detail.devices[:6]
                ]
                or [("None", "no device has logged in")],
            ),
            unsafe_allow_html=True,
        )

    for ban in detail.bans:
        expiry = (
            "permanent" if ban.expires_at is None else components.stamp(ban.expires_at)
        )
        st.warning(
            f"{ban.type.value} ban until {expiry}: {ban.reason or 'no reason given'}"
        )

    password_tab, rename_tab, colour_tab = st.tabs(
        ["Password", "Rename", "Comment colour"]
    )

    with password_tab, st.form("set_password"):
        password = st.text_input("New password", type="password")

        if st.form_submit_button("Set password", type="primary"):
            components.report(
                runtime.active().run(
                    lambda ctx: auth.set_password(ctx, user.id, password)
                ),
                "Password set; the player must log in again.",
            )

    with rename_tab, st.form("rename"):
        username = st.text_input("New username", value=user.username, max_chars=20)

        if st.form_submit_button("Rename", type="primary"):
            components.report(
                runtime.active().run(
                    lambda ctx: administration.rename_user(
                        ctx, actor_user_id=actor, user_id=user.id, username=username
                    )
                ),
                "Renamed.",
            )
            st.rerun()

    with colour_tab, st.form("colour"):
        packed = user.comment_colour or 0xFFFFFF
        chosen = st.color_picker("Colour", value=f"#{packed:06x}")
        clear = st.checkbox("Clear the colour instead")

        if st.form_submit_button("Save colour", type="primary"):
            colour = None if clear else int(chosen.lstrip("#"), 16)
            components.report(
                runtime.active().run(
                    lambda ctx: administration.set_comment_colour(
                        ctx, actor_user_id=actor, user_id=user.id, colour=colour
                    )
                ),
                "Comment colour saved.",
            )


def page() -> None:
    components.header("Users", "Find players, then act on one or many.")
    left, middle, right = st.columns([3, 1, 1])
    query = left.text_input("Search by name, email or id", placeholder="RealistikDash")
    order_label = middle.selectbox("Order", list(_ORDERS))
    order = _ORDERS[order_label or "Newest"]

    with right:
        st.write("")
        st.write("")

    total = runtime.active().run(lambda ctx: ctx.users.count_page(query=query))
    page_index = components.paginator("users", total)
    listing = runtime.active().run(lambda ctx: _listing(ctx, query, order, page_index))
    selected = components.table(_frame(listing), "users_table")
    chosen = [listing.users[index] for index in selected if index < len(listing.users)]

    if len(chosen) == 1:
        _detail_view(chosen[0].id)

    if chosen:
        _bulk(chosen, listing.all_roles)

    st.markdown(
        theme.muted(
            f"Server time {clock.now():%Y-%m-%d %H:%M} UTC · "
            f"bans expire relative to it; a 7 day ban ends "
            f"{(clock.now() + timedelta(days=7)):%Y-%m-%d}."
        ),
        unsafe_allow_html=True,
    )
