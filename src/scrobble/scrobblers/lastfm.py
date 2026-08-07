import os
import time

import pylast

from scrobble.scrobblers.base import Scrobbler
from scrobble.types import ScrobblerTrack


class LastFmScrobbler(Scrobbler):
  def __init__(self) -> None:
    self.network: pylast.LastFMNetwork = pylast.LastFMNetwork(
      api_key=os.environ["LASTFM_API_KEY"],
      api_secret=os.environ["LASTFM_SECRET"],
      username=os.environ["LASTFM_USERNAME"],
      password_hash=pylast.md5(os.environ["LASTFM_PASSWORD"]),
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

    print(f"[Last.fm] Updating feedback for {len(scored)} track(s)...")

    submitted: int = 0
    for track in scored:
      pylast_track: pylast.Track = self.network.get_track(track.artist, track.title)
      album_part: str = "" if track.album is None else f" ({track.album})"
      duration_part: str = LastFmScrobbler._format_duration(track.duration)
      if track.like_status == "LIKE":
        pylast_track.love()
        print(f"[Last.fm] Liked: [{duration_part}] {track.artist} — {track.title}{album_part}")
      else:
        pylast_track.unlove()
        print(f"[Last.fm] Disliked: [{duration_part}] {track.artist} — {track.title}{album_part}")
      submitted += 1

    print(f"[Last.fm] Feedback done. {submitted}/{len(scored)} track(s) updated.")

  def scrobble(self, tracks: list[ScrobblerTrack]) -> int:
    print(f"[Last.fm] Scrobbling {len(tracks)} track(s)...")
    scrobbled: int = 0
    for track in tracks:
      for attempt in range(3):
        try:
          self.network.scrobble(
            artist=track.artist,
            title=track.title,
            timestamp=track.timestamp,
            album=track.album,
            album_artist=track.album_artist,
            duration=track.duration_seconds,
          )
          album_part: str = "" if track.album is None else f" ({track.album})"
          duration_part: str = LastFmScrobbler._format_duration(track.duration)
          print(f"[Last.fm] Scrobbled: [{duration_part}] {track.artist} — {track.title}{album_part}")
          scrobbled += 1
          time.sleep(1)
          break
        except (pylast.NetworkError, pylast.MalformedResponseError) as e:
          print(f"[Last.fm] Attempt {attempt + 1} failed for {track.title}: {e}")
          if attempt < 2:
            time.sleep(5)
          else:
            print(f"[Last.fm] Skipping: {track.title} after 3 failed attempts")

    print(f"[Last.fm] Done. {scrobbled}/{len(tracks)} track(s) scrobbled.")
    return scrobbled
