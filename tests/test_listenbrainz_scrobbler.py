import json
import urllib.error
from unittest.mock import MagicMock, patch

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


def _make_urlopen_ctx() -> MagicMock:
  ctx = MagicMock()
  ctx.__enter__ = MagicMock(return_value=MagicMock())
  ctx.__exit__ = MagicMock(return_value=False)
  return ctx


class TestListenBrainzUpdateLikeStatus:
  def test_indifferent_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    with patch.object(scrobbler, "_lookup_recording_mbid") as mock_lookup:
      scrobbler.update_like_status([make_track(like_status="INDIFFERENT")])
    mock_lookup.assert_not_called()

  def test_like_posts_feedback(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    track = make_track(like_status="LIKE", title="Title", artist="Artist")
    with (
      patch.object(scrobbler, "_lookup_recording_mbid", return_value="mbid-1"),
      patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen", return_value=_make_urlopen_ctx()),
    ):
      scrobbler.update_like_status([track])

  def test_dislike_posts_feedback(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    track = make_track(like_status="DISLIKE", title="Title", artist="Artist")
    with (
      patch.object(scrobbler, "_lookup_recording_mbid", return_value="mbid-1"),
      patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen", return_value=_make_urlopen_ctx()),
    ):
      scrobbler.update_like_status([track])

  def test_lookup_called_with_artist_and_title(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    track = make_track(like_status="LIKE", title="Killpop", artist="Slipknot")
    with (
      patch.object(scrobbler, "_lookup_recording_mbid", return_value="mbid-1") as mock_lookup,
      patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen", return_value=_make_urlopen_ctx()),
    ):
      scrobbler.update_like_status([track])
    mock_lookup.assert_called_once_with("Slipknot", "Killpop")

  def test_lookup_fails_skips_and_warns(
    self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
  ) -> None:
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    track = make_track(like_status="LIKE", title="Missing", artist="Nobody")
    with (
      patch.object(scrobbler, "_lookup_recording_mbid", return_value=None),
      patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen") as mock_urlopen,
    ):
      scrobbler.update_like_status([track])
    mock_urlopen.assert_not_called()
    assert "Recording not found" in capsys.readouterr().err

  def test_http_error_breaks_retry(
    self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
  ) -> None:
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    track = make_track(like_status="LIKE", title="Title", artist="Artist")
    http_err = urllib.error.HTTPError(url=None, code=403, msg="Forbidden", hdrs=None, fp=None)
    with (
      patch.object(scrobbler, "_lookup_recording_mbid", return_value="mbid-1"),
      patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen", side_effect=http_err),
    ):
      scrobbler.update_like_status([track])
    assert "403" in capsys.readouterr().err

  def test_timeout_retries_then_gives_up(
    self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
  ) -> None:
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    track = make_track(like_status="LIKE", title="Title", artist="Artist")
    with (
      patch.object(scrobbler, "_lookup_recording_mbid", return_value="mbid-1"),
      patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen", side_effect=TimeoutError("timeout")),
      patch("scrobble.scrobblers.listenbrainz.time.sleep") as mock_sleep,
    ):
      scrobbler.update_like_status([track])
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(5)
    assert "Skipping" in capsys.readouterr().err

  def test_url_error_retries_then_succeeds(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "tok")
    scrobbler = make_scrobbler()
    track = make_track(like_status="LIKE", title="Title", artist="Artist")
    url_err = urllib.error.URLError("network down")
    with (
      patch.object(scrobbler, "_lookup_recording_mbid", return_value="mbid-1"),
      patch(
        "scrobble.scrobblers.listenbrainz.urllib.request.urlopen",
        side_effect=[url_err, _make_urlopen_ctx()],
      ),
      patch("scrobble.scrobblers.listenbrainz.time.sleep"),
    ):
      scrobbler.update_like_status([track])


class TestListenBrainzLookupRecordingMbid:
  def test_returns_mbid_on_success(self) -> None:
    scrobbler = make_scrobbler()
    resp = MagicMock()
    resp.read.return_value = json.dumps({"recording_mbid": "abc-123"}).encode()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=resp)
    ctx.__exit__ = MagicMock(return_value=False)
    with patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen", return_value=ctx):
      result = scrobbler._lookup_recording_mbid("Artist", "Title")
    assert result == "abc-123"

  def test_returns_none_when_mbid_missing(self) -> None:
    scrobbler = make_scrobbler()
    resp = MagicMock()
    resp.read.return_value = json.dumps({}).encode()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=resp)
    ctx.__exit__ = MagicMock(return_value=False)
    with patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen", return_value=ctx):
      result = scrobbler._lookup_recording_mbid("Artist", "Title")
    assert result is None

  def test_returns_none_on_url_error(self) -> None:
    scrobbler = make_scrobbler()
    with patch(
      "scrobble.scrobblers.listenbrainz.urllib.request.urlopen",
      side_effect=urllib.error.URLError("fail"),
    ):
      result = scrobbler._lookup_recording_mbid("Artist", "Title")
    assert result is None

  def test_returns_none_on_timeout(self) -> None:
    scrobbler = make_scrobbler()
    with patch(
      "scrobble.scrobblers.listenbrainz.urllib.request.urlopen",
      side_effect=TimeoutError("timeout"),
    ):
      result = scrobbler._lookup_recording_mbid("Artist", "Title")
    assert result is None

  def test_returns_none_on_json_decode_error(self) -> None:
    scrobbler = make_scrobbler()
    resp = MagicMock()
    resp.read.return_value = b"not-json"
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=resp)
    ctx.__exit__ = MagicMock(return_value=False)
    with patch("scrobble.scrobblers.listenbrainz.urllib.request.urlopen", return_value=ctx):
      result = scrobbler._lookup_recording_mbid("Artist", "Title")
    assert result is None
