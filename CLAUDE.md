# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Music Scrobbler syncs YouTube Music listening history to Last.fm and ListenBrainz via GitHub Actions (runs every 2 hours). No server required — authentication uses a browser cookie captured via DevTools.

**Core flow:** fetch 50 recent YTM tracks → diff against PostgreSQL play history → insert new plays → scrobble unscrobbled tracks per service → persist scrobble timestamps.

## Commands

```bash
make install      # uv sync — install dependencies
make fetch        # uv run fetch — fetch new plays from YT Music into DB
make run          # uv run scrobble — scrobble unscrobbled DB plays to Last.fm/ListenBrainz
make update-likes # uv run update-likes — push LIKE/DISLIKE feedback to scrobbler services
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

- **`fetch.py`** — Fetches top-50 history from YT Music, diffs against recent DB video_ids, inserts new plays into PostgreSQL.
- **`main.py`** — Orchestrates scrobbling: queries DB for unscrobbled tracks per service → `prepare_tracks()` → scrobble → mark scrobbled. Also writes `runs.log` and a GitHub Step Summary.
- **`db.py`** — `PlayDb`: PostgreSQL via psycopg (Neon). Manages schema, inserts plays, queries unscrobbled tracks per service, marks scrobbled.
- **`update_likes.py`** — Fetches current YT Music history and pushes LIKE/DISLIKE feedback to configured scrobblers.
- **`auth.py`** — One-time setup helper: parses a raw `curl.txt` DevTools export (regex over `-b`, `Authorization`, `x-goog-authuser`) and writes/merges `browser.json`.
- **`types.py`** — `YouTubeMusicTrack` and `ScrobblerTrack` dataclasses, plus `prepare_tracks()` which joins artists with `" & "` and assigns synthetic timestamps.
- **`scrobblers/base.py`** — Abstract `Scrobbler` base: `scrobble()` (required) and `update_like_status()` (optional no-op default).
- **`scrobblers/lastfm.py`** — `LastFmScrobbler`: submits via `pylast`, retries on network errors, calls `.love()`/`.unlove()` for feedback.
- **`scrobblers/listenbrainz.py`** — `ListenBrainzScrobbler`: submits via `liblistenbrainz`, posts feedback scores to the ListenBrainz API.
- **`yt_music/youtube_music_client.py`** — `YouTubeMusicClient`: fetches top-50 history and applies artist filters.
- **`yt_music/artist_as_label_filter.py`** — Removes `InVogue Records` from artist lists (label incorrectly appears as primary artist on some releases).

### Fetch diffing

`_diff()` in `fetch.py` finds the join point where the current YT Music list re-aligns with the saved DB snapshot using a minimum consecutive-match window (`min_seq=3`). Everything before that join point is treated as new plays, returned oldest-first for insertion.

### Timestamp assignment

Timestamps are synthetic — `prepare_tracks()` in `types.py` walks backward from `time.time()` using each track's `duration_seconds` (defaulting to 180 s). Last.fm and ListenBrainz both require distinct timestamps per scrobble.

### Retry logic

Both `LastFmScrobbler.scrobble()` and `YouTubeMusicClient.fetch_history()` retry up to 3 times with a 5-second backoff on transient network errors.

### Workflow trigger chain

`fetch.yml` is triggered by `workflow_dispatch`; an external cron-job.org service calls the GitHub API every 2 hours. On success, it triggers both `scrobble.yml` and `update-likes.yml` in parallel. `scrobble.yml` commits `runs.log` back to main after each run.

## Key Data Structures

```python
# src/scrobble/types.py
@dataclass
class YouTubeMusicTrack:
  video_id: str        # unique key for diffing
  title: str
  artists: list[str]
  duration: str        # "M:SS"
  album: str | None
  like_status: str | None  # "LIKE" | "DISLIKE" | "INDIFFERENT"
  duration_seconds: int | None
  thumbnail: str | None

@dataclass
class ScrobblerTrack:
  artist: str          # artists joined with " & "
  title: str
  timestamp: int       # Unix epoch — set by prepare_tracks()
  album: str | None
  album_artist: str | None  # first artist only
  duration: str | None
  duration_seconds: int | None
  like_status: str | None
```

### Database schema (PostgreSQL / Neon)

```sql
plays (
  id BIGSERIAL PRIMARY KEY,
  video_id TEXT NOT NULL,
  title TEXT NOT NULL,
  duration TEXT, album TEXT, duration_seconds INTEGER, thumbnail TEXT,
  fetched_at TIMESTAMPTZ DEFAULT NOW(),
  lastfm_scrobbled_at TIMESTAMPTZ,
  listenbrainz_scrobbled_at TIMESTAMPTZ
)
play_artists (
  play_id BIGINT REFERENCES plays(id) ON DELETE CASCADE,
  artist_name TEXT NOT NULL,
  position SMALLINT NOT NULL,
  PRIMARY KEY (play_id, position)
)
```

Per-service scrobble tracking: `lastfm_scrobbled_at` and `listenbrainz_scrobbled_at` are set independently, so a failed scrobble to one service doesn't block the other.

`runs.log` is **git-tracked** and committed back by the `scrobble.yml` workflow after each run.

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
| `LASTFM_SECRET` | Last.fm API secret |
| `LASTFM_USERNAME` | Last.fm username |
| `LASTFM_PASSWORD` | Last.fm password (MD5-hashed by pylast) |
| `NEON_DATABASE_URL` | PostgreSQL connection string for Neon |
| `LISTENBRAINZ_TOKEN` | ListenBrainz user token |

`browser.json` and `curl.txt` are git-ignored and must never be committed.

## Pre-commit Hooks

Hooks run automatically on commit/push and include ruff (lint + format with auto-fix), secret scanning (detect-secrets, gitleaks), vulnerability scanning (grype, osv-scanner on `uv.lock`), actionlint for workflow files, and pytest + `uv audit` on pre-push. Run `pre-commit run --all-files` to validate manually.