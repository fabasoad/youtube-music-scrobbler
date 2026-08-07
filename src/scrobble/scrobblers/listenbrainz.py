import os

import liblistenbrainz
import liblistenbrainz.errors

from scrobble.scrobblers.base import Scrobbler
from scrobble.types import ScrobblerTrack


# update_like_status is not implemented: liblistenbrainz exposes no feedback API.
class ListenBrainzScrobbler(Scrobbler):
  def __init__(self) -> None:
    self.client: liblistenbrainz.ListenBrainz = liblistenbrainz.ListenBrainz()
    self.client.set_auth_token(os.environ["LISTENBRAINZ_TOKEN"], check_validity=False)

  def scrobble(self, tracks: list[ScrobblerTrack]) -> int:
    print(f"[ListenBrainz] Scrobbling {len(tracks)} track(s)...")
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
        print(f"[ListenBrainz] Submission failed: {result['message']}")
      for track in tracks:
        album_part: str = "" if track.album is None else f" ({track.album})"
        duration_part: str = "N/A"
        if track.duration:
          duration_part = f"0{track.duration}" if len(track.duration) == 4 else track.duration
        print(f"[ListenBrainz] Scrobbled: [{duration_part}] {track.artist} — {track.title}{album_part}")
      print(f"[ListenBrainz] Done. {len(listens)}/{len(tracks)} track(s) scrobbled.")
      return len(listens)
    except liblistenbrainz.errors.ListenBrainzException as e:
      print(f"[ListenBrainz] Submission failed: {e}")
      return 0
