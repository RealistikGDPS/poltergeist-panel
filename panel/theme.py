import html

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp { font-family: 'Space Grotesk', system-ui, sans-serif; }
code, pre, .stCode { font-family: 'JetBrains Mono', monospace; }
.stApp { background: radial-gradient(ellipse at 20% -10%, #2a0f3f 0%, #0b0716 45%, #06040c 100%); }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #170f2c 0%, #0d0819 100%); border-right: 1px solid rgba(180, 140, 255, .15); }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }

.pg-brand { font-weight: 700; letter-spacing: .18em; font-size: 1.35rem; color: #f3ecff; text-shadow: 0 0 10px #b48cff, 0 0 30px #7b3fe4; margin-bottom: .2rem; }
.pg-sub { color: #9f8cc9; font-size: .8rem; letter-spacing: .12em; text-transform: uppercase; }
.pg-user { margin-top: .6rem; padding: .6rem .8rem; border-radius: 10px; background: rgba(180,140,255,.08); border: 1px solid rgba(180,140,255,.18); font-size: .85rem; }

div[data-testid="stMetric"] { background: linear-gradient(160deg, rgba(180,140,255,.10), rgba(123,63,228,.04)); border: 1px solid rgba(180,140,255,.22); border-radius: 14px; padding: .9rem 1rem; box-shadow: 0 8px 30px rgba(0,0,0,.25); }
div[data-testid="stMetric"] label { color: #b9a6e6 !important; letter-spacing: .08em; text-transform: uppercase; font-size: .72rem; }
div[data-testid="stMetricValue"] { color: #f3ecff; font-weight: 700; }

.stTabs [data-baseweb="tab-list"] { gap: .4rem; }
.stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; padding: .4rem 1rem; background: rgba(180,140,255,.06); }
.stTabs [aria-selected="true"] { background: rgba(180,140,255,.18) !important; }
div[data-testid="stExpander"] { border: 1px solid rgba(180,140,255,.18); border-radius: 12px; background: rgba(23,16,43,.6); }
div[data-testid="stDataFrame"] { border: 1px solid rgba(180,140,255,.18); border-radius: 12px; overflow: hidden; }
.stButton > button { border-radius: 10px; border: 1px solid rgba(180,140,255,.35); }
.stButton > button[kind="primary"] { background: linear-gradient(90deg, #7b3fe4, #b48cff); border: none; color: #fff; font-weight: 600; }
div[data-testid="stForm"] { border: 1px solid rgba(180,140,255,.2); border-radius: 14px; background: rgba(23,16,43,.5); }

.pg-pill { display: inline-block; padding: .15rem .55rem; border-radius: 999px; font-size: .72rem; font-weight: 600; letter-spacing: .05em; margin: 0 .3rem .3rem 0; border: 1px solid transparent; }
.pg-pill.ok { background: rgba(72, 199, 142, .15); color: #7ee2b0; border-color: rgba(72,199,142,.35); }
.pg-pill.warn { background: rgba(255, 190, 80, .15); color: #ffd58a; border-color: rgba(255,190,80,.35); }
.pg-pill.bad { background: rgba(255, 92, 120, .15); color: #ff9db0; border-color: rgba(255,92,120,.35); }
.pg-pill.info { background: rgba(180, 140, 255, .15); color: #d9c8ff; border-color: rgba(180,140,255,.35); }
.pg-muted { color: #9f8cc9; font-size: .85rem; }
.pg-card { padding: 1rem 1.2rem; border-radius: 14px; border: 1px solid rgba(180,140,255,.2); background: rgba(23,16,43,.55); margin-bottom: .8rem; }
.pg-card h4 { margin: 0 0 .4rem 0; color: #f3ecff; }
.pg-kv { display: grid; grid-template-columns: max-content 1fr; gap: .15rem 1rem; font-size: .9rem; }
.pg-kv span:nth-child(odd) { color: #9f8cc9; }
</style>
"""


def apply() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def pill(text: str, kind: str = "info") -> str:
    return f'<span class="pg-pill {kind}">{html.escape(text)}</span>'


def muted(text: str) -> str:
    return f'<span class="pg-muted">{html.escape(text)}</span>'


def card(title: str, rows: list[tuple[str, str]]) -> str:
    cells = "".join(
        f"<span>{html.escape(key)}</span><span>{html.escape(value)}</span>"
        for key, value in rows
    )

    return (
        f'<div class="pg-card"><h4>{html.escape(title)}</h4>'
        f'<div class="pg-kv">{cells}</div></div>'
    )
