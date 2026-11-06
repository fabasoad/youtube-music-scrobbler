from unittest.mock import MagicMock, patch

import pytest

from scrobble.types import YouTubeMusicTrack
from scrobble.update_likes import main


def _ytm_track() -> YouTubeMusicTrack:
  return YouTubeMusicTrack(
    video_id="v1",
    title="Song",
    artists=["Artist"],
    duration="3:00",
    album=None,
    like_status="LIKE",
  )


def _patch_client() -> object:
  client = MagicMock()
  client.fetch_history.return_value = [_ytm_track()]
  return patch("scrobble.update_likes.YouTubeMusicClient", return_value=client)


class TestUpdateLikesMain:
  def test_updates_both_services(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LASTFM_API_KEY", "key")
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "token")
    lastfm, listenbrainz = MagicMock(), MagicMock()
    with (
      _patch_client(),
      patch("scrobble.update_likes.LastFmScrobbler", return_value=lastfm),
      patch("scrobble.update_likes.ListenBrainzScrobbler", return_value=listenbrainz),
    ):
      main()
    lastfm.update_like_status.assert_called_once()
    listenbrainz.update_like_status.assert_called_once()

  def test_lastfm_failure_does_not_block_listenbrainz(
    self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
  ) -> None:
    monkeypatch.setenv("LASTFM_API_KEY", "key")
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "token")
    listenbrainz = MagicMock()
    with (
      _patch_client(),
      patch("scrobble.update_likes.LastFmScrobbler", side_effect=RuntimeError("503")),
      patch("scrobble.update_likes.ListenBrainzScrobbler", return_value=listenbrainz),
    ):
      main()  # must not raise SystemExit: one service still worked
    listenbrainz.update_like_status.assert_called_once()
    assert "[Last.fm] Like updates failed" in capsys.readouterr().err

  def test_exits_1_when_all_configured_services_fail(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LASTFM_API_KEY", "key")
    monkeypatch.setenv("LISTENBRAINZ_TOKEN", "token")
    with (
      _patch_client(),
      patch("scrobble.update_likes.LastFmScrobbler", side_effect=RuntimeError("503")),
      patch("scrobble.update_likes.ListenBrainzScrobbler", side_effect=RuntimeError("down")),
      pytest.raises(SystemExit) as exc_info,
    ):
      main()
    assert exc_info.value.code == 1

  def test_exits_1_when_only_service_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LASTFM_API_KEY", "key")
    monkeypatch.delenv("LISTENBRAINZ_TOKEN", raising=False)
    with (
      _patch_client(),
      patch("scrobble.update_likes.LastFmScrobbler", side_effect=RuntimeError("503")),
      pytest.raises(SystemExit) as exc_info,
    ):
      main()
    assert exc_info.value.code == 1

  def test_no_services_configured_exits_0(
    self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
  ) -> None:
    monkeypatch.delenv("LASTFM_API_KEY", raising=False)
    monkeypatch.delenv("LISTENBRAINZ_TOKEN", raising=False)
    with _patch_client():
      main()  # nothing configured is not a failure
    err = capsys.readouterr().err
    assert "[Last.fm] Not configured" in err
    assert "[ListenBrainz] Not configured" in err

  def test_fetch_failure_exits_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LASTFM_API_KEY", "key")
    client = MagicMock()
    client.fetch_history.side_effect = RuntimeError("yt music down")
    with (
      patch("scrobble.update_likes.YouTubeMusicClient", return_value=client),
      pytest.raises(SystemExit) as exc_info,
    ):
      main()
    assert exc_info.value.code == 1

  def test_dunder_main_calls_main(self, monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.util
    import runpy

    monkeypatch.delenv("LASTFM_API_KEY", raising=False)
    monkeypatch.delenv("LISTENBRAINZ_TOKEN", raising=False)
    spec = importlib.util.find_spec("scrobble.update_likes")
    assert spec is not None
    with _patch_client():
      runpy.run_path(spec.origin, run_name="__main__")
