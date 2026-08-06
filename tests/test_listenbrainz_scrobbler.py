from unittest.mock import MagicMock, patch

import pylistenbrainz
import pylistenbrainz.errors
import pytest

from scrobble.scrobblers.listenbrainz import ListenBrainzScrobbler
from scrobble.types import ScrobblerTrack


def make_track(**kwargs) -> ScrobblerTrack:
  defaults = {
    "artist": "Artist",
    "title": "Title",
    "album": "Album",
    "album_artist": "Artist",
    "duration": "3:00",
    "duration_seconds": 180,
    "timestamp": 1000000,
    "like_status": "INDIFFERENT",
  }
  return ScrobblerTrack(**{**defaults, **kwargs})


def make_scrobbler() -> ListenBrainzScrobbler:
  with patch("scrobble.scrobblers.listenbrainz.pylistenbrainz.ListenBrainz") as MockClient:
    MockClient.return_value.set_auth_token = MagicMock()
    scrobbler = ListenBrainzScrobbler.__new__(ListenBrainzScrobbler)
    scrobbler.client = MockClient.return_value
  return scrobbler


class TestListenBrainzScrobbler:
  def test_scrobble_submits_all_tracks(self) -> None:
    scrobbler = make_scrobbler()
    scrobbler.client.submit_multiple_listens = MagicMock()
    tracks = [make_track(title="T1"), make_track(title="T2")]
    result = scrobbler.scrobble(tracks)
    assert result == 2
    scrobbler.client.submit_multiple_listens.assert_called_once()
    submitted: list[pylistenbrainz.Listen] = scrobbler.client.submit_multiple_listens.call_args[0][0]
    assert len(submitted) == 2

  def test_scrobble_maps_fields_correctly(self) -> None:
    scrobbler = make_scrobbler()
    scrobbler.client.submit_multiple_listens = MagicMock()
    track = make_track(artist="Test Artist", title="Test Song", album="Test Album", timestamp=999)
    scrobbler.scrobble([track])
    submitted: list[pylistenbrainz.Listen] = scrobbler.client.submit_multiple_listens.call_args[0][0]
    listen = submitted[0]
    assert listen.track_name == "Test Song"
    assert listen.artist_name == "Test Artist"
    assert listen.release_name == "Test Album"
    assert listen.listened_at == 999
    assert listen.listening_from == "youtube-music"

  def test_scrobble_returns_zero_on_api_error(self) -> None:
    scrobbler = make_scrobbler()
    scrobbler.client.submit_multiple_listens = MagicMock(
      side_effect=pylistenbrainz.errors.ListenBrainzAPIException(400, "Bad Request")
    )
    result = scrobbler.scrobble([make_track()])
    assert result == 0

  def test_init_sets_auth_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "test-token")
    with patch("scrobble.scrobblers.listenbrainz.pylistenbrainz.ListenBrainz") as MockClient:
      MockClient.return_value.set_auth_token = MagicMock()
      ListenBrainzScrobbler()
      MockClient.return_value.set_auth_token.assert_called_once_with("test-token")
