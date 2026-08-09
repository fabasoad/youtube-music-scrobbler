import os
import sys

from loguru import logger

from scrobble.db import PlayDb
from scrobble.scrobblers.lastfm import LastFmScrobbler
from scrobble.scrobblers.listenbrainz import ListenBrainzScrobbler
from scrobble.types import ScrobblerTrack, YouTubeMusicTrack, prepare_tracks
from scrobble.yt_music.youtube_music_client import YouTubeMusicClient


def _diff(
  current: list[YouTubeMusicTrack], recent_ids: list[str], min_seq: int = 3
) -> list[YouTubeMusicTrack]:
  if not recent_ids:
    return []

  curr_ids: list[str] = [t.video_id for t in current]
  join: int = len(current)
  for i in range(len(current) - min_seq + 1):
    if curr_ids[i : i + min_seq] == recent_ids[:min_seq]:
      join = i
      break

  return list(reversed(current[:join]))  # oldest first


def _update_like_status(tracks: list[YouTubeMusicTrack]) -> None:
  prepared: list[ScrobblerTrack] = prepare_tracks(tracks)
  if os.environ.get("LASTFM_API_KEY"):
    LastFmScrobbler().update_like_status(prepared)
  if os.environ.get("LISTENBRAINZ_TOKEN"):
    ListenBrainzScrobbler().update_like_status(prepared)


def main() -> None:
  logger.remove()
  logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}")

  db = PlayDb()
  try:
    db.init_schema()
    yt_client = YouTubeMusicClient()
    current: list[YouTubeMusicTrack] = yt_client.fetch_history()
    recent_ids: list[str] = db.get_recent_video_ids(limit=yt_client.history_limit)
    new_tracks: list[YouTubeMusicTrack] = _diff(current, recent_ids)

    if new_tracks:
      db.insert_plays(new_tracks)
      logger.info("Fetch done. {} new track(s) saved.", len(new_tracks))
    else:
      logger.info("Fetch done. No new tracks.")

    _update_like_status(current)

  except Exception as e:
    logger.exception("Fetch error: {}", e)
    sys.exit(1)
  finally:
    db.close()


if __name__ == "__main__":
  main()
