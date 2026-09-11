from dataclasses import dataclass
from dataclasses import replace

import pandas as pd
import streamlit as st
from gdformat.enums import DemonDifficulty
from gdformat.enums import SendFeature
from gdformat.enums import TimelyType
from gdformat.enums import Visibility

from app.resources import Level
from app.resources import LevelOrder
from app.resources import LevelSearch
from app.resources import LevelSuggestion
from app.resources import User
from app.services import AbstractContext
from app.services import ServiceError
from app.services import administration
from app.services import levels
from app.services import moderation
from app.services import timely
from panel import components
from panel import labels
from panel import runtime
from panel import theme
from panel.auth import current
from panel.auth import session_for

_ORDERS = {
    "Recent": LevelOrder.UPLOADED,
    "Downloads": LevelOrder.DOWNLOADS,
    "Likes": LevelOrder.LIKES,
    "Featured": LevelOrder.FEATURED,
    "Recently rated": LevelOrder.RATED,
}
_FEATURES = {
    "Keep": None,
    "None": SendFeature.STAR,
    "Feature": SendFeature.FEATURE,
    "Epic": SendFeature.EPIC,
    "Legendary": SendFeature.LEGENDARY,
    "Mythic": SendFeature.MYTHIC,
}
_DEMONS = {
    "Keep": None,
    "Easy": DemonDifficulty.EASY,
    "Medium": DemonDifficulty.MEDIUM,
    "Hard": DemonDifficulty.HARD,
    "Insane": DemonDifficulty.INSANE,
    "Extreme": DemonDifficulty.EXTREME,
}


@dataclass(frozen=True, slots=True)
class Listing:
    levels: list[Level]
    creators: dict[int, User]
    total: int


@dataclass(frozen=True, slots=True)
class Queues:
    suggestions: list[LevelSuggestion]
    reported: list[tuple[int, int]]
    levels: dict[int, Level]
    users: dict[int, User]


def _search(
    query: str, order: LevelOrder, rated: str, creator: str, page: int
) -> LevelSearch:
    search = LevelSearch(
        order=order,
        page=page,
        size=components.PAGE_SIZE,
        include_all_visibilities=True,
        rated=rated == "Rated only",
        unrated=rated == "Unrated only",
    )

    if query.strip().isdecimal():
        return replace(search, level_ids=(int(query),), order=LevelOrder.GIVEN)

    if query.strip():
        search = replace(search, name_prefix=query.strip())

    if creator.strip().isdecimal():
        search = replace(search, creator_ids=(int(creator),))

    return search


async def _listing(ctx: AbstractContext, search: LevelSearch) -> Listing:
    found = await ctx.levels.search(search)
    creators = await ctx.users.find_many_by_ids(
        list({level.user_id for level in found})
    )

    return Listing(
        levels=found,
        creators={user.id: user for user in creators},
        total=await ctx.levels.count(search),
    )


async def _queues(ctx: AbstractContext) -> Queues:
    suggestions = await ctx.suggestions.list_pending(0, components.PAGE_SIZE)
    reported = await ctx.reports.list_open_level_ids(0, components.PAGE_SIZE)
    level_ids = {entry.level_id for entry in suggestions} | {
        level_id for level_id, _ in reported
    }
    found = await ctx.levels.find_many_by_ids(list(level_ids))
    user_ids = {entry.user_id for entry in suggestions} | {
        level.user_id for level in found
    }
    users = await ctx.users.find_many_by_ids(list(user_ids))

    return Queues(
        suggestions=suggestions,
        reported=reported,
        levels={level.id: level for level in found},
        users={user.id: user for user in users},
    )


def _frame(listing: Listing) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": level.id,
                "name": level.name,
                "creator": listing.creators[level.user_id].username
                if level.user_id in listing.creators
                else f"#{level.user_id}",
                "stars": level.stars,
                "difficulty": labels.DIFFICULTY[int(level.difficulty)],
                "rating": labels.RATING[int(level.rating)],
                "featured": level.feature_order > 0,
                "downloads": level.downloads,
                "likes": level.likes,
                "length": labels.LENGTH[int(level.length)],
                "visibility": labels.VISIBILITY[level.visibility],
                "locked": level.update_locked,
                "uploaded": components.stamp(level.uploaded_at),
            }
            for level in listing.levels
        ]
    )


async def _rate_many(
    ctx: AbstractContext,
    actor: int,
    ids: list[int],
    stars: int,
    feature: SendFeature | None,
    demon: DemonDifficulty | None,
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await moderation.rate_level(
            ctx,
            actor_user_id=actor,
            level_id=level_id,
            stars=stars,
            feature=feature,
            demon=demon,
        )
        for level_id in ids
    ]


async def _visibility_many(
    ctx: AbstractContext, actor: int, ids: list[int], visibility: Visibility
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await administration.set_level_visibility(
            ctx, actor_user_id=actor, level_id=level_id, visibility=visibility
        )
        for level_id in ids
    ]


