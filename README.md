# YouTube Music Scrobbler

[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/badges/StandWithUkraine.svg)](https://stand-with-ukraine.pp.ua)
![unit-tests](https://github.com/fabasoad/youtube-music-scrobbler/actions/workflows/unit-tests.yml/badge.svg)
![security](https://github.com/fabasoad/youtube-music-scrobbler/actions/workflows/security.yml/badge.svg)
![linting](https://github.com/fabasoad/youtube-music-scrobbler/actions/workflows/linting.yml/badge.svg)

Automatically syncs your YouTube Music listening history to Last.fm — runs on
GitHub Actions every 2 hours, no server required.

---

## Overview

YouTube Music has no built-in Last.fm integration. This project bridges that gap
by fetching your recent YouTube Music play history and scrobbling new tracks to
Last.fm, complete with artist, title, album, duration and an estimated timestamp.

Everything runs on GitHub Actions — no servers, no costs, and nothing touches
your Google account except your own browser cookies.

---

## How it works

1. A scheduled GitHub Actions job runs every 2 hours
2. It pulls your 50 most recently played tracks from YouTube Music using browser
   cookie authentication
3. Those tracks are compared against a saved snapshot to identify new plays
4. New tracks are scrobbled to Last.fm with timestamps spaced by each track's
   duration apart (defaulting to 3 minutes if duration is unavailable)
5. The snapshot is updated and committed back to the repo for the next run

> **Note:** YouTube Music only provides relative timestamps like "Today" or
> "Yesterday" — exact play times are not available. Timestamps are approximated
> from the time of each sync run.

---

## Prerequisites

- A [GitHub](https://github.com) account
- A [Last.fm](https://www.last.fm) account with API access
- Python 3.14+ on your local machine (for the one-time setup)
- A YouTube Music account with listening history enabled

---

## Setup

### 1. Use this repo

Fork or clone this repository:

```shell
git clone https://github.com/fabasoad/youtube-music-scrobbler.git
cd youtube-music-scrobbler
```

### 2. Set up a local Python environment

```shell
make install
```

### 3. Authenticate with YouTube Music

YouTube Music requires browser cookie auth — standard OAuth does not work with
its internal API.

1. Open [music.youtube.com](https://music.youtube.com) in Chrome while logged in
2. Open DevTools (`Cmd+Option+I` on macOS) → **Network** tab
3. Type `browse` in the filter, then interact with the page
4. Right-click the matching `browse` request → **Copy** → **Copy as cURL**
5. Paste the cURL command into a file named `curl.txt` in the project root
6. Run `uv run refresh-auth` to generate `browser.json`

`browser.json` holds your session cookies — **never commit it**.

To verify it works:

```shell
uv run verify
```

You should see track objects with `title`, `artists`, and `videoId` fields.

> **Cookie expiry:** Cookies typically expire after 1–3 months. When the workflow
> starts failing, repeat steps 4–6 and update the `YTM_BROWSER` secret.

### 4. Create a Last.fm API application

1. Go to [last.fm/api/account/create](https://www.last.fm/api/account/create)
2. Fill in a name and description (e.g. `youtube-music-scrobbler`)
3. Copy the **API Key** and **Shared Secret**

### 5. Add GitHub Actions Secrets

In your repo, go to **Settings → Secrets and variables → Actions** and add:

| Secret name | Value |
| --- | --- |
| `YTM_BROWSER` | Full contents of `browser.json` |
| `LASTFM_API_KEY` | Your Last.fm API key |
| `LASTFM_SECRET` | Your Last.fm shared secret |
| `LASTFM_USERNAME` | Your Last.fm username |
| `LASTFM_PASSWORD` | Your Last.fm password |

---

## Monitoring

- **Last.fm profile** — scrobbles appear within minutes of each run
- **GitHub Actions tab** — full run logs and history
- **runs.log** — committed to the repo after each run with a count of scrobbled
  tracks and timestamps

---

## Refreshing browser auth

When the workflow fails due to expired cookies:

1. Open [music.youtube.com](https://music.youtube.com) in Chrome
2. DevTools → Network → filter by `browse` → interact with the page
3. Right-click the `browse` request → **Copy** → **Copy as cURL**
4. Save to `curl.txt` in the project root
5. Run `uv run refresh-auth` locally to regenerate `browser.json`
6. Update the `YTM_BROWSER` GitHub Secret with the new file contents

GitHub will email you on workflow failure, so you'll know when to refresh.
