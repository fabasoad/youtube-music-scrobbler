import os

import psycopg
from loguru import logger
from psycopg import sql

from scrobble.types import YouTubeMusicTrack

_VALID_SCROBBLERS: frozenset[str] = frozenset({"lastfm", "listenbrainz"})


class PlayDb:
  def __init__(self) -> None:
    self.conn: psycopg.Connection = psycopg.connect(os.environ["NEON_DATABASE_URL"])

  def init_schema(self) -> None:
    with self.conn.cursor() as cur:
      cur.execute("""
        CREATE TABLE IF NOT EXISTS plays (
          id                        BIGSERIAL PRIMARY KEY,
          video_id                  TEXT NOT NULL,
          title                     TEXT NOT NULL,
          duration                  TEXT,
          album                     TEXT,
          duration_seconds          INTEGER,
          thumbnail                 TEXT,
          fetched_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          lastfm_scrobbled_at       TIMESTAMPTZ,
          listenbrainz_scrobbled_at TIMESTAMPTZ
        )
      """)
      cur.execute("""
        CREATE TABLE IF NOT EXISTS play_artists (
          play_id     BIGINT NOT NULL REFERENCES plays (id) ON DELETE CASCADE,
          artist_name TEXT NOT NULL,
          position    SMALLINT NOT NULL,
          PRIMARY KEY (play_id, position)
        )
      """)
      cur.execute("""
        CREATE TABLE IF NOT EXISTS runs (
          id         BIGSERIAL PRIMARY KEY,
          ran_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          scrobbled  INTEGER NOT NULL,
          new_tracks INTEGER NOT NULL
        )
      """)
      cur.execute("CREATE INDEX IF NOT EXISTS plays_video_id_idx ON plays (video_id)")
      cur.execute("CREATE INDEX IF NOT EXISTS plays_fetched_at_idx ON plays (fetched_at DESC)")
      cur.execute("CREATE INDEX IF NOT EXISTS play_artists_artist_name_idx ON play_artists (artist_name)")
      cur.execute("CREATE INDEX IF NOT EXISTS runs_ran_at_idx ON runs (ran_at DESC)")
    self.conn.commit()
    logger.debug("DB schema initialized.")

  def get_recent_video_ids(self, limit: int = 50) -> list[str]:
    with self.conn.cursor() as cur:
      cur.execute("SELECT video_id FROM plays ORDER BY id DESC LIMIT %s", [limit])
      return [row[0] for row in cur.fetchall()]

  def insert_plays(self, tracks: list[YouTubeMusicTrack]) -> int:
    if not tracks:
      return 0
    with self.conn.cursor() as cur:
      for track in tracks:
        cur.execute(
          """
          INSERT INTO plays (video_id, title, duration, album, duration_seconds, thumbnail)
          VALUES (%s, %s, %s, %s, %s, %s)
          RETURNING id
          """,
          (track.video_id, track.title, track.duration, track.album, track.duration_seconds, track.thumbnail),
        )
        play_id: int = cur.fetchone()[0]
        if track.artists:
          cur.executemany(
            "INSERT INTO play_artists (play_id, artist_name, position) VALUES (%s, %s, %s)",
            [(play_id, artist, pos) for pos, artist in enumerate(track.artists)],
          )
    self.conn.commit()
    logger.info("Inserted {} new play(s) into DB.", len(tracks))
    return len(tracks)

  def get_unscrobbled(self, scrobbler: str) -> list[tuple[int, YouTubeMusicTrack]]:
    if scrobbler not in _VALID_SCROBBLERS:
      raise ValueError(f"Unknown scrobbler: {scrobbler!r}")
    query = sql.SQL(
      """
      SELECT
        p.id, p.video_id, p.title, p.duration, p.album, p.duration_seconds, p.thumbnail,
        COALESCE(
          ARRAY_AGG(pa.artist_name ORDER BY pa.position) FILTER (WHERE pa.artist_name IS NOT NULL),
          ARRAY[]::TEXT[]
        ) AS artists
      FROM plays p
      LEFT JOIN play_artists pa ON pa.play_id = p.id
      WHERE p.{} IS NULL
      GROUP BY p.id
      ORDER BY p.id ASC
"""
    ).format(sql.Identifier(f"{scrobbler}_scrobbled_at"))
    with self.conn.cursor() as cur:
      cur.execute(query)
      rows = cur.fetchall()
    return [
      (
        row[0],
        YouTubeMusicTrack(
          video_id=row[1],
          title=row[2],
          duration=row[3],
          album=row[4],
          duration_seconds=row[5],
          thumbnail=row[6],
          artists=list(row[7]),
        ),
      )
      for row in rows
    ]

  def mark_scrobbled(self, play_ids: list[int], scrobbler: str) -> None:
    if not play_ids:
      return
    if scrobbler not in _VALID_SCROBBLERS:
      raise ValueError(f"Unknown scrobbler: {scrobbler!r}")
    query = sql.SQL("UPDATE plays SET {} = NOW() WHERE id = ANY(%s)").format(
      sql.Identifier(f"{scrobbler}_scrobbled_at")
    )
    with self.conn.cursor() as cur:
      cur.execute(query, [play_ids])
    self.conn.commit()
    logger.info("Marked {} play(s) as scrobbled for {}.", len(play_ids), scrobbler)

  def insert_run(self, scrobbled: int, new_tracks: int) -> None:
    with self.conn.cursor() as cur:
      cur.execute(
        "INSERT INTO runs (scrobbled, new_tracks) VALUES (%s, %s)",
        (scrobbled, new_tracks),
      )
    self.conn.commit()
    logger.debug("Run recorded: scrobbled={}, new_tracks={}.", scrobbled, new_tracks)

  def close(self) -> None:
    self.conn.close()
