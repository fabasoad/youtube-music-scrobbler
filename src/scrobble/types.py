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
