# Poltergeist panel

A Streamlit control room for a
[Poltergeist](https://github.com/RealistikGDPS/Poltergeist) server.

It covers a dashboard, players, levels, comments, moderation, the daily,
weekly and event queues, songs, rewards, map packs, gauntlets, roles and the
moderation log. Sign in with a game account that holds the `panel.access`
permission. Every action runs as that account, so the server's permission
checks apply and each change is recorded in the moderation log.

The panel reads and writes the server's MySQL and Redis directly through
[poltergeist-core](https://github.com/RealistikGDPS/poltergeist-core).

## Layout

```
panel/main.py        Entry point, sign-in gate and navigation
panel/runtime.py     Background event loop that runs the async services
panel/auth.py        Sign-in with game credentials
panel/components.py  Tables, paging and bulk-action reporting
panel/charts.py      Charts
panel/theme.py       Styling
panel/pages/         One module per screen
```

## Running

The `Dockerfile` builds the image. It takes the same
`configuration/app.env.example` and `configuration/mysql.env.example`
variables as the server, plus `PANEL_HTTP_PORT` and `PANEL_BASE_PATH`, and is
served under `/panel` behind a reverse proxy.

Locally, with the databases reachable:

```bash
uv sync
make dev
```

To pick up a newer poltergeist-core:

```bash
uv lock --upgrade-package poltergeist-core
```
