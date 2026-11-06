from unittest.mock import MagicMock, call, patch

import pylast
import pytest

from scrobble.scrobblers.lastfm import LastFmScrobbler
from scrobble.types import ScrobblerTrack


def make_track(**kwargs) -> ScrobblerTrack:
  defaults = {
    "artist": "Artist",
    "title": "Title",
    "album": None,
    "album_artist": "Artist",
    "duration": "3:00",
    "duration_seconds": 180,
    "timestamp": 1000000,
    "like_status": "INDIFFERENT",
  }
  return ScrobblerTrack(**{**defaults, **kwargs})


class TestLastFmScrobblerFormatDuration:
  def test_short_duration_padded(self) -> None:
    assert LastFmScrobbler._format_duration("3:00") == "03:00"

  def test_long_duration_unchanged(self) -> None:
    assert LastFmScrobbler._format_duration("10:00") == "10:00"

  def test_none_returns_na(self) -> None:
    assert LastFmScrobbler._format_duration(None) == "N/A"


class TestLastFmScrobblerUpdateLikeStatus:
  def test_like_calls_love(self, capsys: pytest.CaptureFixture) -> None:
    from unittest.mock import MagicMock, patch

    scrobbler = LastFmScrobbler.__new__(LastFmScrobbler)
    mock_network = MagicMock()
    scrobbler.network = mock_network
    track = make_track(like_status="LIKE", artist="A", title="T", album="Alb")

    with patch.object(scrobbler.network, "get_track") as mock_get_track:
      mock_pylast_track = MagicMock()
      mock_get_track.return_value = mock_pylast_track
      scrobbler.update_like_status([track])

    mock_pylast_track.love.assert_called_once()
    err = capsys.readouterr().err
    assert "Liked" in err
    assert "A" in err
    assert "T" in err
    assert "Alb" in err

  def test_dislike_calls_unlove(self, capsys: pytest.CaptureFixture) -> None:
    from unittest.mock import MagicMock, patch

    scrobbler = LastFmScrobbler.__new__(LastFmScrobbler)
    scrobbler.network = MagicMock()
    track = make_track(like_status="DISLIKE")

    with patch.object(scrobbler.network, "get_track") as mock_get_track:
      mock_pylast_track = MagicMock()
      mock_get_track.return_value = mock_pylast_track
      scrobbler.update_like_status([track])

    mock_pylast_track.unlove.assert_called_once()
    err = capsys.readouterr().err
    assert "Disliked" in err

  def test_indifferent_skipped(self) -> None:
    scrobbler = LastFmScrobbler.__new__(LastFmScrobbler)
    scrobbler.network = MagicMock()
    track = make_track(like_status="INDIFFERENT")
    scrobbler.update_like_status([track])
    scrobbler.network.get_track.assert_not_called()

  def test_like_with_no_album(self) -> None:
    scrobbler = LastFmScrobbler.__new__(LastFmScrobbler)
    scrobbler.network = MagicMock()
    mock_pylast_track = MagicMock()
    scrobbler.network.get_track.return_value = mock_pylast_track
    track = make_track(like_status="LIKE", album=None)
    scrobbler.update_like_status([track])
    mock_pylast_track.love.assert_called_once()


class TestLastFmScrobblerInit:
  def test_init_reads_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LASTFM_API_KEY", "key")
    monkeypatch.setenv("LASTFM_SECRET", "secret")
    monkeypatch.setenv("LASTFM_USERNAME", "user")
    monkeypatch.setenv("LASTFM_PASSWORD", "pass")
    with patch("scrobble.scrobblers.lastfm.pylast.LastFMNetwork") as mock_net:
      LastFmScrobbler()
      mock_net.assert_called_once()


class TestLastFmScrobblerScrobble:
  def _make_scrobbler(self) -> LastFmScrobbler:
    s = LastFmScrobbler.__new__(LastFmScrobbler)
    s.network = MagicMock()
    return s

  def test_scrobble_single_track(self) -> None:
    s = self._make_scrobbler()
    with patch("scrobble.scrobblers.lastfm.time.sleep"):
      result = s.scrobble([make_track()])
    assert result == [0]
    s.network.scrobble.assert_called_once()

  def test_scrobble_returns_indices(self) -> None:
    s = self._make_scrobbler()
    with patch("scrobble.scrobblers.lastfm.time.sleep"):
      result = s.scrobble([make_track(title="T1"), make_track(title="T2")])
    assert result == [0, 1]

  def test_scrobble_with_album(self) -> None:
    s = self._make_scrobbler()
    track = make_track(album="My Album")
    with patch("scrobble.scrobblers.lastfm.time.sleep"):
      s.scrobble([track])
    call_kwargs = s.network.scrobble.call_args[1]
    assert call_kwargs["album"] == "My Album"

  def test_scrobble_with_no_album(self) -> None:
    s = self._make_scrobbler()
    track = make_track(album=None)
    with patch("scrobble.scrobblers.lastfm.time.sleep"):
      s.scrobble([track])
    call_kwargs = s.network.scrobble.call_args[1]
    assert call_kwargs["album"] is None

  def test_scrobble_sleeps_between_tracks(self) -> None:
    s = self._make_scrobbler()
    with patch("scrobble.scrobblers.lastfm.time.sleep") as mock_sleep:
      s.scrobble([make_track(title="T1"), make_track(title="T2")])
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(1)

  def test_scrobble_retries_on_network_error_then_succeeds(self) -> None:
    s = self._make_scrobbler()
    s.network.scrobble.side_effect = [pylast.NetworkError(None, "err"), None]
    with patch("scrobble.scrobblers.lastfm.time.sleep") as mock_sleep:
      result = s.scrobble([make_track()])
    assert result == [0]
    assert mock_sleep.call_args_list[0] == call(5)

  def test_scrobble_retries_on_malformed_response_then_succeeds(self) -> None:
    s = self._make_scrobbler()
    s.network.scrobble.side_effect = [pylast.MalformedResponseError(MagicMock(), "err"), None]
    with patch("scrobble.scrobblers.lastfm.time.sleep"):
      result = s.scrobble([make_track()])
    assert result == [0]

  def test_scrobble_skips_after_three_failures(self) -> None:
    s = self._make_scrobbler()
    s.network.scrobble.side_effect = pylast.NetworkError(None, "err")
    with patch("scrobble.scrobblers.lastfm.time.sleep") as mock_sleep:
      result = s.scrobble([make_track()])
    assert result == []
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(5)

  def test_scrobble_empty_tracks(self) -> None:
    s = self._make_scrobbler()
    result = s.scrobble([])
    assert result == []
    s.network.scrobble.assert_not_called()


