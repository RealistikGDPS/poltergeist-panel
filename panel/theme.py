import html

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp { font-family: 'Space Grotesk', system-ui, sans-serif; }
code, pre, .stCode { font-family: 'JetBrains Mono', monospace; }
.stApp { background: radial-gradient(ellipse at 20% -10%, #2a0f3f 0%, #0b0716 45%, #06040c 100%); }
header[data-testid="stHeader"] { background: rgba(11, 7, 22, .85); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(180,140,255,.15); }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-bottom: 2rem; }

.pg-brand { font-weight: 700; letter-spacing: .18em; font-size: 1.25rem; color: #f3ecff; text-shadow: 0 0 10px #b48cff, 0 0 30px #7b3fe4; }
.pg-sub { color: #9f8cc9; font-size: .75rem; letter-spacing: .12em; text-transform: uppercase; }
.pg-muted { color: #9f8cc9; font-size: .85rem; }
.pg-title { font-size: 1.6rem; font-weight: 700; color: #f3ecff; margin: 0; }

div[data-testid="stVerticalBlockBorderWrapper"] { border-color: rgba(180,140,255,.2) !important; border-radius: 14px; background: rgba(23,16,43,.45); }
div[data-testid="stMetric"] { background: #0b0716; border-radius: 14px; }
div[data-testid="stMetric"] label { color: #b9a6e6 !important; letter-spacing: .08em; text-transform: uppercase; font-size: .7rem; }
div[data-testid="stMetricValue"] { color: #f3ecff; font-weight: 700; }

.stTabs [data-baseweb="tab-list"] { gap: 1.2rem; }
div[data-testid="stExpander"] { border: 1px solid rgba(180,140,255,.18); border-radius: 12px; background: rgba(23,16,43,.6); }
.stButton > button { border-radius: 10px; border: 1px solid rgba(180,140,255,.35); }
.stButton > button[kind="primary"] { background: linear-gradient(90deg, #7b3fe4, #b48cff); border: none; color: #fff; font-weight: 600; }

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
