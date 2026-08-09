import sys

from loguru import logger

from scrobble.db import PlayDb
from scrobble.types import YouTubeMusicTrack
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

  except Exception as e:
    logger.exception("Fetch error: {}", e)
    sys.exit(1)
  finally:
    db.close()


if __name__ == "__main__":
  main()
