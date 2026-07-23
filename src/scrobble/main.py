import os
import sys
from datetime import UTC

from scrobble.lastfm_client import LastFmClient
from scrobble.snapshot_manager import SnapshotManager
from scrobble.types import YouTubeMusicTrack
from scrobble.yt_music.youtube_music_client import YouTubeMusicClient


def prune_logs(log_path: str, keep_days: int = 365) -> None:
  if not os.path.exists(log_path):
    return
  from datetime import datetime, timedelta

  cutoff: datetime = datetime.now(UTC) - timedelta(days=keep_days)
  with open(log_path) as f:
    lines: list[str] = f.readlines()
  kept: list[str] = []
  for line in lines:
    try:
      ts: datetime = datetime.fromisoformat(line.split("|")[0].strip())
      if ts > cutoff:
        kept.append(line)
    except ValueError:
      kept.append(line)
  with open(log_path, "w") as f:
    f.writelines(kept)


def write_log(log_path: str, scrobbled: int, new_tracks: int) -> None:
  from datetime import datetime

  prune_logs(log_path)
  ts: str = datetime.now(UTC).isoformat(timespec="seconds")
  with open(log_path, "a") as f:
    f.write(f"{ts} | scrobbled={scrobbled} | new_tracks={new_tracks}\n")


def write_summary(tracks: list[YouTubeMusicTrack]) -> None:
  summary_file: str | None = os.environ.get("GITHUB_STEP_SUMMARY")
  if not summary_file:
    return
  with open(summary_file, "a") as f:
    if not tracks:
      f.write("## Scrobbler\n\nNo new tracks scrobbled.\n")
      return
    f.write("## Scrobbler\n\n")
    f.write("| # | Duration | Artist | Title | Album |  |\n")
    f.write("|---|----------|--------|-------|-------|---|\n")
    for i, track in enumerate(tracks):
      duration: str = "N/A"
      if track.duration:
        duration = f"0{track.duration}" if len(track.duration) == 4 else track.duration
      album: str = "N/A" if track.album is None else track.album
      thumbnail: str = f"![]({track.thumbnail})" if track.thumbnail else ""
      f.write(f"| {i+1} | {duration} | {' & '.join(track.artists)} | {track.title} | {album} | {thumbnail} |\n")


def main() -> None:
  yt_music_client = YouTubeMusicClient()
  lastfm_client = LastFmClient()
  snapshot_manager = SnapshotManager()

  try:
    current: list[YouTubeMusicTrack] = yt_music_client.fetch_history()
    new_tracks: list[YouTubeMusicTrack] = snapshot_manager.get_diff_from_snapshot(current)

    if new_tracks:
      scrobbled: int = lastfm_client.scrobble(new_tracks)
      lastfm_client.update_like_status(new_tracks)
    else:
      print("No new tracks to scrobble.")
      scrobbled = 0

    snapshot_manager.save_snapshot(current)
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
