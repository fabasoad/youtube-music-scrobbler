import json

import pytest

from scrobble.snapshot_manager import SnapshotManager
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


class TestGetDiffFromSnapshot:
  def test_empty_snapshot_returns_empty(
    self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
  ) -> None:
    monkeypatch.chdir(tmp_path)
    sm = SnapshotManager()
    current = [_make_track("v1"), _make_track("v2")]
    result = sm.get_diff_from_snapshot(current)
    assert result == []

  def test_no_overlap_returns_all_current(
    self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
  ) -> None:
    monkeypatch.chdir(tmp_path)
    sm = SnapshotManager()
    snapshot = [_make_track("v1"), _make_track("v2")]
    with open("last_snapshot.json", "w") as f:
      json.dump(
        [
          {
            "video_id": t.video_id,
            "title": t.title,
            "artists": t.artists,
            "duration": t.duration,
            "album": t.album,
            "like_status": t.like_status,
            "duration_seconds": t.duration_seconds,
            "thumbnail": t.thumbnail,
          }
          for t in snapshot
        ],
        f,
      )
    current = [_make_track("v3"), _make_track("v4")]
    result = sm.get_diff_from_snapshot(current)
    assert len(result) == 2
    assert result[0].video_id == "v4"  # reversed, oldest first
    assert result[1].video_id == "v3"

  def test_full_overlap_returns_empty(
    self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
  ) -> None:
    monkeypatch.chdir(tmp_path)
    sm = SnapshotManager()
    snapshot = [_make_track("v1"), _make_track("v2"), _make_track("v3")]
    with open("last_snapshot.json", "w") as f:
      json.dump(
        [
          {
            "video_id": t.video_id,
            "title": t.title,
            "artists": t.artists,
            "duration": t.duration,
            "album": t.album,
            "like_status": t.like_status,
            "duration_seconds": t.duration_seconds,
            "thumbnail": t.thumbnail,
          }
          for t in snapshot
        ],
        f,
      )
    current = [_make_track("v1"), _make_track("v2"), _make_track("v3")]
    result = sm.get_diff_from_snapshot(current)
    assert result == []

  def test_partial_overlap_returns_new_tracks(
    self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
  ) -> None:
    monkeypatch.chdir(tmp_path)
    sm = SnapshotManager()
    snapshot = [_make_track("v1"), _make_track("v2"), _make_track("v3")]
    with open("last_snapshot.json", "w") as f:
      json.dump(
        [
          {
            "video_id": t.video_id,
            "title": t.title,
            "artists": t.artists,
            "duration": t.duration,
            "album": t.album,
            "like_status": t.like_status,
            "duration_seconds": t.duration_seconds,
            "thumbnail": t.thumbnail,
          }
          for t in snapshot
        ],
        f,
      )
    # 2 new tracks at the top, then overlap with snapshot
    current = [_make_track("v5"), _make_track("v4"), _make_track("v1"), _make_track("v2"), _make_track("v3")]
    result = sm.get_diff_from_snapshot(current)
    assert len(result) == 2
    assert result[0].video_id == "v4"  # reversed
    assert result[1].video_id == "v5"

  def test_min_seq_parameter(self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    sm = SnapshotManager()
    snapshot = [_make_track("v1"), _make_track("v2"), _make_track("v3")]
    with open("last_snapshot.json", "w") as f:
      json.dump(
        [
          {
            "video_id": t.video_id,
            "title": t.title,
            "artists": t.artists,
            "duration": t.duration,
            "album": t.album,
            "like_status": t.like_status,
            "duration_seconds": t.duration_seconds,
            "thumbnail": t.thumbnail,
          }
          for t in snapshot
        ],
        f,
      )
    # min_seq=1 means a single match is enough
    current = [_make_track("v4"), _make_track("v1"), _make_track("v2")]
    result = sm.get_diff_from_snapshot(current, min_seq=1)
    assert len(result) == 1
    assert result[0].video_id == "v4"


class TestSaveSnapshot:
  def test_creates_file(self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    sm = SnapshotManager()
    tracks = [_make_track("v1"), _make_track("v2")]
    sm.save_snapshot(tracks)
    with open("last_snapshot.json") as f:
      data = json.load(f)
    assert len(data) == 2
    assert data[0]["video_id"] == "v1"

  def test_roundtrip(self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    sm = SnapshotManager()
    original = [
      YouTubeMusicTrack(
        video_id="v1",
        title="Song",
        artists=["A"],
        duration="3:00",
        album="Alb",
        like_status="LIKE",
        duration_seconds=180,
        thumbnail="https://example.com/t.jpg",
      )
    ]
    sm.save_snapshot(original)
    loaded = sm._load_snapshot()
    assert len(loaded) == 1
    assert loaded[0].video_id == "v1"
    assert loaded[0].title == "Song"
    assert loaded[0].thumbnail == "https://example.com/t.jpg"
