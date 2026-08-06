from unittest.mock import patch

import pytest

from scrobble.scrobblers.base import Scrobbler
from scrobble.scrobblers.lastfm import LastFmScrobbler, LastFmTrack, convert_track_ytm_to_lfm
from scrobble.types import YouTubeMusicTrack


class TestAssignTimestamps:
  def test_single_track(self) -> None:
    tracks = [
      YouTubeMusicTrack(
        video_id="v1",
        title="T",
        artists=["A"],
        duration="3:00",
        album=None,
        like_status="INDIFFERENT",
        duration_seconds=180,
      )
    ]
    with patch("scrobble.scrobblers.base.time") as mock_time:
      mock_time.time.return_value = 1000000
      result = Scrobbler.assign_timestamps(tracks)
    assert len(result) == 1
    assert result[0][1] == 1000000

  def test_multiple_tracks_spaced(self) -> None:
    tracks = [
      YouTubeMusicTrack(
        video_id="v1",
        title="T1",
        artists=["A"],
        duration="3:00",
        album=None,
        like_status="INDIFFERENT",
        duration_seconds=180,
      ),
      YouTubeMusicTrack(
        video_id="v2",
        title="T2",
        artists=["B"],
        duration="4:00",
        album=None,
        like_status="INDIFFERENT",
        duration_seconds=240,
      ),
      YouTubeMusicTrack(
        video_id="v3",
        title="T3",
        artists=["C"],
        duration="2:00",
        album=None,
        like_status="INDIFFERENT",
        duration_seconds=120,
      ),
    ]
    with patch("scrobble.scrobblers.base.time") as mock_time:
      mock_time.time.return_value = 1000000
      result = Scrobbler.assign_timestamps(tracks)
    # Reversed: track[2] gets now, track[1] gets now-120, track[0] gets now-120-240
    assert result[2][1] == 1000000
    assert result[1][1] == 1000000 - 120
    assert result[0][1] == 1000000 - 120 - 240

  def test_none_duration_falls_back_to_180(self) -> None:
    tracks = [
      YouTubeMusicTrack(
        video_id="v1",
        title="T1",
        artists=["A"],
        duration=None,
        album=None,
        like_status="INDIFFERENT",
        duration_seconds=None,
      ),
      YouTubeMusicTrack(
        video_id="v2",
        title="T2",
        artists=["B"],
        duration="3:00",
        album=None,
        like_status="INDIFFERENT",
        duration_seconds=180,
      ),
    ]
    with patch("scrobble.scrobblers.base.time") as mock_time:
      mock_time.time.return_value = 1000000
      result = Scrobbler.assign_timestamps(tracks)
    # Reversed: T2 gets now (offset=0), T1 gets now-180 (offset=180)
    assert result[1][1] == 1000000
    assert result[0][1] == 1000000 - 180
    assert result[0][1] != result[1][1]


class TestConvertTrackYtmToLfm:
  def test_basic_conversion(self, sample_track: YouTubeMusicTrack) -> None:
    result = convert_track_ytm_to_lfm(sample_track, timestamp=12345)
    assert isinstance(result, LastFmTrack)
    assert result.artist == "Test Artist"
    assert result.title == "Test Song"
    assert result.album == "Test Album"
    assert result.album_artist == "Test Artist"
    assert result.duration == "3:30"
    assert result.duration_seconds == 210
    assert result.timestamp == 12345

  def test_multi_artist_joins_with_ampersand(self, multi_artist_track: YouTubeMusicTrack) -> None:
    result = convert_track_ytm_to_lfm(multi_artist_track, timestamp=0)
    assert result.artist == "Artist A & Artist B & Artist C"
    assert result.album_artist == "Artist A"

  def test_empty_artists_uses_placeholder(self) -> None:
    track = YouTubeMusicTrack(
      video_id="v",
      title="T",
      artists=[],
      duration=None,
      album=None,
      like_status="INDIFFERENT",
    )
    result = convert_track_ytm_to_lfm(track, timestamp=0)
    assert result.artist == "Unknown Artist"
    assert result.album_artist == "Unknown Artist"

  def test_none_album_preserved(self) -> None:
    track = YouTubeMusicTrack(
      video_id="v",
      title="T",
      artists=["A"],
      duration=None,
      album=None,
      like_status="INDIFFERENT",
    )
    result = convert_track_ytm_to_lfm(track, timestamp=0)
    assert result.album is None
    assert result.duration is None
    assert result.duration_seconds is None


class TestLogLikeStatus:
  def test_basic_output(self, capsys: pytest.CaptureFixture) -> None:
    track = YouTubeMusicTrack(
      video_id="v1",
      title="My Song",
      artists=["Artist A"],
      duration="3:30",
      album="Album",
      like_status="LIKE",
    )
    LastFmScrobbler._log_like_status("Liked", track)
    out = capsys.readouterr().out
    assert "Liked" in out
    assert "Artist A" in out
    assert "My Song" in out
    assert "Album" in out

  def test_no_album(self, capsys: pytest.CaptureFixture) -> None:
    track = YouTubeMusicTrack(
      video_id="v1",
      title="Song",
      artists=["A"],
      duration=None,
      album=None,
      like_status="LIKE",
    )
    LastFmScrobbler._log_like_status("Disliked", track)
    out = capsys.readouterr().out
    assert "Disliked" in out
    assert "N/A" in out

  def test_multi_artist(self, capsys: pytest.CaptureFixture) -> None:
    track = YouTubeMusicTrack(
      video_id="v1",
      title="Collab",
      artists=["A", "B"],
      duration="4:00",
      album=None,
      like_status="LIKE",
    )
    LastFmScrobbler._log_like_status("Liked", track)
    out = capsys.readouterr().out
    assert "A & B" in out