async def _lock_many(
    ctx: AbstractContext, actor: int, ids: list[int], locked: bool
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await administration.set_level_locked(
            ctx, actor_user_id=actor, level_id=level_id, locked=locked
        )
        for level_id in ids
    ]


async def _delete_many(
    ctx: AbstractContext, actor: int, ids: list[int]
) -> list[ServiceError.OnSuccess[object]]:
    user = await ctx.users.find_by_id(actor)

    if user is None:
        return []

    session = session_for(user)

    return [await levels.delete(ctx, session, level_id) for level_id in ids]


async def _schedule_many(
    ctx: AbstractContext, actor: int, ids: list[int], timely_type: TimelyType
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await timely.schedule(
            ctx, actor_user_id=actor, timely_type=timely_type, level_id=level_id
        )
        for level_id in ids
    ]


async def _resolve_many(
    ctx: AbstractContext, actor: int, ids: list[int]
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await administration.resolve_reports(
            ctx, actor_user_id=actor, level_id=level_id
        )
        for level_id in ids
    ]


async def _dismiss_many(
    ctx: AbstractContext, actor: int, ids: list[int]
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await administration.dismiss_suggestions(
            ctx, actor_user_id=actor, level_id=level_id
        )
        for level_id in ids
    ]


def _bulk(ids: list[int]) -> None:
    operator = current()

    if operator is None:
        return

    actor = operator.user_id
    st.markdown(f"#### Bulk actions · {len(ids)} selected")
    rate_tab, visibility_tab, timely_tab, danger_tab = st.tabs(
        ["Rate", "Visibility & lock", "Timely", "Delete"]
    )

    with rate_tab, st.form("bulk_rate"):
        stars = st.slider("Stars (0 removes the rating)", 0, 10, 5)
        feature = st.selectbox("Feature tier", list(_FEATURES))
        demon = st.selectbox("Demon tier (stars 10)", list(_DEMONS))

        if st.form_submit_button("Rate selected", type="primary"):
            outcomes = runtime.active().run(
                lambda ctx: _rate_many(
                    ctx,
                    actor,
                    ids,
                    stars,
                    _FEATURES[feature or "Keep"],
                    _DEMONS[demon or "Keep"],
                )
            )
            components.report_bulk(outcomes, "Rated")

    with visibility_tab:
        left, right = st.columns(2)

        with left, st.form("bulk_visibility"):
            visibility = components.choose(
                "Visibility", list(Visibility), lambda v: labels.VISIBILITY[v]
            )

            if st.form_submit_button("Apply visibility", type="primary"):
                outcomes = runtime.active().run(
                    lambda ctx: _visibility_many(ctx, actor, ids, visibility)
                )
                components.report_bulk(outcomes, "Updated")

        with right:
            lock_left, lock_right = st.columns(2)

            if lock_left.button("Lock updates", key="bulk_lock"):
                components.report_bulk(
                    runtime.active().run(lambda ctx: _lock_many(ctx, actor, ids, True)),
                    "Locked",
                )

            if lock_right.button("Unlock updates", key="bulk_unlock"):
                components.report_bulk(
                    runtime.active().run(
                        lambda ctx: _lock_many(ctx, actor, ids, False)
                    ),
                    "Unlocked",
                )

    with timely_tab, st.form("bulk_timely"):
        timely_type = components.choose(
            "Queue as", list(TimelyType), lambda t: labels.TIMELY[t]
        )
        st.markdown(
            theme.muted("Each level is appended to the queue in the order selected."),
            unsafe_allow_html=True,
        )

        if st.form_submit_button("Schedule selected", type="primary"):
            outcomes = runtime.active().run(
                lambda ctx: _schedule_many(ctx, actor, ids, timely_type)
            )
            components.report_bulk(outcomes, "Scheduled")

    with danger_tab:
        st.markdown(
            theme.muted(
                "Deleted levels vanish from every listing; their files stay in storage."
            ),
            unsafe_allow_html=True,
        )

        if components.confirm("Delete selected levels", "bulk_delete"):
            components.report_bulk(
                runtime.active().run(lambda ctx: _delete_many(ctx, actor, ids)),
                "Deleted",
            )
            st.rerun()


def _detail(level: Level, creator: User | None) -> None:
    st.markdown(
        theme.card(
            f"{level.name} #{level.id}",
            [
                ("Creator", creator.username if creator else f"#{level.user_id}"),
                ("Description", level.description or "—"),
                ("Version", str(level.version)),
                (
                    "Song",
                    f"custom {level.custom_song_id}"
                    if level.custom_song_id
                    else f"official {level.official_song_id}",
                ),
                ("Objects", str(level.object_count)),
                (
                    "Coins",
                    f"{level.coins} "
                    f"({'verified' if level.coins_verified else 'unverified'})",
                ),
                ("Requested stars", str(level.requested_stars)),
                (
                    "Editor time",
                    f"{level.editor_seconds // 3600}h "
                    f"{level.editor_seconds % 3600 // 60}m",
                ),
                ("Two player", "yes" if level.two_player else "no"),
                ("Copyable", "yes" if level.copyable else "no"),
                ("Client", f"{level.game_version} / {level.binary_version}"),
                ("Updated", components.stamp(level.updated_at)),
            ],
        ),
        unsafe_allow_html=True,
    )


