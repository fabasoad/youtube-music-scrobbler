import os
import sys

from loguru import logger

from scrobble.scrobblers.lastfm import LastFmScrobbler
from scrobble.scrobblers.listenbrainz import ListenBrainzScrobbler
from scrobble.types import YouTubeMusicTrack, prepare_tracks
from scrobble.yt_music.youtube_music_client import YouTubeMusicClient


def main() -> None:
  logger.remove()
  logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}")

  try:
    current: list[YouTubeMusicTrack] = YouTubeMusicClient().fetch_history()
    prepared = prepare_tracks(current)

    if os.environ.get("LASTFM_API_KEY"):
      LastFmScrobbler().update_like_status(prepared)
    else:
      logger.warning("[Last.fm] Not configured, skipping like updates.")

    if os.environ.get("LISTENBRAINZ_TOKEN"):
      ListenBrainzScrobbler().update_like_status(prepared)
    else:
      logger.warning("[ListenBrainz] Not configured, skipping like updates.")

  except Exception as e:
    logger.exception("Update likes error: {}", e)
    sys.exit(1)


if __name__ == "__main__":
  main()
