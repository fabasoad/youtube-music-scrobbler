from abc import ABC, abstractmethod

from scrobble.types import ScrobblerTrack


class Scrobbler(ABC):
  # Returns the indices of the tracks that were accepted by the service. Anything left out is
  # deliberately not marked as scrobbled, so the next run picks it up again.
  @abstractmethod
  def scrobble(self, tracks: list[ScrobblerTrack]) -> list[int]:  # pragma: no cover
    pass

  def update_like_status(self, tracks: list[ScrobblerTrack]) -> None:  # noqa: B027
    pass
