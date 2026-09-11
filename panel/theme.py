import html

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp { font-family: 'Inter', system-ui, sans-serif; }
code, pre, .stCode { font-family: 'JetBrains Mono', monospace; }
header[data-testid="stHeader"] { background: #0f0c19; border-bottom: 1px solid #2c2447; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-bottom: 2rem; }

.pg-brand { font-weight: 600; letter-spacing: .12em; font-size: 1rem; color: #ece4ff; }
.pg-sub { color: #9f8cc9; font-size: .75rem; letter-spacing: .1em; text-transform: uppercase; }
.pg-muted { color: #9f8cc9; font-size: .85rem; }
.pg-title { font-size: 1.5rem; font-weight: 600; color: #ece4ff; margin: 0; }

div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #2c2447 !important; border-radius: 12px; background: #18132a; }
div[data-testid="stMetric"] { background: #0f0c19; border-radius: 12px; }
div[data-testid="stMetric"] label { color: #9f8cc9 !important; letter-spacing: .06em; text-transform: uppercase; font-size: .7rem; }
div[data-testid="stMetricValue"] { color: #ece4ff; font-weight: 600; }

.stTabs [data-baseweb="tab-list"] { gap: 1.2rem; }

.pg-kv { display: grid; grid-template-columns: max-content 1fr; gap: .35rem 1.2rem; font-size: .9rem; margin-bottom: 1rem; }
.pg-kv span:nth-child(odd) { color: #9f8cc9; }
</style>
"""


def apply() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def muted(text: str) -> str:
    return f'<span class="pg-muted">{html.escape(text)}</span>'


def title(text: str) -> str:
    return f'<p class="pg-title">{html.escape(text)}</p>'


def facts(rows: list[tuple[str, str]]) -> str:
    cells = "".join(
        f"<span>{html.escape(key)}</span><span>{html.escape(value)}</span>"
        for key, value in rows
    )

    return f'<div class="pg-kv">{cells}</div>'
