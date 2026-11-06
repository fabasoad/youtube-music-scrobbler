import os
import sys

from loguru import logger

from scrobble.scrobblers.base import Scrobbler
from scrobble.scrobblers.lastfm import LastFmScrobbler
from scrobble.scrobblers.listenbrainz import ListenBrainzScrobbler
from scrobble.types import ScrobblerTrack, YouTubeMusicTrack, prepare_tracks
from scrobble.yt_music.youtube_music_client import YouTubeMusicClient


def main() -> None:
  logger.remove()
  logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}")

  try:
    current: list[YouTubeMusicTrack] = YouTubeMusicClient().fetch_history()
    prepared: list[ScrobblerTrack] = prepare_tracks(current)
  except Exception as e:
    logger.exception("Update likes error: {}", e)
    sys.exit(1)

  # Feedback is re-pushed from the full history on every run, so a service failing here is not
  # fatal — it self-heals next run. Each service is isolated so one outage cannot block the other.
  configured: int = 0
  failed: int = 0
  services: list[tuple[str, str, type[Scrobbler]]] = [
    ("Last.fm", "LASTFM_API_KEY", LastFmScrobbler),
    ("ListenBrainz", "LISTENBRAINZ_TOKEN", ListenBrainzScrobbler),
  ]
  for name, env_var, scrobbler_cls in services:
    if not os.environ.get(env_var):
      logger.warning("[{}] Not configured, skipping like updates.", name)
      continue
    configured += 1
    try:
      scrobbler_cls().update_like_status(prepared)
    except Exception as e:
      failed += 1
      logger.error("[{}] Like updates failed: {!r}", name, e)

  # Only fail the job if every configured service failed, which points at a real problem
  # rather than one service having a bad few minutes.
  if configured and failed == configured:
    logger.error("Like updates failed for all {} configured service(s).", configured)
    sys.exit(1)


if __name__ == "__main__":
  main()
