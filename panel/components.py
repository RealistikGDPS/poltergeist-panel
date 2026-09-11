from collections.abc import Callable
from collections.abc import Sequence
from datetime import datetime

import pandas as pd
import streamlit as st
from gdformat import encoding

from app.services import ServiceError
from app.services import is_error
from app.utilities import clock
from panel import theme

PAGE_SIZE = 50


def header(title: str, subtitle: str) -> None:
    st.markdown(f"## {title}")
    st.markdown(theme.muted(subtitle), unsafe_allow_html=True)


def age(moment: datetime | None) -> str:
    if moment is None:
        return "never"

    return f"{encoding.describe_age(clock.seconds_since(moment))} ago"


def stamp(moment: datetime | None) -> str:
    return "" if moment is None else moment.strftime("%Y-%m-%d %H:%M")


def paginator(key: str, total: int, size: int = PAGE_SIZE) -> int:
    pages = max((total + size - 1) // size, 1)
    left, right = st.columns([1, 3])

    with left:
        page = st.number_input(
            "Page", min_value=1, max_value=pages, value=1, step=1, key=f"{key}_page"
        )

    with right:
        st.write("")
        st.markdown(
            theme.muted(f"{total} rows, page {page} of {pages}"), unsafe_allow_html=True
        )

    return int(page) - 1


def table(frame: pd.DataFrame, key: str, *, multi: bool = True) -> list[int]:
    """Renders a selectable table and returns the selected row positions."""

    if frame.empty:
        st.info("Nothing matches.")

        return []

    event = st.dataframe(
        frame,
        key=key,
        hide_index=True,
        width="stretch",
        on_select="rerun",
        selection_mode="multi-row" if multi else "single-row",
    )
    rows: Sequence[int] = event.selection.rows

    return list(rows)


def report(result: ServiceError.OnSuccess[object], success: str) -> bool:
    """Shows the outcome of one service call and reports whether it succeeded."""

    if is_error(result):
        st.error(f"Refused: {result.resolve_name()}")

        return False

    st.toast(success, icon="✅")

    return True


def report_bulk(outcomes: Sequence[ServiceError.OnSuccess[object]], verb: str) -> None:
    refused = [outcome for outcome in outcomes if is_error(outcome)]
    done = len(outcomes) - len(refused)

    if done:
        st.toast(f"{verb} {done} of {len(outcomes)}.", icon="✅")

    if refused:
        reasons = sorted({outcome.resolve_name() for outcome in refused})
        st.error(f"{len(refused)} refused: {', '.join(reasons)}")


def confirm(label: str, key: str, *, danger: bool = True) -> bool:
    """A popover holding a confirmation button for destructive bulk actions."""

    with st.popover(label, width="stretch"):
        if danger:
            st.warning("This cannot be undone from the panel.")

        return st.button("Confirm", key=f"{key}_confirm", type="primary")


def pills(labels: Sequence[str], kind: str = "info") -> str:
    return " ".join(theme.pill(label, kind) for label in labels)


def choose[T](
    label: str,
    options: Sequence[T],
    describe: Callable[[T], str],
    *,
    key: str | None = None,
) -> T:
    """A select box that always yields one of its options."""

    chosen = st.selectbox(label, options, format_func=describe, key=key)

    return options[0] if chosen is None else chosen


def parse_ids(text: str) -> list[int]:
    parts = text.replace("\n", ",").replace(" ", ",").split(",")

    return [int(part) for part in parts if part.strip().isdecimal()]
