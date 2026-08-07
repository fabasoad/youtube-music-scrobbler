import sys

import pytest
from loguru import logger

from scrobble.types import YouTubeMusicTrack


@pytest.fixture(autouse=True)
def _patch_loguru_stderr(capsys: pytest.CaptureFixture) -> None:
  logger.remove()
  logger.add(sys.stderr)
  yield
  logger.remove()


@pytest.fixture
def sample_track() -> YouTubeMusicTrack:
  return YouTubeMusicTrack(
    video_id="abc123",
    title="Test Song",
    artists=["Test Artist"],
    duration="3:30",
    album="Test Album",
    like_status="INDIFFERENT",
    duration_seconds=210,
    thumbnail="https://example.com/thumb.jpg",
  )


@pytest.fixture
def sample_tracks() -> list[YouTubeMusicTrack]:
  return [
    YouTubeMusicTrack(
      video_id="vid1",
      title="Song One",
      artists=["Artist A"],
      duration="4:00",
      album="Album X",
      like_status="LIKE",
      duration_seconds=240,
      thumbnail=None,
    ),
    YouTubeMusicTrack(
      video_id="vid2",
      title="Song Two",
      artists=["Artist B", "Artist C"],
      duration="3:15",
      album=None,
      like_status="INDIFFERENT",
      duration_seconds=195,
      thumbnail="https://example.com/t2.jpg",
    ),
    YouTubeMusicTrack(
      video_id="vid3",
      title="Song Three",
      artists=[],
      duration=None,
      album="Album Y",
      like_status="DISLIKE",
      duration_seconds=None,
      thumbnail=None,
    ),
  ]


@pytest.fixture
def multi_artist_track() -> YouTubeMusicTrack:
  return YouTubeMusicTrack(
    video_id="multi1",
    title="Collab Song",
    artists=["Artist A", "Artist B", "Artist C"],
    duration="5:00",
    album="Collab Album",
    like_status="INDIFFERENT",
    duration_seconds=300,
    thumbnail=None,
  )
