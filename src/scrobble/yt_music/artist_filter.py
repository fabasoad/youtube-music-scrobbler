from abc import ABC, abstractmethod


class ArtistFilter(ABC):
  @abstractmethod
  def filter(self, artist: str) -> bool:
    pass
