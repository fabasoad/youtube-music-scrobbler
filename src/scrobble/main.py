import os
import sys
from datetime import UTC

from loguru import logger

from scrobble.db import PlayDb
from scrobble.scrobblers.base import Scrobbler
from scrobble.scrobblers.lastfm import LastFmScrobbler
from scrobble.scrobblers.listenbrainz import ListenBrainzScrobbler
from scrobble.types import ScrobblerTrack, YouTubeMusicTrack, prepare_tracks


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
      f.write(
        f"| {i + 1} | {duration} | {' & '.join(track.artists)} | {track.title} | {album} | {thumbnail} |\n"
      )


def build_scrobblers() -> list[Scrobbler]:
  scrobblers: list[Scrobbler] = []
  lastfm_vars = ("LASTFM_API_KEY", "LASTFM_SECRET", "LASTFM_USERNAME", "LASTFM_PASSWORD")
  missing_lastfm: list[str] = [v for v in lastfm_vars if not os.environ.get(v)]
  if missing_lastfm:
    logger.warning("[Last.fm] Not configured. Missing: {}", ", ".join(missing_lastfm))
  else:
    scrobblers.append(LastFmScrobbler())
    logger.info("[Last.fm] Scrobbler configured.")
  if os.environ.get("LISTENBRAINZ_TOKEN"):
    try:
      scrobblers.append(ListenBrainzScrobbler())
      logger.info("[ListenBrainz] Scrobbler configured.")
    except Exception as e:
      logger.error("[ListenBrainz] Failed to configure scrobbler: {!r}", e)
  else:
    logger.warning("[ListenBrainz] Not configured. Missing: LISTENBRAINZ_TOKEN")
  if not scrobblers:
    raise RuntimeError("No scrobblers configured. Set at least one set of credentials.")
  return scrobblers


def main() -> None:
  logger.remove()
  logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}")

  scrobblers: list[Scrobbler] = build_scrobblers()
  scrobbler_keys: list[str] = []
  if any(isinstance(s, LastFmScrobbler) for s in scrobblers):
    scrobbler_keys.append("lastfm")
  if any(isinstance(s, ListenBrainzScrobbler) for s in scrobblers):
    scrobbler_keys.append("listenbrainz")

  db = PlayDb()
  try:
    db.init_schema()

    total_scrobbled: int = 0
    all_new_tracks: list[YouTubeMusicTrack] = []

    for key, scrobbler in zip(scrobbler_keys, scrobblers, strict=True):
      rows: list[tuple[int, YouTubeMusicTrack]] = db.get_unscrobbled(key)
      if not rows:
        logger.info("No unscrobbled tracks for {}.", key)
        continue

      play_ids: list[int] = [r[0] for r in rows]
      tracks: list[YouTubeMusicTrack] = [r[1] for r in rows]
      prepared: list[ScrobblerTrack] = prepare_tracks(tracks)

      count: int = scrobbler.scrobble(prepared)
      db.mark_scrobbled(play_ids, key)
      total_scrobbled = max(total_scrobbled, count)
      if len(tracks) > len(all_new_tracks):
        all_new_tracks = tracks

    write_log("runs.log", total_scrobbled, len(all_new_tracks))
    write_summary(all_new_tracks)
    logger.info("Done. Scrobbled {} track(s).", total_scrobbled)

  except Exception as e:
    logger.exception("Error: {}", e)
    sys.exit(1)
  finally:
    db.close()


if __name__ == "__main__":
  main()
