from scrobble.yt_music.artist_as_label_filter import ArtistAsLabelFilter


class TestArtistAsLabelFilter:
    def test_allows_normal_artist(self) -> None:
        f = ArtistAsLabelFilter()
        assert f.filter("Radiohead") is True

    def test_filters_label(self) -> None:
        f = ArtistAsLabelFilter()
        assert f.filter("InVogue Records") is False

    def test_case_insensitive(self) -> None:
        f = ArtistAsLabelFilter()
        assert f.filter("invogue records") is False
        assert f.filter("INVOGUE RECORDS") is False
        assert f.filter("inVogue records") is False

    def test_partial_match_not_filtered(self) -> None:
        f = ArtistAsLabelFilter()
        assert f.filter("InVogue") is True
        assert f.filter("Records") is True

    def test_empty_string(self) -> None:
        f = ArtistAsLabelFilter()
        assert f.filter("") is True
