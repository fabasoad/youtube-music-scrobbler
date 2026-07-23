from dataclasses import dataclass

@dataclass
class YouTubeMusicTrack:
  video_id: str
  title: str
  artists: list[str]
  duration: str | None
  album: str | None
  like_status: str

@dataclass
class LastFmTrack:
  artist: str
  title: str
  timestamp: int
  album: str | None
  album_artist: str | None
  duration: str
  duration_in_sec: int | None

def convert_track_ytm_to_lfm(track: YouTubeMusicTrack) -> LastFmTrack:
  duration: str = track.duration or "3:00"
  minutes, seconds = map(int, duration.split(":"))
  duration_in_sec: int = minutes * 60 + seconds

  artist: str = ", ".join(track.artists) if track.artists else "Unknown Artist"
  return LastFmTrack(
    artist=artist,
    title=track.title,
    timestamp=0,
    album=track.album,
    album_artist=artist,
    duration=duration,
    duration_in_sec=duration_in_sec,
  )
