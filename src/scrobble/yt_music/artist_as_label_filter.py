from scrobble.yt_music.artist_filter import ArtistFilter


class ArtistAsLabelFilter(ArtistFilter):
  def __init__(self) -> None:
    self.excluded_artists: list[str] = [
      # This label is marked as an artist in YouTube Music:
      # https://music.youtube.com/channel/UCmJaMS37yHTNgGHIabLeeRg
      # and all its releases are shown as InVogue Records & <Artist>.
      # We need to filter out InVogue Records and leave <Artist> only.
      "InVogue Records",
    ]

  def filter(self, artist: str) -> bool:
    allow = True
    for excluded_artist in self.excluded_artists:
      if artist.casefold() == excluded_artist.casefold():
        allow = False
        break
    return allow
