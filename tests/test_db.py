from unittest.mock import MagicMock, call, patch

import pytest

from scrobble.db import PlayDb
from scrobble.types import YouTubeMusicTrack


def _make_db() -> tuple[PlayDb, MagicMock]:
  """Return a PlayDb whose psycopg connection is fully mocked."""
  mock_conn = MagicMock()
  with patch("scrobble.db.psycopg.connect", return_value=mock_conn):
    db = PlayDb()
  return db, mock_conn


def _make_cursor(mock_conn: MagicMock) -> MagicMock:
  cur = MagicMock()
  mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
  mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
  return cur


def _ytm(video_id: str = "v1", artists: list[str] | None = None) -> YouTubeMusicTrack:
  return YouTubeMusicTrack(
    video_id=video_id,
    title="Song",
    artists=artists if artists is not None else ["Artist"],
    duration="3:00",
    album="Album",
    like_status="INDIFFERENT",
    duration_seconds=180,
    thumbnail="https://example.com/t.jpg",
  )


class TestPlayDbInit:
  def test_connects_with_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEON_DATABASE_URL", "postgresql://test")
    with patch("scrobble.db.psycopg.connect") as mock_connect:
      mock_connect.return_value = MagicMock()
      PlayDb()
    mock_connect.assert_called_once_with("postgresql://test")


class TestInitSchema:
  def test_executes_all_ddl_and_commits(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    db.init_schema()
    assert cur.execute.call_count == 7  # 3 CREATE TABLE + 4 CREATE INDEX
    mock_conn.commit.assert_called_once()

  def test_creates_plays_table(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    db.init_schema()
    sql_stmts = [c.args[0] for c in cur.execute.call_args_list]
    assert any("plays" in s and "CREATE TABLE" in s for s in sql_stmts)

  def test_creates_play_artists_table(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    db.init_schema()
    sql_stmts = [c.args[0] for c in cur.execute.call_args_list]
    assert any("play_artists" in s and "CREATE TABLE" in s for s in sql_stmts)

  def test_creates_runs_table(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    db.init_schema()
    sql_stmts = [c.args[0] for c in cur.execute.call_args_list]
    assert any("runs" in s and "CREATE TABLE" in s for s in sql_stmts)


class TestGetRecentVideoIds:
  def test_returns_video_ids(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    cur.fetchall.return_value = [("v1",), ("v2",), ("v3",)]
    result = db.get_recent_video_ids(limit=3)
    assert result == ["v1", "v2", "v3"]

  def test_passes_limit_to_query(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    cur.fetchall.return_value = []
    db.get_recent_video_ids(limit=25)
    cur.execute.assert_called_once()
    assert [25] in [list(c.args[1]) for c in cur.execute.call_args_list]

  def test_default_limit_is_50(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    cur.fetchall.return_value = []
    db.get_recent_video_ids()
    assert [50] in [list(c.args[1]) for c in cur.execute.call_args_list]


class TestInsertPlays:
  def test_empty_list_returns_zero(self) -> None:
    db, _ = _make_db()
    assert db.insert_plays([]) == 0

  def test_returns_track_count(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    cur.fetchone.return_value = (42,)
    result = db.insert_plays([_ytm("v1"), _ytm("v2")])
    assert result == 2

  def test_inserts_artists(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    cur.fetchone.return_value = (1,)
    db.insert_plays([_ytm("v1", artists=["A", "B"])])
    cur.executemany.assert_called_once()
    rows = cur.executemany.call_args.args[1]
    assert rows == [(1, "A", 0), (1, "B", 1)]

  def test_no_artists_skips_executemany(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    cur.fetchone.return_value = (1,)
    db.insert_plays([_ytm("v1", artists=[])])
    cur.executemany.assert_not_called()

  def test_commits_after_insert(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    cur.fetchone.return_value = (1,)
    db.insert_plays([_ytm()])
    mock_conn.commit.assert_called_once()


class TestGetUnscrobbled:
  def test_invalid_scrobbler_raises(self) -> None:
    db, _ = _make_db()
    with pytest.raises(ValueError, match="Unknown scrobbler"):
      db.get_unscrobbled("invalid")

  def test_returns_empty_list_when_no_rows(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    cur.fetchall.return_value = []
    result = db.get_unscrobbled("lastfm")
    assert result == []

  def test_maps_rows_to_tuples(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    cur.fetchall.return_value = [
      (10, "v1", "Song", "3:00", "Album", 180, "https://t.jpg", ["Artist"]),
    ]
    result = db.get_unscrobbled("lastfm")
    assert len(result) == 1
    play_id, track = result[0]
    assert play_id == 10
    assert track.video_id == "v1"
    assert track.title == "Song"
    assert track.artists == ["Artist"]

  def test_listenbrainz_key_accepted(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    cur.fetchall.return_value = []
    db.get_unscrobbled("listenbrainz")
    cur.execute.assert_called_once()


class TestMarkScrobbled:
  def test_empty_ids_returns_immediately(self) -> None:
    db, mock_conn = _make_db()
    db.mark_scrobbled([], "lastfm")
    mock_conn.cursor.assert_not_called()

  def test_invalid_scrobbler_raises(self) -> None:
    db, _ = _make_db()
    with pytest.raises(ValueError, match="Unknown scrobbler"):
      db.mark_scrobbled([1, 2], "unknown")

  def test_executes_update_and_commits(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    db.mark_scrobbled([1, 2, 3], "lastfm")
    cur.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

  def test_passes_ids_to_query(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    db.mark_scrobbled([7, 8], "listenbrainz")
    args = cur.execute.call_args.args
    assert [[7, 8]] in args


class TestInsertRun:
  def test_inserts_and_commits(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    db.insert_run(scrobbled=5, new_tracks=10)
    cur.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

  def test_passes_values(self) -> None:
    db, mock_conn = _make_db()
    cur = _make_cursor(mock_conn)
    db.insert_run(scrobbled=3, new_tracks=7)
    args = cur.execute.call_args.args
    assert (3, 7) in args


class TestClose:
  def test_closes_connection(self) -> None:
    db, mock_conn = _make_db()
    db.close()
    mock_conn.close.assert_called_once()