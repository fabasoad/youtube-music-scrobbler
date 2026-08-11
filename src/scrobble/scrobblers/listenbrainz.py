import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

import liblistenbrainz
import liblistenbrainz.errors
from loguru import logger

from scrobble.scrobblers.base import Scrobbler
from scrobble.types import ScrobblerTrack

_FEEDBACK_URL = "https://api.listenbrainz.org/1/feedback/recording-feedback"
_METADATA_LOOKUP_URL = "https://api.listenbrainz.org/1/metadata/lookup/"


class ListenBrainzScrobbler(Scrobbler):
  def __init__(self) -> None:
    self.client: liblistenbrainz.ListenBrainz = liblistenbrainz.ListenBrainz()
    self.client.set_auth_token(os.environ["LISTENBRAINZ_TOKEN"], check_validity=False)

  def scrobble(self, tracks: list[ScrobblerTrack]) -> int:
    logger.info("[ListenBrainz] Scrobbling {} track(s)...", len(tracks))
    listens: list[liblistenbrainz.Listen] = [
      liblistenbrainz.Listen(
        track_name=track.title,
        artist_name=track.artist,
        listened_at=track.timestamp,
        release_name=track.album,
        listening_from="youtube-music",
      )
      for track in tracks
    ]
    try:
      result: dict[str, str] = self.client.submit_multiple_listens(listens)
      if result["status"] != "ok":
        logger.error("[ListenBrainz] Submission failed: {}", result["message"])
      for track in tracks:
        album_part: str = "" if track.album is None else f" ({track.album})"
        duration_part: str = "N/A"
        if track.duration:
          duration_part = f"0{track.duration}" if len(track.duration) == 4 else track.duration
        logger.info(
          "[ListenBrainz] Scrobbled: [{}] {} — {}{}", duration_part, track.artist, track.title, album_part
        )
      logger.info("[ListenBrainz] Done. {}/{} track(s) scrobbled.", len(listens), len(tracks))
      return len(listens)
    except liblistenbrainz.errors.ListenBrainzException as e:
      logger.error("[ListenBrainz] Submission failed: {}", e)
      return 0

  def _lookup_recording_metadata(self, artist: str, title: str) -> tuple[str | None, str | None]:
    params: str = urllib.parse.urlencode(
      {"artist_name": artist, "recording_name": title, "metadata": "false"}
    )
    url: str = f"{_METADATA_LOOKUP_URL}?{params}"
    req: urllib.request.Request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
      with urllib.request.urlopen(req, timeout=10) as resp:
        data: dict = json.loads(resp.read())
        return data.get("recording_mbid"), data.get("recording_msid")
    except urllib.error.URLError, TimeoutError, json.JSONDecodeError:
      return None, None

  def update_like_status(self, tracks: list[ScrobblerTrack]) -> None:
    scored: list[tuple[ScrobblerTrack, int]] = []
    for track in tracks:
      if track.like_status == "LIKE":
        scored.append((track, 1))
      elif track.like_status == "DISLIKE":
        scored.append((track, 0))

    if not scored:
      return

    logger.info("[ListenBrainz] Updating feedback for {} track(s)...", len(scored))

    token: str = os.environ["LISTENBRAINZ_TOKEN"]
    submitted: int = 0
    for track, score in scored:
      mbid, msid = self._lookup_recording_metadata(track.artist, track.title)
      if not mbid:
        logger.warning("[ListenBrainz] Recording not found for feedback: {} — {}", track.artist, track.title)
        continue

      body: dict[str, str | int] = {"score": score, "recording_mbid": mbid}
      if msid:
        body["recording_msid"] = msid

      req: urllib.request.Request = urllib.request.Request(
        _FEEDBACK_URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Token {token}", "Content-Type": "application/json"},
        method="POST",
      )
      for attempt in range(3):
        try:
          with urllib.request.urlopen(req, timeout=10):
            label: str = "Liked" if score == 1 else "Disliked"
            logger.info("[ListenBrainz] {}: {} — {}", label, track.artist, track.title)
            submitted += 1
            break
        except urllib.error.HTTPError as http_err:
          logger.error(
            "[ListenBrainz] Feedback failed for {} — {}: {}", track.artist, track.title, http_err.code
          )
          break
        except (TimeoutError, urllib.error.URLError) as e:
          logger.warning(
            "[ListenBrainz] Attempt {} failed for {} — {}: {}", attempt + 1, track.artist, track.title, e
          )
          if attempt < 2:
            time.sleep(5)
          else:
            logger.error("[ListenBrainz] Skipping {} — {} after 3 failed attempts", track.artist, track.title)

    logger.info("[ListenBrainz] Feedback done. {}/{} track(s) updated.", submitted, len(scored))
