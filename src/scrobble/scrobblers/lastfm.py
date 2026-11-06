import functools
import os
import time
from collections.abc import Callable

import pylast
from loguru import logger

from scrobble.scrobblers.base import Scrobbler
from scrobble.types import ScrobblerTrack

_MAX_ATTEMPTS: int = 3
_BACKOFF_SECONDS: int = 5

# pylast raises WSError both for HTTP-level failures (status is the HTTP code) and for Last.fm API
# errors (status is the API error code). Only these are worth retrying — the rest, such as an
# invalid API key or session, will fail identically on every attempt.
_RETRYABLE_STATUSES: frozenset[str] = frozenset(
  {
    "500",  # internal server error
    "502",  # bad gateway
    "503",  # service unavailable
    "504",  # gateway timeout
    "11",  # service offline
    "16",  # temporarily unavailable
    "29",  # rate limit exceeded
  }
)


def _is_transient(error: pylast.PyLastError) -> bool:
  if isinstance(error, pylast.NetworkError | pylast.MalformedResponseError):
    return True
  if isinstance(error, pylast.WSError):
    return str(error.status) in _RETRYABLE_STATUSES
  return False


def _call_with_retry[T](label: str, operation: Callable[[], T]) -> T:
  # Retries transient Last.fm failures, then re-raises the last error if every attempt failed.
  last_error: pylast.PyLastError
  for attempt in range(_MAX_ATTEMPTS):
    try:
      return operation()
    except pylast.PyLastError as e:
      if not _is_transient(e):
        raise
      last_error = e
      logger.warning("[Last.fm] Attempt {}/{} failed for {}: {}", attempt + 1, _MAX_ATTEMPTS, label, e)
      if attempt < _MAX_ATTEMPTS - 1:
        time.sleep(_BACKOFF_SECONDS)
  raise last_error


class LastFmScrobbler(Scrobbler):
  def __init__(self) -> None:
    # Authenticating hits the Last.fm API, so it needs the same retry treatment as scrobbling.
    self.network: pylast.LastFMNetwork = _call_with_retry(
      "authentication",
      functools.partial(
        pylast.LastFMNetwork,
        api_key=os.environ["LASTFM_API_KEY"],
        api_secret=os.environ["LASTFM_SECRET"],
        username=os.environ["LASTFM_USERNAME"],
        password_hash=pylast.md5(os.environ["LASTFM_PASSWORD"]),
      ),
    )

  @staticmethod
  def _format_duration(duration: str | None) -> str:
    if not duration:
      return "N/A"
    return f"0{duration}" if len(duration) == 4 else duration

  def update_like_status(self, tracks: list[ScrobblerTrack]) -> None:
    scored: list[ScrobblerTrack] = [t for t in tracks if t.like_status != "INDIFFERENT"]
    if not scored:
      return

    logger.info("[Last.fm] Updating feedback for {} track(s)...", len(scored))

    submitted: int = 0
    for track in scored:
      pylast_track: pylast.Track = self.network.get_track(track.artist, track.title)
      album_part: str = "" if track.album is None else f" ({track.album})"
      duration_part: str = LastFmScrobbler._format_duration(track.duration)
      if track.like_status == "LIKE":
        pylast_track.love()
        logger.info("[Last.fm] Liked: [{}] {} — {}{}", duration_part, track.artist, track.title, album_part)
      else:
        pylast_track.unlove()
        logger.info(
          "[Last.fm] Disliked: [{}] {} — {}{}", duration_part, track.artist, track.title, album_part
        )
      submitted += 1

    logger.info("[Last.fm] Feedback done. {}/{} track(s) updated.", submitted, len(scored))

  def scrobble(self, tracks: list[ScrobblerTrack]) -> list[int]:
    logger.info("[Last.fm] Scrobbling {} track(s)...", len(tracks))
    scrobbled: list[int] = []
    for index, track in enumerate(tracks):
      try:
        _call_with_retry(
          track.title,
          functools.partial(
            self.network.scrobble,
            artist=track.artist,
            title=track.title,
            timestamp=track.timestamp,
            album=track.album,
            album_artist=track.album_artist,
            duration=track.duration_seconds,
          ),
        )
      except pylast.PyLastError as e:
        logger.error("[Last.fm] Skipping {}: {}", track.title, e)
        continue

      album_part: str = "" if track.album is None else f" ({track.album})"
      duration_part: str = LastFmScrobbler._format_duration(track.duration)
      logger.info("[Last.fm] Scrobbled: [{}] {} — {}{}", duration_part, track.artist, track.title, album_part)
      scrobbled.append(index)
      time.sleep(1)

    logger.info("[Last.fm] Done. {}/{} track(s) scrobbled.", len(scrobbled), len(tracks))
    return scrobbled
