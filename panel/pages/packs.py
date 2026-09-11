from dataclasses import dataclass

import pandas as pd
import streamlit as st
from gdformat.enums import MapPackDifficulty

from app.resources import Gauntlet
from app.resources import MapPack
from app.services import AbstractContext
from app.services import ServiceError
from app.services import administration
from app.services import packs
from panel import components
from panel import labels
from panel import runtime
from panel.auth import current


@dataclass(frozen=True, slots=True)
class Packs:
    map_packs: list[MapPack]
    pack_levels: dict[int, list[int]]
    gauntlets: list[Gauntlet]


async def _load(ctx: AbstractContext) -> Packs:
    map_packs = await ctx.map_packs.list_all()

    return Packs(
        map_packs=map_packs,
        pack_levels=await ctx.map_packs.list_level_ids_many(
            [pack.id for pack in map_packs]
        ),
        gauntlets=await ctx.gauntlets.list_all(),
    )


async def _remove_packs(
    ctx: AbstractContext, actor: int, ids: list[int]
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await administration.remove_map_pack(ctx, actor_user_id=actor, pack_id=pack_id)
        for pack_id in ids
    ]


async def _remove_gauntlets(
    ctx: AbstractContext, actor: int, ids: list[int]
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await administration.remove_gauntlet(
            ctx, actor_user_id=actor, gauntlet_id=gauntlet_id
        )
        for gauntlet_id in ids
    ]


def _colour(text: str) -> int:
    return int(text.lstrip("#"), 16)


def _map_packs(loaded: Packs, actor: int) -> None:
    st.markdown("#### Map packs")
    frame = pd.DataFrame(
        [
            {
                "id": pack.id,
                "name": pack.name,
                "stars": pack.stars,
                "coins": pack.coins,
                "difficulty": pack.difficulty.name.replace("_", " ").title(),
                "levels": ", ".join(map(str, loaded.pack_levels.get(pack.id, []))),
            }
            for pack in loaded.map_packs
        ]
    )
    selected = components.table(frame, "packs_table")
    chosen = [loaded.map_packs[index].id for index in selected]

    if chosen and components.confirm("Remove selected packs", "packs_remove"):
        components.report_bulk(
            runtime.active().run(lambda ctx: _remove_packs(ctx, actor, chosen)),
            "Removed",
        )
        st.rerun()

    with st.form("pack_create", border=False):
        st.markdown("**New map pack**")
        name = st.text_input("Name", max_chars=64)
        left, middle, right = st.columns(3)
        stars = left.number_input("Stars", min_value=0, max_value=10, value=3)
        coins = middle.number_input("Coins", min_value=0, max_value=2, value=1)

        with right:
            difficulty = components.choose(
                "Difficulty",
                list(MapPackDifficulty),
                lambda d: d.name.replace("_", " ").title(),
            )

        level_text = st.text_input("Level ids, comma separated")
        left, right = st.columns(2)
        text_colour = left.color_picker("Text colour", "#ffffff")
        bar_colour = right.color_picker("Bar colour", "#b48cff")

        if st.form_submit_button("Create pack", type="primary", width="stretch"):
            components.report(
                runtime.active().run(
                    lambda ctx: packs.create_map_pack(
                        ctx,
                        actor_user_id=actor,
                        name=name,
                        level_ids=components.parse_ids(level_text),
                        stars=int(stars),
                        coins=int(coins),
                        difficulty=difficulty,
                        text_colour=_colour(text_colour),
                        bar_colour=_colour(bar_colour),
                    )
                ),
                "Map pack created.",
            )
            st.rerun()


def _gauntlets(loaded: Packs, actor: int) -> None:
    st.markdown("#### Gauntlets")
    frame = pd.DataFrame(
        [
            {
                "id": gauntlet.id,
                "name": labels.gauntlet(gauntlet.id),
                "levels": ", ".join(map(str, gauntlet.level_ids)),
            }
            for gauntlet in loaded.gauntlets
        ]
    )
    selected = components.table(frame, "gauntlets_table")
    chosen = [loaded.gauntlets[index].id for index in selected]

    if chosen and components.confirm("Remove selected gauntlets", "gauntlets_remove"):
        components.report_bulk(
            runtime.active().run(lambda ctx: _remove_gauntlets(ctx, actor, chosen)),
            "Removed",
        )
        st.rerun()

    with st.form("gauntlet_set", border=False):
        st.markdown("**Set a gauntlet**")
        gauntlet_id = components.choose("Gauntlet", list(range(1, 61)), labels.gauntlet)
        level_text = st.text_input("Exactly five level ids, comma separated")

        if st.form_submit_button("Save gauntlet", type="primary", width="stretch"):
            components.report(
                runtime.active().run(
                    lambda ctx: packs.set_gauntlet(
                        ctx,
                        actor_user_id=actor,
                        gauntlet_id=int(gauntlet_id),
                        level_ids=components.parse_ids(level_text),
                    )
                ),
                "Gauntlet saved.",
            )
            st.rerun()


def page() -> None:
    components.header("Packs", "Map packs and gauntlets.")
    operator = current()

    if operator is None:
        return

    loaded = runtime.active().run(_load)
    packs_column, gauntlets_column = st.columns(2, border=True)

    with packs_column:
        _map_packs(loaded, operator.user_id)

    with gauntlets_column:
        _gauntlets(loaded, operator.user_id)
