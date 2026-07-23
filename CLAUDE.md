# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Music Scrobbler syncs YouTube Music listening history to Last.fm via GitHub Actions (runs every 2 hours). No server required — authentication uses a browser cookie captured via DevTools.

**Core flow:** fetch 50 recent YTM tracks → diff against saved snapshot → identify new plays → assign approximate timestamps → scrobble to Last.fm → persist updated snapshot.

## Commands

```bash
make install      # uv sync — install dependencies
make run          # uv run scrobble — run the full scrobble workflow
make refresh-auth # uv run refresh-auth — parse curl.txt → browser.json
make verify       # uv run python verify.py — test YouTube Music auth connection
make test         # uv run pytest — run unit tests
make lint         # ruff check + ruff format --check
make audit        # uv audit — vulnerability scan
make outdated     # uv tree --outdated --depth 1 — check for dependency updates
```

Run a single test file:
```bash
uv run pytest tests/test_auth.py
```

Run a single test by name:
```bash
uv run pytest -k "test_name"
```

## Architecture

All source lives in `src/scrobble/`:

- **`main.py`** — Full scrobbling pipeline: `fetch_history` → `diff_tracks` → `assign_timestamps` → `scrobble` → `save_snapshot`. Also writes `runs.log` and a GitHub Step Summary.
- **`auth.py`** — One-time setup helper: parses a raw `curl.txt` DevTools export (regex over `-b`, `Authorization`, `x-goog-authuser`) and writes/merges `browser.json`.

### Snapshot diffing (`diff_tracks`)

The algorithm finds new tracks by locating where the current list rejoins the previous snapshot using a minimum consecutive-match window (`min_seq=3`). Everything before that join point is treated as new plays.

### Timestamp assignment (`assign_timestamps`)

Timestamps are synthetic — computed by walking backward from `datetime.now()` using each track's reported duration (defaulting to 3 minutes). Last.fm requires distinct timestamps per scrobble.

### Retry logic

`scrobble()` retries up to 3 times with a 5-second backoff on any `pylast` exception.

## Key Data Structure

Track dict passed through the pipeline:
```python
{
  "videoId": str,       # YouTube video ID — used as the unique key for diffing
  "title": str,
  "artist": str,
  "duration": str,      # "M:SS" string
  "duration_in_sec": int, # derived — used for synthetic timestamp math
  "album": str | None,
  "timestamp": int,     # Unix epoch — added by assign_timestamps(), required by Last.fm
}
```

`last_snapshot.json` and `runs.log` are **git-tracked** and committed back to the repo by the `scrobble.yml` workflow after each run.

## Code Style

- Python `>=3.14` required
- Line length: 110 characters
- Indentation: 2 spaces
- Strings: double quotes preferred over single quotes
- Typings: always annotate variables, function parameters, and return types
- Ruff rules: `E`, `F`, `I` (isort), `UP` (pyupgrade), `B` (bugbear), `SIM` (simplify)

## Secrets & Auth

| Secret | Purpose |
|---|---|
| `YTM_BROWSER` | JSON string written to `browser.json` at runtime |
| `LASTFM_API_KEY` | Last.fm API key |
| `LASTFM_API_SECRET` | Last.fm API secret |
| `LASTFM_USERNAME` | Last.fm username |
| `LASTFM_PASSWORD` | Last.fm password (MD5-hashed by pylast) |

`browser.json` and `curl.txt` are git-ignored and must never be committed.

## Pre-commit Hooks

Hooks run automatically on commit/push and include ruff (lint + format with auto-fix), secret scanning (detect-secrets, gitleaks), vulnerability scanning (grype, osv-scanner on `uv.lock`), actionlint for workflow files, and pytest + `uv audit` on pre-push. Run `pre-commit run --all-files` to validate manually.
