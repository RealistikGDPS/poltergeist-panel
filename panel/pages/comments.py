from dataclasses import dataclass

import pandas as pd
import streamlit as st

from app.resources import AccountComment
from app.resources import BanType
from app.resources import Comment
from app.resources import User
from app.services import AbstractContext
from app.services import ServiceError
from app.services import comments
from app.services import moderation
from panel import components
from panel import runtime
from panel import theme
from panel.auth import current
from panel.auth import session_for


@dataclass(frozen=True, slots=True)
class LevelListing:
    comments: list[Comment]
    users: dict[int, User]
    level_names: dict[int, str]


@dataclass(frozen=True, slots=True)
class ProfileListing:
    comments: list[AccountComment]
    users: dict[int, User]


async def _level_listing(
    ctx: AbstractContext, query: str, user_id: int | None, page: int
) -> LevelListing:
    found = await ctx.comments.list_recent(
        query=query, user_id=user_id, page=page, size=components.PAGE_SIZE
    )
    users = await ctx.users.find_many_by_ids(list({entry.user_id for entry in found}))
    level_ids = list({entry.level_id for entry in found if entry.level_id is not None})
    found_levels = await ctx.levels.find_many_by_ids(level_ids)

    return LevelListing(
        comments=found,
        users={user.id: user for user in users},
        level_names={level.id: level.name for level in found_levels},
    )


async def _profile_listing(
    ctx: AbstractContext, query: str, user_id: int | None, page: int
) -> ProfileListing:
    found = await ctx.account_comments.list_recent(
        query=query, user_id=user_id, page=page, size=components.PAGE_SIZE
    )
    users = await ctx.users.find_many_by_ids(list({entry.user_id for entry in found}))

    return ProfileListing(comments=found, users={user.id: user for user in users})


async def _delete_level_comments(
    ctx: AbstractContext, actor: int, ids: list[int]
) -> list[ServiceError.OnSuccess[object]]:
    user = await ctx.users.find_by_id(actor)

    if user is None:
        return []

    session = session_for(user)

    return [
        await comments.delete_level_comment(ctx, session, comment_id)
        for comment_id in ids
    ]


async def _delete_profile_comments(
    ctx: AbstractContext, actor: int, ids: list[int]
) -> list[ServiceError.OnSuccess[object]]:
    user = await ctx.users.find_by_id(actor)

    if user is None:
        return []

    session = session_for(user)

    return [
        await comments.delete_account_comment(ctx, session, comment_id)
        for comment_id in ids
    ]


async def _ban_authors(
    ctx: AbstractContext, actor: int, user_ids: list[int], days: int | None, reason: str
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await moderation.ban(
            ctx,
            actor_user_id=actor,
            target_user_id=user_id,
            ban_type=BanType.COMMENT,
            days=days,
            reason=reason,
        )
        for user_id in user_ids
    ]


def _filters(key: str) -> tuple[str, int | None, int]:
    with components.toolbar():
        query = st.text_input("Content contains", key=f"{key}_query")
        author = st.text_input("Author id", key=f"{key}_author")
        author_id = int(author) if author.strip().isdecimal() else None
        total = runtime.active().run(
            lambda ctx: (
                ctx.comments.count_recent(query=query, user_id=author_id)
                if key == "lc"
                else ctx.account_comments.count_recent(query=query, user_id=author_id)
            )
        )
        page_index = components.paginator(key, total)

    return query, author_id, page_index


def _actions(
    key: str,
    comment_ids: list[int],
    author_ids: list[int],
    actor: int,
    *,
    profile: bool,
) -> None:
    if not comment_ids:
        st.markdown(
            theme.muted("Select rows to delete them or to ban their authors."),
            unsafe_allow_html=True,
        )

        return

    delete_column, ban_column = st.columns(2, border=True)

    with delete_column:
        st.markdown("#### Delete")
        components.badges([f"{len(comment_ids)} comments"], "blue")

        if components.confirm("Delete selected comments", f"{key}_delete"):
            action = _delete_profile_comments if profile else _delete_level_comments
            components.report_bulk(
                runtime.active().run(lambda ctx: action(ctx, actor, comment_ids)),
                "Deleted",
            )
            st.rerun()

    with ban_column, st.form(f"{key}_ban_form", border=False):
        st.markdown("#### Comment-ban the authors")
        components.badges([f"{len(set(author_ids))} authors"], "blue")
        left, right = st.columns(2)
        permanent = left.checkbox("Permanent", key=f"{key}_perm")
        days = right.number_input(
            "Days", min_value=1, max_value=3650, value=3, key=f"{key}_days"
        )
        reason = st.text_input("Reason", max_chars=255, key=f"{key}_reason")

        if st.form_submit_button("Ban authors", type="primary", width="stretch"):
            components.report_bulk(
                runtime.active().run(
                    lambda ctx: _ban_authors(
                        ctx,
                        actor,
                        sorted(set(author_ids)),
                        None if permanent else int(days),
                        reason,
                    )
                ),
                "Banned",
            )


def page() -> None:
    components.header("Comments", "Review level comments and profile posts in bulk.")
    operator = current()

    if operator is None:
        return

    actor = operator.user_id
    level_tab, profile_tab = st.tabs(["Level comments", "Profile posts"])

    with level_tab:
        query, author, page_index = _filters("lc")
        listing = runtime.active().run(
            lambda ctx: _level_listing(ctx, query, author, page_index)
        )
        frame = pd.DataFrame(
            [
                {
                    "id": entry.id,
                    "author": listing.users[entry.user_id].username
                    if entry.user_id in listing.users
                    else f"#{entry.user_id}",
                    "on": listing.level_names.get(entry.level_id, f"#{entry.level_id}")
                    if entry.level_id is not None
                    else f"list {entry.list_id}",
                    "content": entry.content,
                    "percent": entry.percent,
                    "likes": entry.likes,
                    "when": components.stamp(entry.created_at),
                }
                for entry in listing.comments
            ]
        )
        selected = components.table(frame, "lc_table")
        chosen = [listing.comments[index] for index in selected]
        _actions(
            "lc",
            [entry.id for entry in chosen],
            [entry.user_id for entry in chosen],
            actor,
            profile=False,
        )

    with profile_tab:
        query, author, page_index = _filters("pc")
        profile = runtime.active().run(
            lambda ctx: _profile_listing(ctx, query, author, page_index)
        )
        profile_frame = pd.DataFrame(
            [
                {
                    "id": entry.id,
                    "author": profile.users[entry.user_id].username
                    if entry.user_id in profile.users
                    else f"#{entry.user_id}",
                    "content": entry.content,
                    "likes": entry.likes,
                    "when": components.stamp(entry.created_at),
                }
                for entry in profile.comments
            ]
        )
        selected = components.table(profile_frame, "pc_table")
        chosen_profile = [profile.comments[index] for index in selected]
        _actions(
            "pc",
            [entry.id for entry in chosen_profile],
            [entry.user_id for entry in chosen_profile],
            actor,
            profile=True,
        )
