from scrobble.fetch import _diff
from scrobble.types import YouTubeMusicTrack


def _make_track(video_id: str, title: str = "Song") -> YouTubeMusicTrack:
  return YouTubeMusicTrack(
    video_id=video_id,
    title=title,
    artists=["Artist"],
    duration="3:00",
    album=None,
    like_status="INDIFFERENT",
    duration_seconds=180,
  )


class TestDiff:
  def test_empty_recent_ids_returns_empty(self) -> None:
    current = [_make_track("v1"), _make_track("v2")]
    assert _diff(current, []) == []

  def test_no_overlap_returns_all_current(self) -> None:
    recent_ids = ["v1", "v2", "v3"]
    current = [_make_track("v4"), _make_track("v5"), _make_track("v6")]
    result = _diff(current, recent_ids)
    assert len(result) == 3
    assert result[0].video_id == "v6"  # oldest first
    assert result[2].video_id == "v4"

  def test_full_overlap_returns_empty(self) -> None:
    recent_ids = ["v1", "v2", "v3"]
    current = [_make_track("v1"), _make_track("v2"), _make_track("v3")]
    assert _diff(current, recent_ids) == []

  def test_partial_overlap_returns_new_tracks(self) -> None:
    recent_ids = ["v1", "v2", "v3"]
    current = [_make_track("v5"), _make_track("v4"), _make_track("v1"), _make_track("v2"), _make_track("v3")]
    result = _diff(current, recent_ids)
    assert len(result) == 2
    assert result[0].video_id == "v4"  # oldest first
    assert result[1].video_id == "v5"

  def test_min_seq_parameter(self) -> None:
    recent_ids = ["v1", "v2", "v3"]
    current = [_make_track("v4"), _make_track("v1"), _make_track("v2")]
    result = _diff(current, recent_ids, min_seq=1)
    assert len(result) == 1
    assert result[0].video_id == "v4"
