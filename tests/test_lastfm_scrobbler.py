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
    from unittest.mock import MagicMock

    scrobbler = LastFmScrobbler.__new__(LastFmScrobbler)
    scrobbler.network = MagicMock()
    track = make_track(like_status="INDIFFERENT")
    scrobbler.update_like_status([track])
    scrobbler.network.get_track.assert_not_called()
