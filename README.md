# poltergeist-panel

**Archived on 2026-09-13.** The Streamlit control room has been replaced by the
admin area of the website, [rgdps-web](https://github.com/RealistikGDPS/rgdps-web),
served under `/admin` to accounts holding the `admin.access` permission. Every
feature moved across: dashboard, users, levels and their rating and report
queues, comments, the moderation log and bans, daily, weekly and event queues,
songs, quests and vault codes, map packs and gauntlets, roles, plus new live
server settings and a stack status page.

The last published image, `ghcr.io/realistikgdps/poltergeist-panel`, expects a
`poltergeist-core` that still knows `panel.access`; the migration
`1789000005_server_settings` in the deployment repository renames that
permission to `admin.access`, so this panel cannot be run against a current
database. The history stays here for reference.
