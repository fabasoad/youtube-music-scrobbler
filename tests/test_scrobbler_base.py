from scrobble.scrobblers.base import Scrobbler
from scrobble.types import ScrobblerTrack


class _ConcreteScrobbler(Scrobbler):
  def scrobble(self, tracks: list[ScrobblerTrack]) -> int:
    return 0


class TestScrobblerBase:
  def test_default_update_like_status_is_noop(self) -> None:
    s = _ConcreteScrobbler()
    s.update_like_status([])
