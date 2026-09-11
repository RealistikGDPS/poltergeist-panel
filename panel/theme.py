import html

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp { font-family: 'Inter', system-ui, sans-serif; }
code, pre, .stCode { font-family: 'JetBrains Mono', monospace; }
header[data-testid="stHeader"] { background: #131314; border-bottom: 1px solid #2e2f31; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-bottom: 2rem; }

.pg-brand { font-weight: 600; letter-spacing: .12em; font-size: 1rem; color: #e3e3e3; }
.pg-sub { color: #9aa0a6; font-size: .75rem; letter-spacing: .1em; text-transform: uppercase; }
.pg-muted { color: #9aa0a6; font-size: .85rem; }
.pg-title { font-size: 1.5rem; font-weight: 600; color: #e3e3e3; margin: 0; }

div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #2e2f31 !important; border-radius: 12px; background: #1e1f20; }
div[data-testid="stMetric"] { background: #131314; border-radius: 12px; }
div[data-testid="stMetric"] label { color: #9aa0a6 !important; letter-spacing: .06em; text-transform: uppercase; font-size: .7rem; }
div[data-testid="stMetricValue"] { color: #e3e3e3; font-weight: 600; }

.stTabs [data-baseweb="tab-list"] { gap: 1.2rem; }

.pg-kv { display: grid; grid-template-columns: max-content 1fr; gap: .35rem 1.2rem; font-size: .9rem; margin-bottom: 1rem; }
.pg-kv span:nth-child(odd) { color: #9aa0a6; }
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
