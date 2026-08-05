from datetime import UTC, datetime, timedelta

import pytest

from scrobble.main import prune_logs, write_log, write_summary
from scrobble.types import YouTubeMusicTrack


class TestPruneLogs:
  def test_no_file(self, tmp_path: pytest.TempPathFactory) -> None:
    log_path = str(tmp_path / "missing.log")
    prune_logs(log_path)  # should not raise

  def test_keeps_recent_lines(self, tmp_path: pytest.TempPathFactory) -> None:
    log_path = str(tmp_path / "runs.log")
    now = datetime.now(UTC)
    recent = (now - timedelta(days=10)).isoformat(timespec="seconds")
    old = (now - timedelta(days=400)).isoformat(timespec="seconds")
    with open(log_path, "w") as f:
      f.write(f"{recent} | scrobbled=5 | new_tracks=3\n")
      f.write(f"{old} | scrobbled=2 | new_tracks=1\n")
    prune_logs(log_path)
    with open(log_path) as f:
      lines = f.readlines()
    assert len(lines) == 1
    assert "scrobbled=5" in lines[0]

  def test_keeps_unparseable_lines(self, tmp_path: pytest.TempPathFactory) -> None:
    log_path = str(tmp_path / "runs.log")
    with open(log_path, "w") as f:
      f.write("not a timestamp\n")
      f.write("also not valid\n")
    prune_logs(log_path)
    with open(log_path) as f:
      lines = f.readlines()
    assert len(lines) == 2

  def test_custom_keep_days(self, tmp_path: pytest.TempPathFactory) -> None:
    log_path = str(tmp_path / "runs.log")
    now = datetime.now(UTC)
    recent = (now - timedelta(days=5)).isoformat(timespec="seconds")
    borderline = (now - timedelta(days=15)).isoformat(timespec="seconds")
    with open(log_path, "w") as f:
      f.write(f"{recent} | scrobbled=1 | new_tracks=1\n")
      f.write(f"{borderline} | scrobbled=2 | new_tracks=2\n")
    prune_logs(log_path, keep_days=10)
    with open(log_path) as f:
      lines = f.readlines()
    assert len(lines) == 1
    assert "scrobbled=1" in lines[0]


class TestWriteLog:
  def test_appends_to_file(self, tmp_path: pytest.TempPathFactory) -> None:
    log_path = str(tmp_path / "runs.log")
    write_log(log_path, 5, 3)
    write_log(log_path, 2, 1)
    with open(log_path) as f:
      lines = f.readlines()
    assert len(lines) == 2
    assert "scrobbled=5" in lines[0]
    assert "new_tracks=1" in lines[1]

  def test_format_contains_timestamp(self, tmp_path: pytest.TempPathFactory) -> None:
    log_path = str(tmp_path / "runs.log")
    write_log(log_path, 1, 1)
    with open(log_path) as f:
      content = f.read()
    assert "|" in content
    assert "scrobbled=" in content
    assert "new_tracks=" in content


class TestWriteSummary:
  def test_no_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    tracks = [
      YouTubeMusicTrack(
        video_id="v1",
        title="Song",
        artists=["A"],
        duration="3:00",
        album="Alb",
        like_status="INDIFFERENT",
      )
    ]
    write_summary(tracks)  # should not raise

  def test_writes_table(self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    summary_file = str(tmp_path / "summary.md")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", summary_file)
    tracks = [
      YouTubeMusicTrack(
        video_id="v1",
        title="My Song",
        artists=["Artist A"],
        duration="3:30",
        album="Album",
        like_status="INDIFFERENT",
        thumbnail="https://example.com/t.jpg",
      ),
      YouTubeMusicTrack(
        video_id="v2",
        title="No Album",
        artists=["Artist B"],
        duration=None,
        album=None,
        like_status="INDIFFERENT",
      ),
    ]
    write_summary(tracks)
    with open(summary_file) as f:
      content = f.read()
    assert "| 1 |" in content
    assert "Artist A" in content
    assert "My Song" in content
    assert "Album" in content
    assert "| 2 |" in content
    assert "N/A" in content  # no album, no duration

  def test_empty_tracks(self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    summary_file = str(tmp_path / "summary.md")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", summary_file)
    write_summary([])
    with open(summary_file) as f:
      content = f.read()
    assert "No new tracks scrobbled" in content
