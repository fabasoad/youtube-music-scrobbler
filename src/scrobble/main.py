import json
import os
import sys
import time

import pylast
from ytmusicapi import YTMusic

OAUTH_PATH = "browser.json"
SNAPSHOT_PATH = "last_snapshot.json"


def fetch_history(auth_path: str) -> list[dict]:
  yt = YTMusic(auth_path)
  history = yt.get_history()
  tracks = []
  for item in history[:50]:
    artists = item.get("artists") or []
    album = item.get("album")

    # default: 3 min
    duration = item.get("duration") or "3:00"
    minutes, seconds = map(int, duration.split(':'))
    duration_in_sec = minutes * 60 + seconds

    tracks.append({
      "videoId": item.get("videoId") or "",
      "title": item.get("title") or "Unknown Title",
      "artist": artists[0]["name"] if artists else "Unknown Artist",
      "duration": duration,
      "durationInSec": duration_in_sec,
      "album": album.get("name") if album and album.get("name") else None,
    })
  return tracks


def load_snapshot(path: str) -> list[dict]:
  if not os.path.exists(path):
    return []
  with open(path) as f:
    return json.load(f)


def diff_tracks(current: list[dict], snapshot: list[dict], min_seq: int = 3) -> \
    list[dict]:
  if not snapshot:
    return []
  snap_ids = [t["videoId"] for t in snapshot]
  curr_ids = [t["videoId"] for t in current]
  join = len(current)
  for i in range(len(current) - min_seq + 1):
    if curr_ids[i: i + min_seq] == snap_ids[:min_seq]:
      join = i
      break
  return list(reversed(current[:join]))  # oldest first


def assign_timestamps(tracks: list[dict]) -> list[dict]:
  now = int(time.time())
  offset = 0
  for track in reversed(tracks):
    track["timestamp"] = now - offset
    offset += track["durationInSec"]
  return tracks


def scrobble(tracks: list[dict]) -> int:
  api_key = os.environ["LASTFM_API_KEY"]
  api_secret = os.environ["LASTFM_SECRET"]
  username = os.environ["LASTFM_USERNAME"]
  password = pylast.md5(os.environ["LASTFM_PASSWORD"])

  network = pylast.LastFMNetwork(
    api_key=api_key,
    api_secret=api_secret,
    username=username,
    password_hash=password,
  )

  scrobbled = 0
  for track in tracks:
    for attempt in range(3):
      try:
        network.scrobble(
          artist=track["artist"],
          title=track["title"],
          timestamp=track["timestamp"],
          album=track["album"],
          duration=track["durationInSec"],
        )
        album_part = "" if track['album'] is None else f" ({track['album']})"
        print(f"Scrobbled: {track['artist']} — {track['title']}{album_part} {track['duration']}")
        scrobbled += 1
        time.sleep(1)
        break
      except (pylast.NetworkError, pylast.MalformedResponseError) as e:
        print(f"Attempt {attempt + 1} failed for {track['title']}: {e}")
        if attempt < 2:
          time.sleep(5)
        else:
          print(f"Skipping: {track['title']} after 3 failed attempts")

  return scrobbled


def save_snapshot(tracks: list[dict], path: str) -> None:
  with open(path, "w") as f:
    json.dump(tracks, f, indent=2)


def prune_logs(log_path: str, keep_days: int = 365) -> None:
  if not os.path.exists(log_path):
    return
  from datetime import datetime, timezone, timedelta
  cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
  with open(log_path) as f:
    lines = f.readlines()
  kept = []
  for line in lines:
    try:
      ts = datetime.fromisoformat(line.split("|")[0].strip())
      if ts > cutoff:
        kept.append(line)
    except ValueError:
      kept.append(line)
  with open(log_path, "w") as f:
    f.writelines(kept)


def write_log(log_path: str, scrobbled: int, new_tracks: int) -> None:
  from datetime import datetime, timezone
  prune_logs(log_path)
  ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
  with open(log_path, "a") as f:
    f.write(f"{ts} | scrobbled={scrobbled} | new_tracks={new_tracks}\n")


def write_summary(tracks: list[dict]) -> None:
  summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
  if not summary_file:
    return
  with open(summary_file, "a") as f:
    if not tracks:
      f.write("## Scrobbler\n\nNo new tracks scrobbled.\n")
      return
    f.write("## Scrobbler\n\n")
    f.write("| # | Artist | Title | Duration |\n")
    f.write("|---|--------|-------|----------|\n")
    for i, track in enumerate(tracks, 1):
      f.write(f"| {i} | {track['artist']} | {track['title']} | {track['duration']} |\n")


def main():
  try:
    current = fetch_history(OAUTH_PATH)
    snapshot = load_snapshot(SNAPSHOT_PATH)
    new_tracks = diff_tracks(current, snapshot)

    if new_tracks:
      new_tracks = assign_timestamps(new_tracks)
      scrobbled = scrobble(new_tracks)
    else:
      print("No new tracks to scrobble.")
      scrobbled = 0

    save_snapshot(current, SNAPSHOT_PATH)
    write_log("runs.log", scrobbled, len(new_tracks))
    write_summary(new_tracks)
    print(f"Done. Scrobbled {scrobbled} track(s).")

  except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
    sys.exit(1)


if __name__ == "__main__":
  main()
