import json

import pytest

from scrobble.auth import main, parse_curl

VALID_CURL: str = (
  "curl 'https://music.youtube.com/youtubei/v1/browse' "
  "-H 'authorization: Bearer ya29.abc123' "
  "-H 'x-goog-authuser: 0' "
  "-b 'CONSENT=YES; SID=abc; HSID=def'"
)


class TestParseCurl:
  def test_returns_all_fields(self) -> None:
    result: dict = parse_curl(VALID_CURL)
    assert result == {
      "cookie": "CONSENT=YES; SID=abc; HSID=def",
      "authorization": "Bearer ya29.abc123",
      "x-goog-authuser": "0",
    }

  def test_missing_cookie_exits(self) -> None:
    curl: str = (
      "curl 'https://music.youtube.com/youtubei/v1/browse' "
      "-H 'authorization: Bearer ya29.abc123' "
      "-H 'x-goog-authuser: 0'"
    )
    with pytest.raises(SystemExit):
      parse_curl(curl)

  def test_missing_authorization_exits(self) -> None:
    curl: str = (
      "curl 'https://music.youtube.com/youtubei/v1/browse' -H 'x-goog-authuser: 0' -b 'CONSENT=YES; SID=abc'"
    )
    with pytest.raises(SystemExit):
      parse_curl(curl)

  def test_missing_authuser_exits(self) -> None:
    curl: str = (
      "curl 'https://music.youtube.com/youtubei/v1/browse' "
      "-H 'authorization: Bearer ya29.abc123' "
      "-b 'CONSENT=YES; SID=abc'"
    )
    with pytest.raises(SystemExit):
      parse_curl(curl)

  def test_missing_multiple_fields_exits(self) -> None:
    with pytest.raises(SystemExit):
      parse_curl("curl 'https://music.youtube.com/youtubei/v1/browse'")

  def test_missing_fields_prints_error(self, capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(SystemExit):
      parse_curl("curl 'https://music.youtube.com/youtubei/v1/browse'")
    out: str = capsys.readouterr().out
    assert "Error: Could not find:" in out

  def test_authuser_value_extracted(self) -> None:
    curl: str = (
      "curl 'https://music.youtube.com/youtubei/v1/browse' "
      "-H 'authorization: Bearer token' "
      "-H 'x-goog-authuser: 2' "
      "-b 'cookie=val'"
    )
    result: dict = parse_curl(curl)
    assert result["x-goog-authuser"] == "2"


class TestMain:
  def test_no_curl_file_exits_zero(
    self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
  ) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
      main()
    assert exc_info.value.code == 0

  def test_no_curl_file_prints_instructions(
    self,
    tmp_path: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
  ) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
      main()
    out: str = capsys.readouterr().out
    assert "curl.txt" in out

  def test_creates_browser_json_when_missing(
    self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
  ) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "curl.txt").write_text(VALID_CURL)

    main()

    data: dict = json.loads((tmp_path / "browser.json").read_text())
    assert data["cookie"] == "CONSENT=YES; SID=abc; HSID=def"
    assert data["authorization"] == "Bearer ya29.abc123"
    assert data["x-goog-authuser"] == "0"

  def test_merges_into_existing_browser_json(
    self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
  ) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "curl.txt").write_text(VALID_CURL)
    (tmp_path / "browser.json").write_text(json.dumps({"existing_key": "existing_value"}))

    main()

    data: dict = json.loads((tmp_path / "browser.json").read_text())
    assert data["existing_key"] == "existing_value"
    assert data["authorization"] == "Bearer ya29.abc123"

  def test_overwrites_stale_auth_in_browser_json(
    self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
  ) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "curl.txt").write_text(VALID_CURL)
    (tmp_path / "browser.json").write_text(json.dumps({"authorization": "Bearer old_token"}))

    main()

    data: dict = json.loads((tmp_path / "browser.json").read_text())
    assert data["authorization"] == "Bearer ya29.abc123"

  def test_prints_success_message(
    self,
    tmp_path: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
  ) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "curl.txt").write_text(VALID_CURL)

    main()

    out: str = capsys.readouterr().out
    assert "browser.json updated successfully" in out
