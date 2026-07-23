from ytmusicapi import YTMusic

from scrobble.types import YouTubeMusicTrack
from scrobble.yt_music.artist_as_label_filter import ArtistAsLabelFilter
from scrobble.yt_music.artist_filter import ArtistFilter


class YouTubeMusicClient:
  def __init__(self):
    self.auth_path: str = "browser.json"
    self.history_limit: int = 50
    self.artist_filters: list[ArtistFilter] = [
      ArtistAsLabelFilter(),
    ]

  def fetch_history(self) -> list[YouTubeMusicTrack]:
    yt: YTMusic = YTMusic(self.auth_path)
    history: list[dict] = yt.get_history()[: self.history_limit]
    tracks: list[YouTubeMusicTrack] = []
    for item in history:
      artists: list[dict] = item.get("artists") or []
      album: dict | None = item.get("album")

      filtered_artists: list[str] = []
      for artist in artists:
        for artist_filter in self.artist_filters:
          if artist_filter.filter(artist["name"]):
            filtered_artists.append(artist["name"])

      # If after filtering list is empty, we need to fill it with at least something
      if not filtered_artists:
        # - If we filtered out all the available artists, then let's leave them as is.
        # - If original list of artists is also empty, then we use a placeholder.
        filtered_artists = [artist["name"] for artist in artists] if artists else ["Unknown Artist"]

      thumbnails = item.get("thumbnails") or []
      thumbnail: str | None = None
      for t in thumbnails:
        if t.get("width") == 60 and t.get("height") == 60:
          thumbnail = t.get("url")
          break

      tracks.append(
        YouTubeMusicTrack(
          video_id=item.get("videoId") or "",
          title=item.get("title") or "Unknown Title",
          artists=filtered_artists,
          duration=item.get("duration"),
          duration_seconds=item.get("duration_seconds"),
          album=album.get("name") if album and album.get("name") else None,
          like_status=item.get("likeStatus") or "INDIFFERENT",
          thumbnail=thumbnail,
        )
      )
    return tracks
