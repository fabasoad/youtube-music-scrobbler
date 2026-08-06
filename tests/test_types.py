from scrobble.types import YouTubeMusicTrack


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
