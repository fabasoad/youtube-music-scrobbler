import os
import time

import pylast

from scrobble.types import LastFmTrack, YouTubeMusicTrack, convert_track_ytm_to_lfm


class LastFmClient:
  def __init__(self) -> None:
    self.network: pylast.LastFMNetwork = pylast.LastFMNetwork(
      api_key=os.environ["LASTFM_API_KEY"],
      api_secret=os.environ["LASTFM_SECRET"],
      username=os.environ["LASTFM_USERNAME"],
      password_hash=pylast.md5(os.environ["LASTFM_PASSWORD"]),
    )

  @staticmethod
  def _assign_timestamps(tracks: list[LastFmTrack]) -> list[LastFmTrack]:
    now: int = int(time.time())
    offset: int = 0
    for track in reversed(tracks):
      track.timestamp = now - offset
      offset += track.duration_seconds
    return tracks

  @staticmethod
  def _log_like_status(prefix: str, track: YouTubeMusicTrack) -> None:
    artist_part: str = " & ".join(track.artists) if track.artists else "Unknown Artist"
    album_part: str = "" if track.album is None else f" ({track.album})"
    duration_part: str = " N/A "
    if track.duration:
      duration_part = f"0{track.duration}" if len(track.duration) == 4 else track.duration
    print(f"{prefix}: [{duration_part}] {artist_part} — {track.title}{album_part}")

  def update_like_status(self, tracks: list[YouTubeMusicTrack]) -> None:
    for track in tracks:
      if track.like_status != "INDIFFERENT":
        artist: str = " & ".join(track.artists) if track.artists else "Unknown Artist"
        pylast_track: pylast.Track = self.network.get_track(
          artist,
          track.title,
        )
        if track.like_status == "LIKE":
          pylast_track.love()
          LastFmClient._log_like_status("Liked", track)
        else:
          pylast_track.unlove()
          LastFmClient._log_like_status("Disliked", track)

  def scrobble(self, tracks: list[YouTubeMusicTrack]) -> int:
    lastfm_tracks = LastFmClient._assign_timestamps(
      [convert_track_ytm_to_lfm(track) for track in tracks],
    )
    scrobbled: int = 0
    for lastfm_track in lastfm_tracks:
      for attempt in range(3):
        try:
          self.network.scrobble(
            artist=lastfm_track.artist,
            title=lastfm_track.title,
            timestamp=lastfm_track.timestamp,
            album=lastfm_track.album,
            album_artist=lastfm_track.artist,
            duration=lastfm_track.duration_seconds,
          )
          album_part: str = "" if lastfm_track.album is None else f" ({lastfm_track.album})"
          duration_part: str = "N/A"
          if lastfm_track.duration:
            duration_part = (
              f"0{lastfm_track.duration}" if len(lastfm_track.duration) == 4 else lastfm_track.duration
            )
          print(f"Scrobbled: [{duration_part}] {lastfm_track.artist} — {lastfm_track.title}{album_part}")
          scrobbled += 1
          time.sleep(1)
          break
        except (pylast.NetworkError, pylast.MalformedResponseError) as e:
          print(f"Attempt {attempt + 1} failed for {lastfm_track.title}: {e}")
          if attempt < 2:
            time.sleep(5)
          else:
            print(f"Skipping: {lastfm_track.title} after 3 failed attempts")

    return scrobbled
