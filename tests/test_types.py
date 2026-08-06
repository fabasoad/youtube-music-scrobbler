import pytest

from scrobble.types import ScrobblerTrack, YouTubeMusicTrack, prepare_tracks


class TestYouTubeMusicTrack:
  def test_required_fields(self) -> None:
    track = YouTubeMusicTrack(
      video_id="v1",
      title="Title",
      artists=["Artist"],
      duration="3:00",
      album="Album",
      like_status="INDIFFERENT",
    )
    assert track.video_id == "v1"
    assert track.title == "Title"
    assert track.artists == ["Artist"]
    assert track.duration == "3:00"
    assert track.album == "Album"
    assert track.like_status == "INDIFFERENT"
    assert track.duration_seconds is None
    assert track.thumbnail is None

  def test_optional_fields(self, sample_track: YouTubeMusicTrack) -> None:
    assert sample_track.duration_seconds == 210
    assert sample_track.thumbnail == "https://example.com/thumb.jpg"

  def test_empty_artists(self) -> None:
    track = YouTubeMusicTrack(
      video_id="v2",
      title="No Artist",
      artists=[],
      duration=None,
      album=None,
      like_status="INDIFFERENT",
    )
    assert track.artists == []

  def test_multiple_artists(self, multi_artist_track: YouTubeMusicTrack) -> None:
    assert len(multi_artist_track.artists) == 3
    assert multi_artist_track.artists[0] == "Artist A"


class TestPrepareTracks:
  def test_returns_scrobbler_tracks(self, sample_track: YouTubeMusicTrack) -> None:
    result = prepare_tracks([sample_track])
    assert len(result) == 1
    assert isinstance(result[0], ScrobblerTrack)

  def test_maps_fields(self, sample_track: YouTubeMusicTrack) -> None:
    result = prepare_tracks([sample_track])
    t = result[0]
    assert t.artist == "Test Artist"
    assert t.album_artist == "Test Artist"
    assert t.title == "Test Song"
    assert t.album == "Test Album"
    assert t.duration == "3:30"
    assert t.duration_seconds == 210
    assert t.like_status == "INDIFFERENT"

  def test_multi_artist_joined(self, multi_artist_track: YouTubeMusicTrack) -> None:
    result = prepare_tracks([multi_artist_track])
    assert result[0].artist == "Artist A & Artist B & Artist C"
    assert result[0].album_artist == "Artist A"

  def test_empty_artists_uses_placeholder(self) -> None:
    track = YouTubeMusicTrack(
      video_id="v",
      title="T",
      artists=[],
      duration=None,
      album=None,
      like_status="INDIFFERENT",
    )
    result = prepare_tracks([track])
    assert result[0].artist == "Unknown Artist"
    assert result[0].album_artist == "Unknown Artist"

  def test_timestamps_assigned_oldest_first(self) -> None:
    from unittest.mock import patch

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
        duration="2:00",
        album=None,
        like_status="INDIFFERENT",
        duration_seconds=120,
      ),
    ]
    with patch("scrobble.types.time") as mock_time:
      mock_time.time.return_value = 1000000
      result = prepare_tracks(tracks)
    # T2 is most recent → timestamp=now; T1 played before T2 → now-120
    assert result[1].timestamp == 1000000
    assert result[0].timestamp == 1000000 - 120

  def test_none_duration_falls_back_to_180(self) -> None:
    from unittest.mock import patch

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
    with patch("scrobble.types.time") as mock_time:
      mock_time.time.return_value = 1000000
      result = prepare_tracks(tracks)
    assert result[1].timestamp == 1000000
    assert result[0].timestamp == 1000000 - 180
    assert result[0].timestamp != result[1].timestamp

  def test_empty_list(self) -> None:
    assert prepare_tracks([]) == []

  def test_preserves_order_oldest_first(self, sample_tracks: list[YouTubeMusicTrack]) -> None:
    result = prepare_tracks(sample_tracks)
    assert len(result) == len(sample_tracks)
    assert result[0].title == sample_tracks[0].title
    assert result[-1].title == sample_tracks[-1].title

  def test_timestamps_decrease_toward_past(self, sample_tracks: list[YouTubeMusicTrack]) -> None:
    result = prepare_tracks(sample_tracks)
    # Each earlier track has a smaller (older) timestamp
    for i in range(len(result) - 1):
      assert result[i].timestamp < result[i + 1].timestamp

    @pytest.mark.parametrize("like_status", ["LIKE", "DISLIKE", "INDIFFERENT"])
    def test_like_status_preserved(self, like_status: str) -> None:
      track = YouTubeMusicTrack(
        video_id="v",
        title="T",
        artists=["A"],
        duration=None,
        album=None,
        like_status=like_status,
      )
      result = prepare_tracks([track])
      assert result[0].like_status == like_status
