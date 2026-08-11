import importlib.util
import runpy
from unittest.mock import MagicMock, patch

import pytest

from scrobble.main import build_scrobblers, main, write_summary
from scrobble.scrobblers.lastfm import LastFmScrobbler
from scrobble.scrobblers.listenbrainz import ListenBrainzScrobbler
from scrobble.types import YouTubeMusicTrack

LASTFM_VARS = {
  "LASTFM_API_KEY": "key",  # pragma: allowlist secret
  "LASTFM_SECRET": "secret",  # pragma: allowlist secret
  "LASTFM_USERNAME": "user",
  "LASTFM_PASSWORD": "pass",  # pragma: allowlist secret
}


class TestBuildScrobblers:
  def test_lastfm_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in LASTFM_VARS.items():
      monkeypatch.setenv(k, v)
    monkeypatch.delenv("LISTENBRAINZ_TOKEN", raising=False)
    with patch("scrobble.scrobblers.lastfm.pylast.LastFMNetwork"):
      result = build_scrobblers()
    assert len(result) == 1
    assert isinstance(result[0], LastFmScrobbler)

  def test_listenbrainz_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
    for k in LASTFM_VARS:
      monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "token")
    with patch("scrobble.scrobblers.listenbrainz.liblistenbrainz.ListenBrainz"):
      result = build_scrobblers()
    assert len(result) == 1
    assert isinstance(result[0], ListenBrainzScrobbler)

  def test_both_scrobblers(self, monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in LASTFM_VARS.items():
      monkeypatch.setenv(k, v)
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "token")
    with (
      patch("scrobble.scrobblers.lastfm.pylast.LastFMNetwork"),
      patch("scrobble.scrobblers.listenbrainz.liblistenbrainz.ListenBrainz"),
    ):
      result = build_scrobblers()
    assert len(result) == 2
    assert isinstance(result[0], LastFmScrobbler)
    assert isinstance(result[1], ListenBrainzScrobbler)

  def test_no_credentials_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
    for k in LASTFM_VARS:
      monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("LISTENBRAINZ_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="No scrobblers configured"):
      build_scrobblers()

  def test_partial_lastfm_vars_skips_lastfm(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LASTFM_API_KEY", "key")
    for k in ("LASTFM_SECRET", "LASTFM_USERNAME", "LASTFM_PASSWORD"):
      monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "token")
    with patch("scrobble.scrobblers.listenbrainz.liblistenbrainz.ListenBrainz"):
      result = build_scrobblers()
    assert len(result) == 1
    assert isinstance(result[0], ListenBrainzScrobbler)


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

  def test_short_duration_prefixed(
    self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
  ) -> None:
    summary_file = str(tmp_path / "summary.md")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", summary_file)
    track = YouTubeMusicTrack(
      video_id="v1", title="Song", artists=["A"], duration="3:00", album=None, like_status="INDIFFERENT"
    )
    write_summary([track])
    content = (tmp_path / "summary.md").read_text()
    assert "03:00" in content


class TestBuildScrobblersListenBrainzError:
  def test_listenbrainz_init_error_skips_and_warns(
    self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
  ) -> None:
    for k in ("LASTFM_API_KEY", "LASTFM_SECRET", "LASTFM_USERNAME", "LASTFM_PASSWORD"):
      monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "token")
    with patch(
      "scrobble.main.ListenBrainzScrobbler", side_effect=RuntimeError("bad token")
    ):
      with pytest.raises(RuntimeError, match="No scrobblers configured"):
        build_scrobblers()
    assert "Failed to configure" in capsys.readouterr().err


def _make_db_mock(tracks: list | None = None) -> MagicMock:
  db = MagicMock()
  rows = [(i, t) for i, t in enumerate(tracks or [])]
  db.get_unscrobbled.return_value = rows
  return db


def _make_scrobbler_mock(count: int = 0) -> MagicMock:
  s = MagicMock()
  s.scrobble.return_value = count
  return s


def _ytm_track(video_id: str = "v1") -> YouTubeMusicTrack:
  return YouTubeMusicTrack(
    video_id=video_id, title="Song", artists=["Artist"], duration="3:00", album=None, like_status="INDIFFERENT"
  )


class TestMain:
  def _patch_main(
    self,
    monkeypatch: pytest.MonkeyPatch,
    db: MagicMock,
    scrobblers: list[MagicMock],
    scrobbler_keys: list[str] | None = None,
  ):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    patch_build = patch("scrobble.main.build_scrobblers", return_value=scrobblers)
    patch_db = patch("scrobble.main.PlayDb", return_value=db)
    if scrobbler_keys is not None:
      patch_lastfm = patch(
        "scrobble.main.LastFmScrobbler",
        side_effect=lambda: scrobblers[scrobbler_keys.index("lastfm")]
        if "lastfm" in scrobbler_keys
        else None,
      )
    return patch_build, patch_db

  def test_scrobbles_and_marks(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    track = _ytm_track()
    db = _make_db_mock([track])
    scrobbler = _make_scrobbler_mock(count=1)
    scrobbler.__class__ = LastFmScrobbler
    with (
      patch("scrobble.main.build_scrobblers", return_value=[scrobbler]),
      patch("scrobble.main.PlayDb", return_value=db),
      patch("scrobble.main.isinstance", side_effect=lambda obj, cls: cls == LastFmScrobbler),
      patch("scrobble.main.prepare_tracks", return_value=[MagicMock()]),
    ):
      main()
    scrobbler.scrobble.assert_called_once()
    db.mark_scrobbled.assert_called_once()

  def test_no_unscrobbled_skips_scrobble(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    db = _make_db_mock([])
    scrobbler = _make_scrobbler_mock()
    with (
      patch("scrobble.main.build_scrobblers", return_value=[scrobbler]),
      patch("scrobble.main.PlayDb", return_value=db),
      patch("scrobble.main.isinstance", side_effect=lambda obj, cls: cls == LastFmScrobbler),
    ):
      main()
    scrobbler.scrobble.assert_not_called()

  def test_exception_exits_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    db = MagicMock()
    db.init_schema.side_effect = RuntimeError("db down")
    with (
      patch("scrobble.main.build_scrobblers", return_value=[MagicMock()]),
      patch("scrobble.main.PlayDb", return_value=db),
      pytest.raises(SystemExit) as exc_info,
    ):
      main()
    assert exc_info.value.code == 1

  def test_db_closed_on_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    db = MagicMock()
    db.init_schema.side_effect = RuntimeError("db down")
    with (
      patch("scrobble.main.build_scrobblers", return_value=[MagicMock()]),
      patch("scrobble.main.PlayDb", return_value=db),
      pytest.raises(SystemExit),
    ):
      main()
    db.close.assert_called_once()

  def test_db_closed_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    db = _make_db_mock([])
    scrobbler = _make_scrobbler_mock()
    with (
      patch("scrobble.main.build_scrobblers", return_value=[scrobbler]),
      patch("scrobble.main.PlayDb", return_value=db),
      patch("scrobble.main.isinstance", side_effect=lambda obj, cls: cls == LastFmScrobbler),
    ):
      main()
    db.close.assert_called_once()

  def test_dunder_main_calls_main(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    db = _make_db_mock([])
    spec = importlib.util.find_spec("scrobble.main")
    assert spec is not None
    with (
      patch("scrobble.main.build_scrobblers", return_value=[MagicMock()]),
      patch("scrobble.main.PlayDb", return_value=db),
      patch("scrobble.main.isinstance", side_effect=lambda obj, cls: False),
    ):
      runpy.run_path(spec.origin, run_name="__main__")
