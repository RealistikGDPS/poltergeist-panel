from dataclasses import dataclass

import pandas as pd
import streamlit as st
from poltergeist_core.resources import Song
from poltergeist_core.services import AbstractContext
from poltergeist_core.services import ServiceError
from poltergeist_core.services import administration
from poltergeist_core.services import songs

from panel import components
from panel import runtime
from panel import theme
from panel.auth import current

_BYTES_PER_MB = 1_048_576


@dataclass(frozen=True, slots=True)
class Listing:
    songs: list[Song]


async def _listing(ctx: AbstractContext, query: str, page: int) -> Listing:
    return Listing(
        songs=await ctx.songs.list_page(
            query=query, page=page, size=components.PAGE_SIZE
        )
    )


async def _toggle_many(
    ctx: AbstractContext, actor: int, ids: list[int], disabled: bool
) -> list[ServiceError.OnSuccess[object]]:
    return [
        await administration.set_song_disabled(
            ctx, actor_user_id=actor, song_id=song_id, disabled=disabled
        )
        for song_id in ids
    ]


def _editor(song: Song, actor: int) -> None:
    with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
        st.markdown(f"#### Edit song {song.id}")
        st.badge(song.source.value, color="gray")

    with st.form(f"song_{song.id}", border=False):
        left, right = st.columns(2)
        name = left.text_input("Name", value=song.name, max_chars=128)
        artist = right.text_input("Artist", value=song.artist_name, max_chars=64)
        url = st.text_input("Direct audio URL", value=song.url, max_chars=512)
        size = st.number_input(
            "Size in MB",
            min_value=0.0,
            value=round(song.size_bytes / _BYTES_PER_MB, 2),
            step=0.1,
        )

        if st.form_submit_button("Save song", type="primary", width="stretch"):
            components.report(
                runtime.active().run(
                    lambda ctx: administration.update_song(
                        ctx,
                        actor_user_id=actor,
                        song_id=song.id,
                        name=name,
                        artist_name=artist,
                        url=url,
                        size_bytes=int(size * _BYTES_PER_MB),
                    )
                ),
                "Song saved.",
            )
            st.rerun()


def page() -> None:
    components.header(
        "Songs",
        "Newgrounds, library and custom songs known to the server. "
        "Select one row to edit it.",
    )
    operator = current()

    if operator is None:
        return

    actor = operator.user_id

    with components.toolbar():
        query = st.text_input("Search by name, artist or id")
        total = runtime.active().run(lambda ctx: ctx.songs.count_page(query=query))
        page_index = components.paginator("songs", total)

    listing = runtime.active().run(lambda ctx: _listing(ctx, query, page_index))
    frame = pd.DataFrame(
        [
            {
                "id": song.id,
                "name": song.name,
                "artist": song.artist_name,
                "source": song.source.value,
                "size MB": round(song.size_bytes / _BYTES_PER_MB, 2),
                "disabled": song.disabled_at is not None,
                "url": song.url,
            }
            for song in listing.songs
        ]
    )
    selected = components.table(frame, "songs_table")
    chosen = [listing.songs[index].id for index in selected]

    if len(selected) == 1:
        with st.container(border=True):
            _editor(listing.songs[selected[0]], actor)

    if chosen:
        with st.container(horizontal=True, gap="small"):
            components.badges([f"{len(chosen)} selected"], "blue")

            if st.button("Disable selected", type="primary"):
                components.report_bulk(
                    runtime.active().run(
                        lambda ctx: _toggle_many(ctx, actor, chosen, True)
                    ),
                    "Disabled",
                )
                st.rerun()

            if st.button("Enable selected"):
                components.report_bulk(
                    runtime.active().run(
                        lambda ctx: _toggle_many(ctx, actor, chosen, False)
                    ),
                    "Enabled",
                )
                st.rerun()

    create_column, fetch_column = st.columns(2, border=True)

    with create_column, st.form("custom_song", border=False):
        st.markdown("#### Add a custom song")
        left, right = st.columns(2)
        name = left.text_input("Name")
        artist = right.text_input("Artist")
        url = st.text_input("Direct audio URL")
        size = st.number_input("Size in MB", min_value=0.0, value=3.0, step=0.1)

        if st.form_submit_button("Create", type="primary", width="stretch"):
            components.report(
                runtime.active().run(
                    lambda ctx: songs.create_custom(
                        ctx,
                        name=name,
                        artist_name=artist,
                        url=url,
                        size_bytes=int(size * _BYTES_PER_MB),
                        uploaded_by_user_id=actor,
                    )
                ),
                "Song created.",
            )

    with fetch_column, st.form("fetch_song", border=False):
        st.markdown("#### Fetch from the official servers")
        st.markdown(
            theme.muted(
                "Caches a Newgrounds song's metadata if the upstream is reachable."
            ),
            unsafe_allow_html=True,
        )
        song_id = st.number_input("Song id", min_value=1, step=1)

        if st.form_submit_button("Fetch", width="stretch"):
            song = runtime.active().run(lambda ctx: songs.ensure(ctx, int(song_id)))

            if song is None:
                st.error("The song could not be fetched.")
            else:
                st.success(f"{song.name} by {song.artist_name} is known.")
