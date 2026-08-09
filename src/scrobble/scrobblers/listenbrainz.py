import json
import os
import urllib.error
import urllib.request

import liblistenbrainz
import liblistenbrainz.errors
from loguru import logger

from scrobble.scrobblers.base import Scrobbler
from scrobble.types import ScrobblerTrack

_FEEDBACK_URL = "https://api.listenbrainz.org/1/feedback/recording-feedback"


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

    try:
      listens: list[liblistenbrainz.Listen] = self.client.get_listens(
        username=os.environ["LISTENBRAINZ_USERNAME"],
        count=200,
      )
    except liblistenbrainz.errors.ListenBrainzException as e:
      logger.error("[ListenBrainz] Failed to fetch listens for feedback: {}", e)
      return

    listen_index: dict[tuple[str, str], liblistenbrainz.Listen] = {
      (listen.track_name.lower(), listen.artist_name.lower()): listen for listen in listens
    }

    token: str = os.environ["LISTENBRAINZ_TOKEN"]
    submitted: int = 0
    for track, score in scored:
      listen: liblistenbrainz.Listen | None = listen_index.get((track.title.lower(), track.artist.lower()))
      if listen is None:
        logger.warning("[ListenBrainz] Listen not found for feedback: {} — {}", track.artist, track.title)
        continue

      body: dict[str, str | int] = {"score": score}
      if listen.recording_msid:
        body["recording_msid"] = listen.recording_msid
      if listen.recording_mbid:
        body["recording_mbid"] = listen.recording_mbid

      if "recording_msid" not in body and "recording_mbid" not in body:
        logger.warning("[ListenBrainz] No recording ID available for: {} — {}", track.artist, track.title)
        continue

      req: urllib.request.Request = urllib.request.Request(
        _FEEDBACK_URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Token {token}", "Content-Type": "application/json"},
        method="POST",
      )
      try:
        with urllib.request.urlopen(req, timeout=10):
          label: str = "Liked" if score == 1 else "Disliked"
          logger.info("[ListenBrainz] {}: {} — {}", label, track.artist, track.title)
          submitted += 1
      except urllib.error.HTTPError as http_err:
        logger.error(
          "[ListenBrainz] Feedback failed for {} — {}: {}", track.artist, track.title, http_err.code
        )

    logger.info("[ListenBrainz] Feedback done. {}/{} track(s) updated.", submitted, len(scored))
