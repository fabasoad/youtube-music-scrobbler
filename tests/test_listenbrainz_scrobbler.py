import urllib.error
from unittest.mock import MagicMock, call, patch

import liblistenbrainz
import liblistenbrainz.errors
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
  with patch("scrobble.scrobblers.listenbrainz.liblistenbrainz.ListenBrainz") as MockClient:
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
    submitted: list[liblistenbrainz.Listen] = scrobbler.client.submit_multiple_listens.call_args[0][0]
    assert len(submitted) == 2

  def test_scrobble_maps_fields_correctly(self) -> None:
    scrobbler = make_scrobbler()
    scrobbler.client.submit_multiple_listens = MagicMock()
    track = make_track(artist="Test Artist", title="Test Song", album="Test Album", timestamp=999)
    scrobbler.scrobble([track])
    submitted: list[liblistenbrainz.Listen] = scrobbler.client.submit_multiple_listens.call_args[0][0]
    listen = submitted[0]
    assert listen.track_name == "Test Song"
    assert listen.artist_name == "Test Artist"
    assert listen.release_name == "Test Album"
    assert listen.listened_at == 999
    assert listen.listening_from == "youtube-music"

  def test_scrobble_returns_zero_on_api_error(self) -> None:
    scrobbler = make_scrobbler()
    scrobbler.client.submit_multiple_listens = MagicMock(
      side_effect=liblistenbrainz.errors.ListenBrainzAPIException(400, "Bad Request")
    )
    result = scrobbler.scrobble([make_track()])
    assert result == 0

  def test_init_sets_auth_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "test-token")
    with patch("scrobble.scrobblers.listenbrainz.liblistenbrainz.ListenBrainz") as MockClient:
      MockClient.return_value.set_auth_token = MagicMock()
      ListenBrainzScrobbler()
      MockClient.return_value.set_auth_token.assert_called_once_with("test-token", check_validity=False)

  def test_scrobble_failed_status_logs_error(self, capsys: pytest.CaptureFixture) -> None:
    scrobbler = make_scrobbler()
    scrobbler.client.submit_multiple_listens = MagicMock(return_value={"status": "error", "message": "bad"})
    scrobbler.scrobble([make_track()])
    assert "bad" in capsys.readouterr().err

  def test_scrobble_no_album(self) -> None:
    scrobbler = make_scrobbler()
    scrobbler.client.submit_multiple_listens = MagicMock()
    track = make_track(album=None, duration=None)
    result = scrobbler.scrobble([track])
    assert result == 1

  def test_scrobble_long_duration(self) -> None:
    scrobbler = make_scrobbler()
    scrobbler.client.submit_multiple_listens = MagicMock()
    track = make_track(duration="10:00")
    result = scrobbler.scrobble([track])
    assert result == 1


def _make_listen(track_name: str, artist_name: str, recording_msid: str | None = "msid-1", recording_mbid: str | None = None) -> MagicMock:
  m = MagicMock()
  m.track_name = track_name
  m.artist_name = artist_name
  m.recording_msid = recording_msid
  m.recording_mbid = recording_mbid
  return m


