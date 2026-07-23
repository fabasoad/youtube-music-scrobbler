from abc import abstractmethod, ABC


class ArtistFilter(ABC):
  @abstractmethod
  def filter(self, artist: str) -> bool:
    pass
