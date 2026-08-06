from abc import ABC, abstractmethod

from scrobble.types import ScrobblerTrack


class Scrobbler(ABC):
  @abstractmethod
  def scrobble(self, tracks: list[ScrobblerTrack]) -> int:
    pass

  def update_like_status(self, tracks: list[ScrobblerTrack]) -> None:  # noqa: B027
    pass
