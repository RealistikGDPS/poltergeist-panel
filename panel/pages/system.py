from dataclasses import dataclass

import streamlit as st

from app import settings
from app.services import AbstractContext
from app.services import administration
from app.services import leaderboards
from app.utilities import clock
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
    first, second, third, fourth = st.columns(4)
    first.metric("MySQL", "up" if facts.mysql else "down")
    second.metric("Redis", "up" if facts.redis else "down")
    third.metric("Redis memory", facts.redis_facts.get("used_memory_human", "?"))
    fourth.metric("Redis keys", facts.redis_facts.get("keys", "?"))

    st.markdown(
        theme.card(
            "Configuration",
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
            ],
        ),
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)

    with left:
        st.markdown("#### Leaderboards")
        st.markdown(
            theme.muted(
                "Rebuilds every ranking from MySQL. Safe while players are online."
            ),
            unsafe_allow_html=True,
        )

        if st.button("Rebuild leaderboards", type="primary"):
            total = runtime.active().run(leaderboards.rebuild)
            st.success(f"Ranked {total} players.")

    with right, st.form("revoke"):
        st.markdown("#### Force a player to re-authenticate")
        user_id = st.number_input("User id", min_value=1, step=1)

        if st.form_submit_button("Revoke sessions and permission cache"):
            components.report(
                runtime.active().run(
                    lambda ctx: administration.revoke_sessions(
                        ctx, actor_user_id=actor, user_id=int(user_id)
                    )
                ),
                "Revoked.",
            )
