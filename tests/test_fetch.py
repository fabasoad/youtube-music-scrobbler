import importlib.util
import runpy
from unittest.mock import MagicMock, patch

import pytest

from scrobble.fetch import _diff, main
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


def _make_db(recent_ids: list[str] | None = None) -> MagicMock:
  db = MagicMock()
  db.get_recent_video_ids.return_value = recent_ids or []
  return db


def _make_yt_client(tracks: list[YouTubeMusicTrack] | None = None, limit: int = 50) -> MagicMock:
  client = MagicMock()
  client.fetch_history.return_value = tracks or []
  client.history_limit = limit
  return client


class TestFetchMain:
  def test_inserts_new_tracks(self) -> None:
    # recent_ids has matches so _diff finds new tracks ahead of the overlap
    tracks = [_make_track("v3"), _make_track("v1"), _make_track("v2"), _make_track("v3")]
    db = _make_db(recent_ids=["v1", "v2", "v3"])
    yt = _make_yt_client(tracks=tracks)
    with (
      patch("scrobble.fetch.PlayDb", return_value=db),
      patch("scrobble.fetch.YouTubeMusicClient", return_value=yt),
    ):
      main()
    db.insert_plays.assert_called_once()

  def test_no_new_tracks_skips_insert(self) -> None:
    tracks = [_make_track("v1"), _make_track("v2"), _make_track("v3")]
    db = _make_db(recent_ids=["v1", "v2", "v3"])
    yt = _make_yt_client(tracks=tracks)
    with (
      patch("scrobble.fetch.PlayDb", return_value=db),
      patch("scrobble.fetch.YouTubeMusicClient", return_value=yt),
    ):
      main()
    db.insert_plays.assert_not_called()

  def test_exception_exits_with_code_1(self) -> None:
    db = _make_db()
    db.init_schema.side_effect = RuntimeError("boom")
    with (
      patch("scrobble.fetch.PlayDb", return_value=db),
      pytest.raises(SystemExit) as exc_info,
    ):
      main()
    assert exc_info.value.code == 1

  def test_db_closed_on_exception(self) -> None:
    db = _make_db()
    db.init_schema.side_effect = RuntimeError("boom")
    with (
      patch("scrobble.fetch.PlayDb", return_value=db),
      pytest.raises(SystemExit),
    ):
      main()
    db.close.assert_called_once()

  def test_db_closed_on_success(self) -> None:
    db = _make_db()
    yt = _make_yt_client()
    with (
      patch("scrobble.fetch.PlayDb", return_value=db),
      patch("scrobble.fetch.YouTubeMusicClient", return_value=yt),
    ):
      main()
    db.close.assert_called_once()

  def test_dunder_main_calls_main(self) -> None:
    db = _make_db()
    yt = _make_yt_client()
    spec = importlib.util.find_spec("scrobble.fetch")
    assert spec is not None
    with (
      patch("scrobble.db.PlayDb", return_value=db),
      patch("scrobble.yt_music.youtube_music_client.YouTubeMusicClient", return_value=yt),
    ):
      runpy.run_path(spec.origin, run_name="__main__")
