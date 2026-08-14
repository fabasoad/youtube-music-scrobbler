from scrobble.yt_music.artist_filter import ArtistFilter


class ArtistAsLabelFilter(ArtistFilter):
  """Filters out music labels that YouTube Music incorrectly marks as artists."""

  def __init__(self) -> None:
    self.excluded_artists: list[str] = [
      # This label is marked as an artist in YouTube Music:
      # https://music.youtube.com/channel/UCmJaMS37yHTNgGHIabLeeRg
      # and all its releases are shown as InVogue Records & <Artist>.
      # We need to filter out InVogue Records and leave <Artist> only.
      "InVogue Records",
      # Same here: https://music.youtube.com/channel/UCaR2hMhiQHeiBtLDCcdwwUA
      "Thriller Records",
    ]
    self._excluded_lower: set[str] = {a.casefold() for a in self.excluded_artists}

  def filter(self, artist: str) -> bool:
    return artist.casefold() not in self._excluded_lower
