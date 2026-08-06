import time
from abc import ABC, abstractmethod

from scrobble.types import YouTubeMusicTrack


class Scrobbler(ABC):
  @staticmethod
  def assign_timestamps(tracks: list[YouTubeMusicTrack]) -> list[tuple[YouTubeMusicTrack, int]]:
    now: int = int(time.time())
    offset: int = 0
    result: list[tuple[YouTubeMusicTrack, int]] = []
    for track in reversed(tracks):
      result.append((track, now - offset))
      offset += track.duration_seconds or 180
    return list(reversed(result))

  @abstractmethod
  def scrobble(self, tracks: list[YouTubeMusicTrack]) -> int:
    pass

  def update_like_status(self, tracks: list[YouTubeMusicTrack]) -> None:  # noqa: B027
    pass
