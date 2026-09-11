# Poltergeist control room

A Streamlit administration panel for a [Poltergeist](../poltergeist) Geometry
Dash server: dashboards, player and level management, mass moderation, timely
queues, songs, rewards, packs, roles, and a full event log.

Sign in with a game account that holds the `panel.access` permission. Every
action runs as that account, so the server's permission checks apply and each
change lands in the moderation log with your name on it.

## How it fits together

The panel talks to Poltergeist's MySQL and Redis directly through a copy of
Poltergeist's non-HTTP layers (`app/adapters`, `app/resources`,
`app/services`, `app/utilities`, `app/settings.py`). `make sync` refreshes that
copy from a sibling `../poltergeist` checkout; the panel itself lives in
`panel/` and is the only code written here.

```
panel/
├── main.py        Entry point: sign-in gate, navigation, sidebar
├── runtime.py     Background event loop bridging Streamlit to the async services
├── auth.py        Sign-in with game credentials and panel.access
├── theme.py       Custom styling
├── components.py  Tables with row selection, paging, bulk-action reporting
├── charts.py      Altair charts
└── pages/         One module per screen
```

## Running

The panel joins Poltergeist's Docker network and is reached through
Poltergeist's nginx at `/panel`:

```bash
for f in configuration/*.example; do cp "$f" "${f%.example}"; done
cp .env.example .env
# Use the same app.env and mysql.env values as the Poltergeist deployment.
make build
make run
```

For local development with the databases reachable on localhost:

```bash
uv sync
make dev
```
