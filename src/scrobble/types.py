import time
from dataclasses import dataclass, field


@dataclass
class YouTubeMusicTrack:
  video_id: str
  title: str
  artists: list[str]
  duration: str | None
  album: str | None
  like_status: str
  duration_seconds: int | None = field(default=None)
  thumbnail: str | None = field(default=None)


@dataclass
class ScrobblerTrack:
  artist: str
  title: str
  album: str | None
  album_artist: str | None
  duration: str | None
  duration_seconds: int | None
  timestamp: int
  like_status: str | None


def prepare_tracks(tracks: list[YouTubeMusicTrack]) -> list[ScrobblerTrack]:
  now: int = int(time.time())
  offset: int = 0
  result: list[ScrobblerTrack] = []
  for track in reversed(tracks):
    artist: str = " & ".join(track.artists) if track.artists else "Unknown Artist"
    album_artist: str = track.artists[0] if track.artists else "Unknown Artist"
    result.append(
      ScrobblerTrack(
        artist=artist,
        title=track.title,
        album=track.album,
        album_artist=album_artist,
        duration=track.duration,
        duration_seconds=track.duration_seconds,
        timestamp=now - offset,
        like_status=track.like_status,
      )
    )
    offset += track.duration_seconds or 180
  return list(reversed(result))
