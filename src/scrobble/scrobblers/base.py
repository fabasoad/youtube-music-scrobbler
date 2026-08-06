from abc import ABC, abstractmethod

from scrobble.types import YouTubeMusicTrack


class Scrobbler(ABC):
  @abstractmethod
  def scrobble(self, tracks: list[YouTubeMusicTrack]) -> int:
    pass

  def update_like_status(self, tracks: list[YouTubeMusicTrack]) -> None:  # noqa: B027
    pass
