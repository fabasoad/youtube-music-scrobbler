from unittest.mock import MagicMock, patch

from scrobble.yt_music.youtube_music_client import YouTubeMusicClient


def _make_ytm_item(
    video_id: str = "vid1",
    title: str = "Song",
    artists: list[dict] | None = None,
    album: dict | None = None,
    duration: str = "3:00",
    duration_seconds: int = 180,
    like_status: str = "INDIFFERENT",
    thumbnails: list[dict] | None = None,
) -> dict:
    if artists is None:
        artists = [{"name": "Artist"}]
    return {
        "videoId": video_id,
        "title": title,
        "artists": artists,
        "album": album,
        "duration": duration,
        "duration_seconds": duration_seconds,
        "likeStatus": like_status,
        "thumbnails": thumbnails or [],
    }


class TestFetchHistory:
    def test_basic_fetch(self) -> None:
        items = [_make_ytm_item()]
        with patch("scrobble.yt_music.youtube_music_client.YTMusic") as mock_cls:
            mock_cls.return_value.get_history.return_value = items
            client = YouTubeMusicClient()
            result = client.fetch_history()
        assert len(result) == 1
        assert result[0].video_id == "vid1"
        assert result[0].title == "Song"
        assert result[0].artists == ["Artist"]

    def test_filters_out_label_artist(self) -> None:
        items = [
            _make_ytm_item(artists=[
                {"name": "InVogue Records"},
                {"name": "Real Artist"},
            ])
        ]
        with patch("scrobble.yt_music.youtube_music_client.YTMusic") as mock_cls:
            mock_cls.return_value.get_history.return_value = items
            client = YouTubeMusicClient()
            result = client.fetch_history()
        assert result[0].artists == ["Real Artist"]

    def test_all_artists_filtered_uses_original(self) -> None:
        items = [
            _make_ytm_item(artists=[{"name": "InVogue Records"}])
        ]
        with patch("scrobble.yt_music.youtube_music_client.YTMusic") as mock_cls:
            mock_cls.return_value.get_history.return_value = items
            client = YouTubeMusicClient()
            result = client.fetch_history()
        assert result[0].artists == ["InVogue Records"]

    def test_no_artists_uses_placeholder(self) -> None:
        items = [_make_ytm_item(artists=[])]
        with patch("scrobble.yt_music.youtube_music_client.YTMusic") as mock_cls:
            mock_cls.return_value.get_history.return_value = items
            client = YouTubeMusicClient()
            result = client.fetch_history()
        assert result[0].artists == ["Unknown Artist"]

    def test_none_artists_uses_placeholder(self) -> None:
        items = [_make_ytm_item()]
        items[0]["artists"] = None
        with patch("scrobble.yt_music.youtube_music_client.YTMusic") as mock_cls:
            mock_cls.return_value.get_history.return_value = items
            client = YouTubeMusicClient()
            result = client.fetch_history()
        assert result[0].artists == ["Unknown Artist"]

    def test_thumbnail_selection(self) -> None:
        items = [_make_ytm_item(thumbnails=[
            {"width": 120, "height": 120, "url": "https://example.com/large.jpg"},
            {"width": 60, "height": 60, "url": "https://example.com/small.jpg"},
        ])]
        with patch("scrobble.yt_music.youtube_music_client.YTMusic") as mock_cls:
            mock_cls.return_value.get_history.return_value = items
            client = YouTubeMusicClient()
            result = client.fetch_history()
        assert result[0].thumbnail == "https://example.com/small.jpg"

    def test_no_matching_thumbnail(self) -> None:
        items = [_make_ytm_item(thumbnails=[
            {"width": 120, "height": 120, "url": "https://example.com/large.jpg"},
        ])]
        with patch("scrobble.yt_music.youtube_music_client.YTMusic") as mock_cls:
            mock_cls.return_value.get_history.return_value = items
            client = YouTubeMusicClient()
            result = client.fetch_history()
        assert result[0].thumbnail is None

    def test_missing_video_id(self) -> None:
        items = [_make_ytm_item()]
        items[0].pop("videoId")
        with patch("scrobble.yt_music.youtube_music_client.YTMusic") as mock_cls:
            mock_cls.return_value.get_history.return_value = items
            client = YouTubeMusicClient()
            result = client.fetch_history()
        assert result[0].video_id == ""

    def test_missing_title(self) -> None:
        items = [_make_ytm_item()]
        items[0].pop("title")
        with patch("scrobble.yt_music.youtube_music_client.YTMusic") as mock_cls:
            mock_cls.return_value.get_history.return_value = items
            client = YouTubeMusicClient()
            result = client.fetch_history()
        assert result[0].title == "Unknown Title"

    def test_album_extraction(self) -> None:
        items = [_make_ytm_item(album={"name": "My Album"})]
        with patch("scrobble.yt_music.youtube_music_client.YTMusic") as mock_cls:
            mock_cls.return_value.get_history.return_value = items
            client = YouTubeMusicClient()
            result = client.fetch_history()
        assert result[0].album == "My Album"

    def test_none_album(self) -> None:
        items = [_make_ytm_item(album=None)]
        with patch("scrobble.yt_music.youtube_music_client.YTMusic") as mock_cls:
            mock_cls.return_value.get_history.return_value = items
            client = YouTubeMusicClient()
            result = client.fetch_history()
        assert result[0].album is None

    def test_empty_album_name(self) -> None:
        items = [_make_ytm_item(album={"name": ""})]
        with patch("scrobble.yt_music.youtube_music_client.YTMusic") as mock_cls:
            mock_cls.return_value.get_history.return_value = items
            client = YouTubeMusicClient()
            result = client.fetch_history()
        assert result[0].album is None

    def test_history_limit(self) -> None:
        items = [_make_ytm_item(video_id=f"v{i}") for i in range(60)]
        with patch("scrobble.yt_music.youtube_music_client.YTMusic") as mock_cls:
            mock_cls.return_value.get_history.return_value = items
            client = YouTubeMusicClient()
            result = client.fetch_history()
        assert len(result) == 50  # default limit