def _queues_view() -> None:
    operator = current()

    if operator is None:
        return

    actor = operator.user_id
    queues = runtime.active().run(_queues)
    sent_tab, reported_tab = st.tabs(
        [f"Sent ({len(queues.suggestions)})", f"Reported ({len(queues.reported)})"]
    )

    with sent_tab:
        frame = pd.DataFrame(
            [
                {
                    "level": queues.levels[entry.level_id].name
                    if entry.level_id in queues.levels
                    else f"#{entry.level_id}",
                    "level id": entry.level_id,
                    "sent by": queues.users[entry.user_id].username
                    if entry.user_id in queues.users
                    else f"#{entry.user_id}",
                    "stars": entry.stars,
                    "feature": entry.feature.name.title()
                    if entry.feature is not None
                    else "",
                    "when": components.stamp(entry.created_at),
                }
                for entry in queues.suggestions
            ]
        )
        selected = components.table(frame, "sent_table")
        chosen = [queues.suggestions[index] for index in selected]

        if chosen:
            left, right = st.columns(2)

            if left.button("Rate as suggested", type="primary", key="sent_rate"):
                outcomes = runtime.active().run(
                    lambda ctx: _rate_suggested(ctx, actor, chosen)
                )
                components.report_bulk(outcomes, "Rated")
                st.rerun()

            if right.button("Dismiss", key="sent_dismiss"):
                components.report_bulk(
                    runtime.active().run(
                        lambda ctx: _dismiss_many(
                            ctx, actor, [entry.level_id for entry in chosen]
                        )
                    ),
                    "Dismissed",
                )
                st.rerun()

    with reported_tab:
        frame = pd.DataFrame(
            [
                {
                    "level": queues.levels[level_id].name
                    if level_id in queues.levels
                    else f"#{level_id}",
                    "level id": level_id,
                    "creator": queues.users[queues.levels[level_id].user_id].username
                    if level_id in queues.levels
                    and queues.levels[level_id].user_id in queues.users
                    else "",
                    "reports": reports,
                }
                for level_id, reports in queues.reported
            ]
        )
        selected = components.table(frame, "reported_table")
        chosen_ids = [queues.reported[index][0] for index in selected]

        if chosen_ids:
            left, right = st.columns(2)

            if left.button("Resolve reports", type="primary", key="reports_resolve"):
                components.report_bulk(
                    runtime.active().run(
                        lambda ctx: _resolve_many(ctx, actor, chosen_ids)
                    ),
                    "Resolved",
                )
                st.rerun()

            with right:
                if components.confirm("Delete reported levels", "reports_delete"):
                    components.report_bulk(
                        runtime.active().run(
                            lambda ctx: _delete_many(ctx, actor, chosen_ids)
                        ),
                        "Deleted",
                    )
                    st.rerun()


async def _rate_suggested(
    ctx: AbstractContext, actor: int, chosen: list[LevelSuggestion]
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await moderation.rate_level(
            ctx,
            actor_user_id=actor,
            level_id=entry.level_id,
            stars=entry.stars or 0,
            feature=entry.feature,
            demon=entry.demon_difficulty,
        )
        for entry in chosen
    ]


def page() -> None:
    components.header("Levels", "Search, rate, feature, schedule and moderate levels.")
    browse_tab, queue_tab = st.tabs(["Browse", "Queues"])

    with browse_tab:
        first, second, third, fourth = st.columns([3, 1, 1, 1])
        query = first.text_input("Name prefix or level id", placeholder="Saturation")
        order_label = second.selectbox("Order", list(_ORDERS))
        rated = third.selectbox("Rating", ["All", "Rated only", "Unrated only"])
        creator = fourth.text_input("Creator id")
        search = _search(
            query, _ORDERS[order_label or "Recent"], rated or "All", creator, 0
        )
        total = runtime.active().run(lambda ctx: ctx.levels.count(search))
        page_index = components.paginator("levels", total)
        listing = runtime.active().run(
            lambda ctx: _listing(ctx, replace(search, page=page_index))
        )
        selected = components.table(_frame(listing), "levels_table")
        chosen = [
            listing.levels[index] for index in selected if index < len(listing.levels)
        ]

        if len(chosen) == 1:
            _detail(chosen[0], listing.creators.get(chosen[0].user_id))

        if chosen:
            _bulk([level.id for level in chosen])

    with queue_tab:
        _queues_view()
