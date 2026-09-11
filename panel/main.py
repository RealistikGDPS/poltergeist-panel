import streamlit as st

from app import settings
from app.utilities import logging
from panel import auth
from panel import runtime
from panel import theme
from panel.pages import comments
from panel.pages import dashboard
from panel.pages import levels
from panel.pages import moderation
from panel.pages import packs
from panel.pages import rewards
from panel.pages import roles
from panel.pages import songs
from panel.pages import system
from panel.pages import timely
from panel.pages import users

logging.configure_from_yaml()


def _sidebar(operator: auth.Operator) -> None:
    with st.sidebar:
        st.markdown('<div class="pg-brand">POLTERGEIST</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="pg-sub">{settings.APP_SERVER_NAME} control room</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="pg-user">Signed in as <b>{operator.username}</b> '
            f"<span class='pg-muted'>#{operator.user_id}</span></div>",
            unsafe_allow_html=True,
        )

        if st.button("Sign out", width="stretch"):
            auth.sign_out()
            st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Poltergeist control room",
        page_icon="👻",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    active = runtime.active()
    operator = auth.require(active)
    theme.apply()
    _sidebar(operator)

    pages = [
        st.Page(dashboard.page, title="Dashboard", icon="📊", default=True),
        st.Page(users.page, title="Users", icon="👤", url_path="users"),
        st.Page(levels.page, title="Levels", icon="🧱", url_path="levels"),
        st.Page(comments.page, title="Comments", icon="💬", url_path="comments"),
        st.Page(moderation.page, title="Moderation", icon="🛡️", url_path="moderation"),
        st.Page(timely.page, title="Timely", icon="📅", url_path="timely"),
        st.Page(songs.page, title="Songs", icon="🎵", url_path="songs"),
        st.Page(rewards.page, title="Rewards", icon="🎁", url_path="rewards"),
        st.Page(packs.page, title="Packs", icon="📦", url_path="packs"),
        st.Page(roles.page, title="Roles", icon="🔑", url_path="roles"),
        st.Page(system.page, title="System", icon="⚙️", url_path="system"),
    ]
    st.navigation(pages, position="sidebar").run()


main()
