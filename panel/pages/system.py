from dataclasses import dataclass

import streamlit as st
from poltergeist_core import settings
from poltergeist_core.services import AbstractContext
from poltergeist_core.services import administration
from poltergeist_core.services import leaderboards
from poltergeist_core.utilities import clock

from panel import components
from panel import runtime
from panel import theme
from panel.auth import current


@dataclass(frozen=True, slots=True)
class Facts:
    mysql: bool
    redis: bool
    redis_facts: dict[str, str]


async def _facts(ctx: AbstractContext) -> Facts:
    redis_ok = await ctx.health.redis_available()

    return Facts(
        mysql=await ctx.health.mysql_available(),
        redis=redis_ok,
        redis_facts=await ctx.health.redis_facts() if redis_ok else {},
    )


def page() -> None:
    components.header("System", "Health, caches and housekeeping.")
    operator = current()

    if operator is None:
        return

    actor = operator.user_id
    facts = runtime.active().run(_facts)
    grid = st.columns(4)
    components.metric(grid[0], "MySQL", "up" if facts.mysql else "down")
    components.metric(grid[1], "Redis", "up" if facts.redis else "down")
    components.metric(
        grid[2], "Redis memory", facts.redis_facts.get("used_memory_human", "?")
    )
    components.metric(grid[3], "Redis keys", facts.redis_facts.get("keys", "?"))

    config_column, actions_column = st.columns([3, 2], border=True)

    with config_column:
        st.markdown("#### Configuration")
        components.facts(
            [
                ("Public URL", settings.APP_PUBLIC_URL),
                ("Server name", settings.APP_SERVER_NAME),
                ("Command prefix", settings.APP_COMMAND_PREFIX),
                (
                    "Minimum client",
                    f"game {settings.APP_MIN_GAME_VERSION}, "
                    f"binary {settings.APP_MIN_BINARY_VERSION}",
                ),
                (
                    "Chest cooldowns",
                    f"small {settings.APP_SMALL_CHEST_SECONDS}s, "
                    f"large {settings.APP_LARGE_CHEST_SECONDS}s",
                ),
                ("Level limit", f"{settings.APP_LEVEL_MAX_BYTES:,} bytes"),
                ("Save limit", f"{settings.APP_SAVE_MAX_BYTES:,} bytes"),
                ("Session cache", f"{settings.APP_SESSION_SECONDS}s"),
                ("Server time", f"{clock.now():%Y-%m-%d %H:%M:%S} UTC"),
            ]
        )

    with actions_column:
        st.markdown("#### Leaderboards")
        st.markdown(
            theme.muted(
                "Rebuilds every ranking from MySQL. Safe while players are online."
            ),
            unsafe_allow_html=True,
        )

        if st.button("Rebuild leaderboards", type="primary", width="stretch"):
            total = runtime.active().run(leaderboards.rebuild)
            st.success(f"Ranked {total} players.")

        st.divider()
        st.markdown("#### Force a player to re-authenticate")

        with st.form("revoke", border=False):
            user_id = st.number_input("User id", min_value=1, step=1)

            if st.form_submit_button(
                "Revoke sessions and permission cache", width="stretch"
            ):
                components.report(
                    runtime.active().run(
                        lambda ctx: administration.revoke_sessions(
                            ctx, actor_user_id=actor, user_id=int(user_id)
                        )
                    ),
                    "Revoked.",
                )
