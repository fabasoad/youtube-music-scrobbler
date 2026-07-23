import json
import os
import time

from dataclasses import asdict

from scrobble.types import YouTubeMusicTrack


class SnapshotManager:
  def __init__(self) -> None:
    self.snapshot_path: str = "last_snapshot.json"

  def _load_snapshot(self) -> list[YouTubeMusicTrack]:
    if not os.path.exists(self.snapshot_path):
      return []
    with open(self.snapshot_path) as f:
      data: list[dict] = json.load(f)
      return [YouTubeMusicTrack(**item) for item in data]

  @staticmethod
  def _diff_tracks(current: list[YouTubeMusicTrack], snapshot: list[YouTubeMusicTrack], min_seq: int = 3) -> list[YouTubeMusicTrack]:
    if not snapshot:
      return []

    snap_ids: list[str] = [t.video_id for t in snapshot]
    curr_ids: list[str] = [t.video_id for t in current]

    join: int = len(current)
    for i in range(len(current) - min_seq + 1):
      if curr_ids[i : i + min_seq] == snap_ids[:min_seq]:
        join = i
        break

    return list(reversed(current[:join]))  # oldest first

  def get_diff_from_snapshot(self, current: list[YouTubeMusicTrack]) -> list[YouTubeMusicTrack]:
    snapshot: list[YouTubeMusicTrack] = self._load_snapshot()
    new_tracks: list[YouTubeMusicTrack] = SnapshotManager._diff_tracks(current, snapshot)
    if new_tracks:
      return SnapshotManager._assign_timestamps(new_tracks)
    return []

  def save_snapshot(self, tracks: list[YouTubeMusicTrack]) -> None:
    with open(self.snapshot_path, "w") as f:
      json.dump([asdict(track) for track in tracks], f, indent=2)

