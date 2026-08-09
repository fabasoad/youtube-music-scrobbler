"""
One-time migration: seeds last_snapshot.json into the plays table,
marking all tracks as already scrobbled so they are not re-scrobbled.

Run once:
    uv run python migrate.py

Then delete this file and last_snapshot.json from the repo.
"""

import json
import os
import sys
from datetime import UTC, datetime

import psycopg

SNAPSHOT_PATH = "last_snapshot.json"


def main() -> None:
  url = os.environ.get("NEON_DATABASE_URL")
  if not url:
    print("ERROR: NEON_DATABASE_URL is not set.", file=sys.stderr)
    sys.exit(1)

  if not os.path.exists(SNAPSHOT_PATH):
    print(f"ERROR: {SNAPSHOT_PATH} not found.", file=sys.stderr)
    sys.exit(1)

  with open(SNAPSHOT_PATH) as f:
    tracks: list[dict] = json.load(f)

  now: datetime = datetime.now(UTC)

  with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
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
      cur.execute("CREATE INDEX IF NOT EXISTS plays_video_id_idx ON plays (video_id)")
      cur.execute("CREATE INDEX IF NOT EXISTS plays_fetched_at_idx ON plays (fetched_at DESC)")
      cur.execute("CREATE INDEX IF NOT EXISTS play_artists_artist_name_idx ON play_artists (artist_name)")

      for t in tracks:
        cur.execute(
          """
          INSERT INTO plays
            (video_id, title, duration, album, duration_seconds, thumbnail,
             fetched_at, lastfm_scrobbled_at, listenbrainz_scrobbled_at)
          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
          RETURNING id
          """,
          (
            t.get("video_id", ""),
            t.get("title", "Unknown Title"),
            t.get("duration"),
            t.get("album"),
            t.get("duration_seconds"),
            t.get("thumbnail"),
            now,
            now,
            now,
          ),
        )
        play_id: int = cur.fetchone()[0]
        artists: list[str] = t.get("artists", [])
        if artists:
          cur.executemany(
            "INSERT INTO play_artists (play_id, artist_name, position) VALUES (%s, %s, %s)",
            [(play_id, artist, pos) for pos, artist in enumerate(artists)],
          )

    conn.commit()

  print(f"Migrated {len(tracks)} track(s) from {SNAPSHOT_PATH}.")
  print("You can now delete migrate.py and last_snapshot.json from the repo.")


if __name__ == "__main__":
  main()
