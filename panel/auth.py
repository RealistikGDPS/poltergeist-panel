from dataclasses import dataclass

import streamlit as st
from gdformat import crypto
from gdformat.requests import Client
from gdformat.requests import LoginRequest

from app.resources import Permission
from app.services import auth
from app.services import is_error
from app.services.auth import Session
from app.services.auth import User
from panel import theme
from panel.runtime import Runtime

_KEY = "operator"


@dataclass(frozen=True, slots=True)
class Operator:
    """The signed-in panel user. Every action runs as this account, so the
    game's permissions and event log apply unchanged."""

    user_id: int
    username: str


def current() -> Operator | None:
    operator = st.session_state.get(_KEY)

    return operator if isinstance(operator, Operator) else None


def session_for(user: User) -> Session:
    """A game session for the operator, so services that expect one apply
    their usual permission checks to panel actions."""

    return Session(user=user, client=Client())


def sign_in(runtime: Runtime, username: str, password: str) -> str | None:
    """Returns a message when the sign-in is refused."""

    request = LoginRequest(client=Client(), name=username, gjp2=crypto.gjp2(password))
    result = runtime.run(lambda ctx: auth.login(ctx, request))

    if is_error(result):
        return "Those credentials were not accepted."

    user_id = result.user_id

    allowed = runtime.run(
        lambda ctx: ctx.permissions.has(user_id, Permission.PANEL_ACCESS)
    )

    if not allowed:
        return "This account is not allowed to use the panel."

    st.session_state[_KEY] = Operator(user_id=user_id, username=username.strip())

    return None


def sign_out() -> None:
    st.session_state.pop(_KEY, None)


def require(runtime: Runtime) -> Operator:
    """Renders the sign-in screen and halts the script until someone with
    panel access has signed in."""

    operator = current()

    if operator is not None:
        return operator

    theme.apply()
    _, column, _ = st.columns([1, 1.2, 1])

    with column, st.container(border=True):
        st.markdown('<div class="pg-brand">POLTERGEIST</div>', unsafe_allow_html=True)
        st.markdown('<div class="pg-sub">Control room</div>', unsafe_allow_html=True)
        st.space("small")

        with st.form("sign_in", border=False):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(
                "Sign in", type="primary", width="stretch"
            )

        if submitted:
            refusal = sign_in(runtime, username, password)

            if refusal is None:
                st.rerun()

            st.error(refusal)

        st.caption(
            "Sign in with your game account. It needs the `panel.access` permission."
        )

    st.stop()
