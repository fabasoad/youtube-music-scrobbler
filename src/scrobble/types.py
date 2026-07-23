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
class LastFmTrack:
  artist: str
  title: str
  timestamp: int
  album: str | None
  album_artist: str | None
  duration: str | None
  duration_seconds: int | None


def convert_track_ytm_to_lfm(track: YouTubeMusicTrack) -> LastFmTrack:
  artist: str = " & ".join(track.artists) if track.artists else "Unknown Artist"
  album_artist: str = track.artists[0] if track.artists else "Unknown Artist"
  return LastFmTrack(
    artist=artist,
    title=track.title,
    timestamp=0,
    album=track.album,
    album_artist=album_artist,
    duration=track.duration,
    duration_seconds=track.duration_seconds,
  )
