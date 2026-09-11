from dataclasses import dataclass

import pandas as pd
import streamlit as st

from app.resources import Song
from app.services import AbstractContext
from app.services import ServiceError
from app.services import administration
from app.services import songs
from panel import components
from panel import runtime
from panel import theme
from panel.auth import current

_BYTES_PER_MB = 1_048_576


@dataclass(frozen=True, slots=True)
class Listing:
    songs: list[Song]
    total: int


async def _listing(ctx: AbstractContext, query: str, page: int) -> Listing:
    return Listing(
        songs=await ctx.songs.list_page(
            query=query, page=page, size=components.PAGE_SIZE
        ),
        total=await ctx.songs.count_page(query=query),
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


def page() -> None:
    components.header(
        "Songs", "Newgrounds, library and custom songs known to the server."
    )
    operator = current()

    if operator is None:
        return

    actor = operator.user_id
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

    if chosen:
        left, right = st.columns(2)

        if left.button("Disable selected", type="primary"):
            components.report_bulk(
                runtime.active().run(
                    lambda ctx: _toggle_many(ctx, actor, chosen, True)
                ),
                "Disabled",
            )
            st.rerun()

        if right.button("Enable selected"):
            components.report_bulk(
                runtime.active().run(
                    lambda ctx: _toggle_many(ctx, actor, chosen, False)
                ),
                "Enabled",
            )
            st.rerun()

    left, right = st.columns(2)

    with left, st.form("custom_song"):
        st.markdown("#### Add a custom song")
        name = st.text_input("Name")
        artist = st.text_input("Artist")
        url = st.text_input("Direct audio URL")
        size = st.number_input("Size in MB", min_value=0.0, value=3.0, step=0.1)

        if st.form_submit_button("Create", type="primary"):
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

    with right, st.form("fetch_song"):
        st.markdown("#### Fetch from the official servers")
        st.markdown(
            theme.muted(
                "Caches a Newgrounds song's metadata if the upstream is reachable."
            ),
            unsafe_allow_html=True,
        )
        song_id = st.number_input("Song id", min_value=1, step=1)

        if st.form_submit_button("Fetch"):
            song = runtime.active().run(lambda ctx: songs.ensure(ctx, int(song_id)))

            if song is None:
                st.error("The song could not be fetched.")
            else:
                st.success(f"{song.name} by {song.artist_name} is known.")