class TestListenBrainzUpdateLikeStatus:
  def test_indifferent_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTENBRAINZ_USERNAME", "user")
    scrobbler = make_scrobbler()
    track = make_track(like_status="INDIFFERENT")
    scrobbler.update_like_status([track])
    scrobbler.client.get_listens.assert_not_called()

  def test_fetch_listens_error_returns_early(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTENBRAINZ_USERNAME", "user")
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    scrobbler.client.get_listens = MagicMock(
      side_effect=liblistenbrainz.errors.ListenBrainzAPIException(500, "server error")
    )
    with patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen") as mock_urlopen:
      scrobbler.update_like_status([make_track(like_status="LIKE")])
    mock_urlopen.assert_not_called()

  def test_like_posts_feedback_with_msid(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTENBRAINZ_USERNAME", "user")
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    listen = _make_listen("title", "artist", recording_msid="msid-1", recording_mbid=None)
    scrobbler.client.get_listens = MagicMock(return_value=[listen])
    track = make_track(like_status="LIKE", title="Title", artist="Artist")
    with patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen") as mock_urlopen:
      mock_urlopen.return_value.__enter__ = MagicMock(return_value=MagicMock())
      mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
      scrobbler.update_like_status([track])
    mock_urlopen.assert_called_once()

  def test_dislike_posts_feedback_with_mbid(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTENBRAINZ_USERNAME", "user")
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    listen = _make_listen("title", "artist", recording_msid=None, recording_mbid="mbid-1")
    scrobbler.client.get_listens = MagicMock(return_value=[listen])
    track = make_track(like_status="DISLIKE", title="Title", artist="Artist")
    with patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen") as mock_urlopen:
      mock_urlopen.return_value.__enter__ = MagicMock(return_value=MagicMock())
      mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
      scrobbler.update_like_status([track])
    mock_urlopen.assert_called_once()

  def test_listen_not_found_skips(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setenv("LISTENBRAINZ_USERNAME", "user")
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    scrobbler.client.get_listens = MagicMock(return_value=[])
    track = make_track(like_status="LIKE", title="Missing", artist="Nobody")
    with patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen") as mock_urlopen:
      scrobbler.update_like_status([track])
    mock_urlopen.assert_not_called()
    assert "Listen not found" in capsys.readouterr().err

  def test_no_recording_id_skips(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setenv("LISTENBRAINZ_USERNAME", "user")
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    listen = _make_listen("title", "artist", recording_msid=None, recording_mbid=None)
    scrobbler.client.get_listens = MagicMock(return_value=[listen])
    track = make_track(like_status="LIKE", title="Title", artist="Artist")
    with patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen") as mock_urlopen:
      scrobbler.update_like_status([track])
    mock_urlopen.assert_not_called()
    assert "No recording ID" in capsys.readouterr().err

  def test_http_error_breaks_retry(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setenv("LISTENBRAINZ_USERNAME", "user")
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    listen = _make_listen("title", "artist", recording_msid="msid-1")
    scrobbler.client.get_listens = MagicMock(return_value=[listen])
    track = make_track(like_status="LIKE", title="Title", artist="Artist")
    http_err = urllib.error.HTTPError(url=None, code=403, msg="Forbidden", hdrs=None, fp=None)
    with patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen", side_effect=http_err):
      scrobbler.update_like_status([track])
    assert "403" in capsys.readouterr().err

  def test_timeout_retries_then_gives_up(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setenv("LISTENBRAINZ_USERNAME", "user")
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    listen = _make_listen("title", "artist", recording_msid="msid-1")
    scrobbler.client.get_listens = MagicMock(return_value=[listen])
    track = make_track(like_status="LIKE", title="Title", artist="Artist")
    with (
      patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen", side_effect=TimeoutError("timeout")),
      patch("scrobble.scrobblers.listenbrainz.time.sleep") as mock_sleep,
    ):
      scrobbler.update_like_status([track])
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(5)
    assert "Skipping" in capsys.readouterr().err

  def test_url_error_retries_then_succeeds(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTENBRAINZ_USERNAME", "user")
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    listen = _make_listen("title", "artist", recording_msid="msid-1")
    scrobbler.client.get_listens = MagicMock(return_value=[listen])
    track = make_track(like_status="LIKE", title="Title", artist="Artist")
    url_err = urllib.error.URLError("network down")
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=MagicMock())
    mock_ctx.__exit__ = MagicMock(return_value=False)
    with (
      patch(
        "scrobble.scrobblers.listenbrainz.urllib.request.urlopen",
        side_effect=[url_err, mock_ctx],
      ),
      patch("scrobble.scrobblers.listenbrainz.time.sleep"),
    ):
      scrobbler.update_like_status([track])

  def test_both_msid_and_mbid_included(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTENBRAINZ_USERNAME", "user")
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    listen = _make_listen("title", "artist", recording_msid="msid-1", recording_mbid="mbid-1")
    scrobbler.client.get_listens = MagicMock(return_value=[listen])
    track = make_track(like_status="LIKE", title="Title", artist="Artist")
    with patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen") as mock_urlopen:
      mock_urlopen.return_value.__enter__ = MagicMock(return_value=MagicMock())
      mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
      scrobbler.update_like_status([track])
