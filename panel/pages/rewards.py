from dataclasses import dataclass
from datetime import datetime
from datetime import time

import pandas as pd
import streamlit as st
from gdformat.enums import ChestType
from gdformat.enums import QuestItem
from gdformat.enums import RewardItem

from app.resources import Quest
from app.resources import SecretReward
from app.services import AbstractContext
from app.services import ServiceError
from app.services import administration
from panel import components
from panel import runtime
from panel.auth import current

_ITEMS = {
    "Orbs": RewardItem.ORBS,
    "Diamonds": RewardItem.DIAMONDS,
    "Fire shard": RewardItem.FIRE_SHARD,
    "Ice shard": RewardItem.ICE_SHARD,
    "Poison shard": RewardItem.POISON_SHARD,
    "Shadow shard": RewardItem.SHADOW_SHARD,
    "Lava shard": RewardItem.LAVA_SHARD,
    "Earth shard": RewardItem.EARTH_SHARD,
    "Blood shard": RewardItem.BLOOD_SHARD,
    "Metal shard": RewardItem.METAL_SHARD,
    "Light shard": RewardItem.LIGHT_SHARD,
    "Soul shard": RewardItem.SOUL_SHARD,
    "Demon key": RewardItem.DEMON_KEY,
    "Gold key": RewardItem.GOLD_KEY,
}
_ITEM_SLOTS = 3


@dataclass(frozen=True, slots=True)
class Rewards:
    quests: list[Quest]
    secrets: list[SecretReward]
    claims: dict[int, int]


async def _load(ctx: AbstractContext) -> Rewards:
    secrets = await ctx.secret_rewards.list_all()

    return Rewards(
        quests=await ctx.quests.list_active(),
        secrets=secrets,
        claims={
            reward.id: await ctx.secret_rewards.count_claims(reward.id)
            for reward in secrets
        },
    )


async def _remove_quests(
    ctx: AbstractContext, actor: int, ids: list[int]
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await administration.remove_quest(ctx, actor_user_id=actor, quest_id=quest_id)
        for quest_id in ids
    ]


async def _remove_secrets(
    ctx: AbstractContext, actor: int, ids: list[int]
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await administration.remove_secret_reward(
            ctx, actor_user_id=actor, reward_id=reward_id
        )
        for reward_id in ids
    ]


def _quests(rewards: Rewards, actor: int) -> None:
    st.markdown("#### Quests")
    frame = pd.DataFrame(
        [
            {
                "id": quest.id,
                "name": quest.name,
                "item": quest.item.name.title(),
                "amount": quest.amount,
                "diamonds": quest.diamonds,
            }
            for quest in rewards.quests
        ]
    )
    selected = components.table(frame, "quests_table")
    chosen = [rewards.quests[index].id for index in selected]

    if chosen and components.confirm("Remove selected quests", "quests_remove"):
        components.report_bulk(
            runtime.active().run(lambda ctx: _remove_quests(ctx, actor, chosen)),
            "Removed",
        )
        st.rerun()

    with st.form("quest_create", border=False):
        st.markdown("**New quest**")
        left, right = st.columns(2)
        name = left.text_input("Name", max_chars=64)

        with right:
            item = components.choose("Item", list(QuestItem), lambda i: i.name.title())

        left, right = st.columns(2)
        amount = left.number_input("Amount", min_value=1, value=100)
        diamonds = right.number_input("Diamonds", min_value=1, max_value=255, value=5)

        if st.form_submit_button("Create quest", type="primary", width="stretch"):
            components.report(
                runtime.active().run(
                    lambda ctx: administration.create_quest(
                        ctx,
                        actor_user_id=actor,
                        item=item,
                        amount=int(amount),
                        diamonds=int(diamonds),
                        name=name,
                    )
                ),
                "Quest created.",
            )
            st.rerun()


def _secrets(rewards: Rewards, actor: int) -> None:
    st.markdown("#### Vault codes")
    frame = pd.DataFrame(
        [
            {
                "id": reward.id,
                "code": reward.reward_key,
                "chest": reward.chest_type.name.title(),
                "claims": rewards.claims.get(reward.id, 0),
                "max": "∞" if reward.max_claims is None else str(reward.max_claims),
                "expires": "never"
                if reward.expires_at is None
                else components.stamp(reward.expires_at),
            }
            for reward in rewards.secrets
        ]
    )
    selected = components.table(frame, "secrets_table")
    chosen = [rewards.secrets[index].id for index in selected]

    if chosen and components.confirm("Remove selected codes", "secrets_remove"):
        components.report_bulk(
            runtime.active().run(lambda ctx: _remove_secrets(ctx, actor, chosen)),
            "Removed",
        )
        st.rerun()

    with st.form("secret_create", border=False):
        st.markdown("**New vault code**")
        left, right = st.columns(2)
        key = left.text_input("Code (typed by players)", max_chars=64)

        with right:
            chest = components.choose(
                "Chest look",
                [ChestType.SMALL, ChestType.LARGE],
                lambda c: c.name.title(),
            )

        left, right = st.columns(2)
        max_claims = left.number_input(
            "Max claims (0 = unlimited)", min_value=0, value=0
        )
        expires = right.date_input("Expires on (optional)", value=None)
        picks = []

        for slot in range(_ITEM_SLOTS):
            left, right = st.columns([2, 1])

            with left:
                label = components.choose(
                    f"Item {slot + 1}",
                    ["None", *_ITEMS],
                    lambda i: i,
                    key=f"secret_item_{slot}",
                )

            amount = right.number_input(
                "Amount", min_value=1, value=100, key=f"secret_amount_{slot}"
            )

            if label != "None":
                picks.append((_ITEMS[label], int(amount)))

        if st.form_submit_button("Create code", type="primary", width="stretch"):
            expiry = None if expires is None else datetime.combine(expires, time.max)
            components.report(
                runtime.active().run(
                    lambda ctx: administration.create_secret_reward(
                        ctx,
                        actor_user_id=actor,
                        reward_key=key,
                        chest_type=chest,
                        items=picks,
                        max_claims=int(max_claims) or None,
                        expires_at=expiry,
                    )
                ),
                "Code created.",
            )
            st.rerun()


def page() -> None:
    components.header("Rewards", "Daily quests and vault codes.")
    operator = current()

    if operator is None:
        return

    rewards = runtime.active().run(_load)
    quests_column, secrets_column = st.columns(2, border=True)

    with quests_column:
        _quests(rewards, operator.user_id)

    with secrets_column:
        _secrets(rewards, operator.user_id)
