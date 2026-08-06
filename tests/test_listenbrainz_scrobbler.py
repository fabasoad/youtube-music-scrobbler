from unittest.mock import MagicMock, patch

import pylistenbrainz
import pylistenbrainz.errors
import pytest

from scrobble.scrobblers.listenbrainz import ListenBrainzScrobbler
from scrobble.types import YouTubeMusicTrack


def make_scrobbler() -> ListenBrainzScrobbler:
  with patch("scrobble.scrobblers.listenbrainz.pylistenbrainz.ListenBrainz") as MockClient:
    MockClient.return_value.set_auth_token = MagicMock()
    scrobbler = ListenBrainzScrobbler.__new__(ListenBrainzScrobbler)
    scrobbler.client = MockClient.return_value
  return scrobbler


class TestListenBrainzScrobbler:
  def test_scrobble_submits_all_tracks(self, sample_tracks: list[YouTubeMusicTrack]) -> None:
    scrobbler = make_scrobbler()
    scrobbler.client.submit_multiple_listens = MagicMock()
    with patch("scrobble.scrobblers.base.time") as mock_time:
      mock_time.time.return_value = 1000000
      result = scrobbler.scrobble(sample_tracks)
    assert result == len(sample_tracks)
    scrobbler.client.submit_multiple_listens.assert_called_once()
    submitted: list[pylistenbrainz.Listen] = scrobbler.client.submit_multiple_listens.call_args[0][0]
    assert len(submitted) == len(sample_tracks)

  def test_scrobble_maps_fields_correctly(self, sample_track: YouTubeMusicTrack) -> None:
    scrobbler = make_scrobbler()
    scrobbler.client.submit_multiple_listens = MagicMock()
    with patch("scrobble.scrobblers.base.time") as mock_time:
      mock_time.time.return_value = 1000000
      scrobbler.scrobble([sample_track])
    submitted: list[pylistenbrainz.Listen] = scrobbler.client.submit_multiple_listens.call_args[0][0]
    listen = submitted[0]
    assert listen.track_name == "Test Song"
    assert listen.artist_name == "Test Artist"
    assert listen.release_name == "Test Album"
    assert listen.listened_at == 1000000
    assert listen.listening_from == "youtube-music"

  def test_scrobble_empty_artists_uses_placeholder(self) -> None:
    scrobbler = make_scrobbler()
    scrobbler.client.submit_multiple_listens = MagicMock()
    track = YouTubeMusicTrack(
      video_id="v",
      title="T",
      artists=[],
      duration=None,
      album=None,
      like_status="INDIFFERENT",
    )
    scrobbler.scrobble([track])
    submitted: list[pylistenbrainz.Listen] = scrobbler.client.submit_multiple_listens.call_args[0][0]
    assert submitted[0].artist_name == "Unknown Artist"

  def test_scrobble_returns_zero_on_api_error(self, sample_track: YouTubeMusicTrack) -> None:
    scrobbler = make_scrobbler()
    scrobbler.client.submit_multiple_listens = MagicMock(
      side_effect=pylistenbrainz.errors.ListenBrainzAPIException(400, "Bad Request")
    )
    result = scrobbler.scrobble([sample_track])
    assert result == 0

  def test_scrobble_multi_artist_joined(self, multi_artist_track: YouTubeMusicTrack) -> None:
    scrobbler = make_scrobbler()
    scrobbler.client.submit_multiple_listens = MagicMock()
    scrobbler.scrobble([multi_artist_track])
    submitted: list[pylistenbrainz.Listen] = scrobbler.client.submit_multiple_listens.call_args[0][0]
    assert submitted[0].artist_name == "Artist A & Artist B & Artist C"

  def test_init_sets_auth_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "test-token")
    with patch("scrobble.scrobblers.listenbrainz.pylistenbrainz.ListenBrainz") as MockClient:
      MockClient.return_value.set_auth_token = MagicMock()
      ListenBrainzScrobbler()
      MockClient.return_value.set_auth_token.assert_called_once_with("test-token")
