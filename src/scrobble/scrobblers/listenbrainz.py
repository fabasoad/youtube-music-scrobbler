import os

import pylistenbrainz
import pylistenbrainz.errors

from scrobble.scrobblers.base import Scrobbler
from scrobble.types import ScrobblerTrack


# update_like_status is not implemented: pylistenbrainz 0.5.1 (latest) exposes no feedback API.
class ListenBrainzScrobbler(Scrobbler):
  def __init__(self) -> None:
    self.client: pylistenbrainz.ListenBrainz = pylistenbrainz.ListenBrainz()
    self.client.set_auth_token(os.environ["LISTENBRAINZ_TOKEN"])

  def scrobble(self, tracks: list[ScrobblerTrack]) -> int:
    listens: list[pylistenbrainz.Listen] = [
      pylistenbrainz.Listen(
        track_name=track.title,
        artist_name=track.artist,
        listened_at=track.timestamp,
        release_name=track.album,
        listening_from="youtube-music",
      )
      for track in tracks
    ]
    try:
      self.client.submit_multiple_listens(listens)
      for track in tracks:
        album_part: str = "" if track.album is None else f" ({track.album})"
        duration_part: str = "N/A"
        if track.duration:
          duration_part = f"0{track.duration}" if len(track.duration) == 4 else track.duration
        print(f"Scrobbled: [{duration_part}] {track.artist} — {track.title}{album_part}")
      return len(listens)
    except pylistenbrainz.errors.ListenBrainzException as e:
      print(f"ListenBrainz submission failed: {e}")
      return 0
