from scrobble.types import LastFmTrack, YouTubeMusicTrack, convert_track_ytm_to_lfm


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


class TestLastFmTrack:
  def test_fields(self) -> None:
    track = LastFmTrack(
      artist="A",
      title="T",
      timestamp=12345,
      album="Alb",
      album_artist="AA",
      duration="3:00",
      duration_seconds=180,
    )
    assert track.artist == "A"
    assert track.timestamp == 12345
    assert track.duration_seconds == 180


class TestConvertTrackYtmToLfm:
  def test_basic_conversion(self, sample_track: YouTubeMusicTrack) -> None:
    result = convert_track_ytm_to_lfm(sample_track)
    assert isinstance(result, LastFmTrack)
    assert result.artist == "Test Artist"
    assert result.title == "Test Song"
    assert result.album == "Test Album"
    assert result.album_artist == "Test Artist"
    assert result.duration == "3:30"
    assert result.duration_seconds == 210
    assert result.timestamp == 0

  def test_multi_artist_joins_with_ampersand(self, multi_artist_track: YouTubeMusicTrack) -> None:
    result = convert_track_ytm_to_lfm(multi_artist_track)
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
    result = convert_track_ytm_to_lfm(track)
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
    result = convert_track_ytm_to_lfm(track)
    assert result.album is None
    assert result.duration is None
    assert result.duration_seconds is None