def _ws_error(status: int | str) -> pylast.WSError:
  return pylast.WSError(None, status, f"failed with status {status}")


class TestLastFmScrobblerTransientErrors:
  def _make_scrobbler(self) -> LastFmScrobbler:
    s = LastFmScrobbler.__new__(LastFmScrobbler)
    s.network = MagicMock()
    return s

  def test_scrobble_retries_on_http_503_then_succeeds(self) -> None:
    s = self._make_scrobbler()
    s.network.scrobble.side_effect = [_ws_error(503), None]
    with patch("scrobble.scrobblers.lastfm.time.sleep") as mock_sleep:
      result = s.scrobble([make_track()])
    assert result == [0]
    assert mock_sleep.call_args_list[0] == call(5)

  def test_scrobble_retries_on_rate_limit_then_succeeds(self) -> None:
    s = self._make_scrobbler()
    s.network.scrobble.side_effect = [_ws_error("29"), None]
    with patch("scrobble.scrobblers.lastfm.time.sleep"):
      result = s.scrobble([make_track()])
    assert result == [0]

  def test_scrobble_does_not_retry_permanent_error(self) -> None:
    s = self._make_scrobbler()
    s.network.scrobble.side_effect = _ws_error("10")  # invalid API key
    with patch("scrobble.scrobblers.lastfm.time.sleep") as mock_sleep:
      result = s.scrobble([make_track()])
    assert result == []
    assert s.network.scrobble.call_count == 1
    mock_sleep.assert_not_called()

  def test_scrobble_keeps_going_after_one_track_fails(self) -> None:
    s = self._make_scrobbler()
    s.network.scrobble.side_effect = [_ws_error("10"), None]
    with patch("scrobble.scrobblers.lastfm.time.sleep"):
      result = s.scrobble([make_track(title="T1"), make_track(title="T2")])
    assert result == [1]


class TestLastFmScrobblerInitRetries:
  @staticmethod
  def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LASTFM_API_KEY", "key")
    monkeypatch.setenv("LASTFM_SECRET", "secret")
    monkeypatch.setenv("LASTFM_USERNAME", "user")
    monkeypatch.setenv("LASTFM_PASSWORD", "pass")

  def test_init_retries_transient_failure_then_succeeds(self, monkeypatch: pytest.MonkeyPatch) -> None:
    self._set_env(monkeypatch)
    network = MagicMock()
    with (
      patch(
        "scrobble.scrobblers.lastfm.pylast.LastFMNetwork",
        side_effect=[pylast.NetworkError(None, "read timed out"), network],
      ) as mock_net,
      patch("scrobble.scrobblers.lastfm.time.sleep") as mock_sleep,
    ):
      scrobbler = LastFmScrobbler()
    assert scrobbler.network is network
    assert mock_net.call_count == 2
    mock_sleep.assert_called_once_with(5)

  def test_init_raises_after_three_transient_failures(self, monkeypatch: pytest.MonkeyPatch) -> None:
    self._set_env(monkeypatch)
    with (
      patch(
        "scrobble.scrobblers.lastfm.pylast.LastFMNetwork",
        side_effect=pylast.NetworkError(None, "read timed out"),
      ) as mock_net,
      patch("scrobble.scrobblers.lastfm.time.sleep"),
      pytest.raises(pylast.NetworkError),
    ):
      LastFmScrobbler()
    assert mock_net.call_count == 3

  def test_init_does_not_retry_permanent_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
    self._set_env(monkeypatch)
    with (
      patch("scrobble.scrobblers.lastfm.pylast.LastFMNetwork", side_effect=_ws_error("4")) as mock_net,
      patch("scrobble.scrobblers.lastfm.time.sleep") as mock_sleep,
      pytest.raises(pylast.WSError),
    ):
      LastFmScrobbler()
    assert mock_net.call_count == 1
    mock_sleep.assert_not_called()

  def test_scrobble_does_not_retry_generic_pylast_error(self) -> None:
    s = LastFmScrobbler.__new__(LastFmScrobbler)
    s.network = MagicMock()
    s.network.scrobble.side_effect = pylast.PyLastError("unexpected")
    with patch("scrobble.scrobblers.lastfm.time.sleep") as mock_sleep:
      result = s.scrobble([make_track()])
    assert result == []
    assert s.network.scrobble.call_count == 1
    mock_sleep.assert_not_called()
