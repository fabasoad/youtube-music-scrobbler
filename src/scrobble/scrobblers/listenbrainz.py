import os

import pylistenbrainz
import pylistenbrainz.errors

from scrobble.scrobblers.base import Scrobbler
from scrobble.types import YouTubeMusicTrack


class ListenBrainzScrobbler(Scrobbler):
  def __init__(self) -> None:
    self.client: pylistenbrainz.ListenBrainz = pylistenbrainz.ListenBrainz()
    self.client.set_auth_token(os.environ["LISTENBRAINZ_TOKEN"])

  def scrobble(self, tracks: list[YouTubeMusicTrack]) -> int:
    timestamped = Scrobbler.assign_timestamps(tracks)
    listens: list[pylistenbrainz.Listen] = []
    for track, ts in timestamped:
      artist: str = " & ".join(track.artists) if track.artists else "Unknown Artist"
      listens.append(
        pylistenbrainz.Listen(
          track_name=track.title,
          artist_name=artist,
          listened_at=ts,
          release_name=track.album,
          listening_from="youtube-music",
        )
      )
    try:
      self.client.submit_multiple_listens(listens)
      for track, _ in timestamped:
        artist = " & ".join(track.artists) if track.artists else "Unknown Artist"
        album_part: str = "" if track.album is None else f" ({track.album})"
        duration_part: str = "N/A"
        if track.duration:
          duration_part = f"0{track.duration}" if len(track.duration) == 4 else track.duration
        print(f"Scrobbled: [{duration_part}] {artist} — {track.title}{album_part}")
      return len(listens)
    except pylistenbrainz.errors.ListenBrainzException as e:
      print(f"ListenBrainz submission failed: {e}")
      return 0
