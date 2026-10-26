import sys

from loguru import logger

from scrobble.db import PlayDb
from scrobble.types import YouTubeMusicTrack
from scrobble.yt_music.youtube_music_client import YouTubeMusicClient


def _diff(current: list[YouTubeMusicTrack], previous_ids: list[str]) -> list[YouTubeMusicTrack]:
  if not previous_ids:
    return []

  prev_pos: dict[str, int] = {vid: i for i, vid in enumerate(previous_ids)}
  sentinel: int = len(current) + 1
  new_plays: list[YouTubeMusicTrack] = [
    track for i, track in enumerate(current) if prev_pos.get(track.video_id, sentinel) > i
  ]
  return list(reversed(new_plays))


def main() -> None:
  logger.remove()
  logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}")

  db = PlayDb()
  try:
    db.init_schema()
    yt_client = YouTubeMusicClient()
    current: list[YouTubeMusicTrack] = yt_client.fetch_history()
    previous_ids: list[str] = db.get_history_snapshot()
    new_tracks: list[YouTubeMusicTrack] = _diff(current, previous_ids)

    if new_tracks:
      db.insert_plays(new_tracks)
      logger.info("Fetch done. {} new track(s) saved.", len(new_tracks))
    else:
      logger.info("Fetch done. No new tracks.")

    db.save_history_snapshot([t.video_id for t in current])

  except Exception as e:
    logger.exception("Fetch error: {}", e)
    sys.exit(1)
  finally:
    db.close()


if __name__ == "__main__":
  main()
