from dataclasses import dataclass

import pandas as pd
import streamlit as st

from app.resources import Permission
from app.resources import Role
from app.resources import User
from app.services import AbstractContext
from app.services import administration
from panel import components
from panel import runtime
from panel import theme
from panel.auth import current


@dataclass(frozen=True, slots=True)
class Roles:
    roles: list[Role]
    permissions: dict[int, list[str]]
    members: dict[int, int]


async def _load(ctx: AbstractContext) -> Roles:
    roles = await ctx.roles.list_all()

    return Roles(
        roles=roles,
        permissions={
            role.id: await ctx.roles.list_permissions(role.id) for role in roles
        },
        members={role.id: await ctx.roles.count_members(role.id) for role in roles},
    )


async def _members(ctx: AbstractContext, role_id: int) -> list[User]:
    ids = await ctx.roles.list_member_ids(role_id)

    return await ctx.users.find_many_by_ids(ids[:200])


def _editor(role: Role, granted: list[str], actor: int) -> None:
    with st.form(f"role_{role.id}"):
        st.markdown(f"#### Edit `{role.name}`")
        first, second = st.columns([2, 1])
        name = first.text_input("Name", value=role.name, max_chars=32)
        priority = second.number_input("Priority", value=role.priority, step=1)
        description = st.text_input(
            "Description", value=role.description, max_chars=255
        )
        text = st.text_area(
            "Permissions, one per line (`levels.*` and `*` are wildcards)",
            value="\n".join(granted),
            height=220,
        )

        if st.form_submit_button("Save role", type="primary"):
            components.report(
                runtime.active().run(
                    lambda ctx: administration.update_role(
                        ctx,
                        actor_user_id=actor,
                        role_id=role.id,
                        name=name,
                        description=description,
                        priority=int(priority),
                        granted=text.split("\n"),
                    )
                ),
                "Role saved; members' permissions refreshed.",
            )
            st.rerun()

    members = runtime.active().run(lambda ctx: _members(ctx, role.id))
    st.markdown(
        theme.muted(f"{len(members)} member(s) shown: ")
        + components.pills([user.username for user in members][:60]),
        unsafe_allow_html=True,
    )

    if role.name != "default" and components.confirm(
        f"Remove role {role.name}", f"remove_{role.id}"
    ):
        components.report(
            runtime.active().run(
                lambda ctx: administration.remove_role(
                    ctx, actor_user_id=actor, role_id=role.id
                )
            ),
            "Role removed.",
        )
        st.rerun()


def page() -> None:
    components.header("Roles", "Who may do what. Permissions are dotted strings.")
    operator = current()

    if operator is None:
        return

    actor = operator.user_id
    loaded = runtime.active().run(_load)
    frame = pd.DataFrame(
        [
            {
                "id": role.id,
                "name": role.name,
                "priority": role.priority,
                "members": loaded.members.get(role.id, 0),
                "permissions": len(loaded.permissions.get(role.id, [])),
                "description": role.description,
            }
            for role in loaded.roles
        ]
    )
    selected = components.table(frame, "roles_table", multi=False)

    if selected:
        role = loaded.roles[selected[0]]
        _editor(role, loaded.permissions.get(role.id, []), actor)

    with st.form("role_create"):
        st.markdown("#### New role")
        first, second = st.columns([2, 1])
        name = first.text_input("Name (lowercase, underscores)", max_chars=32)
        priority = second.number_input("Priority", value=10, step=1)
        description = st.text_input("Description", max_chars=255)
        text = st.text_area("Permissions, one per line", height=140)

        if st.form_submit_button("Create role", type="primary"):
            components.report(
                runtime.active().run(
                    lambda ctx: administration.create_role(
                        ctx,
                        actor_user_id=actor,
                        name=name,
                        description=description,
                        priority=int(priority),
                        granted=text.split("\n"),
                    )
                ),
                "Role created.",
            )
            st.rerun()

    with st.expander("Permissions the server checks"):
        st.code("\n".join(permission.value for permission in Permission))
