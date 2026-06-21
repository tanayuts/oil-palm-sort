"""Track lifecycle helpers (pure functions, no Qt imports).

Extracted from the original monolithic main.py (Phase 3 of the refactor).
This module is independently testable — it operates on plain dicts and
integers without any PySide6 dependencies.
"""

from __future__ import annotations

import time
from typing import Dict


def cleanup_tracks(
    tracks: Dict[int, Dict],
    pending_tid: int | None,
    ttl_sec: float,
) -> tuple[Dict[int, Dict], int | None, list[int]]:
    """Remove tracks that have exceeded their time-to-live.

    Args:
        tracks: The current tracks dict mapping tid -> track data.
        pending_tid: The track ID currently waiting for operator input.
        ttl_sec: Time-to-live in seconds.

    Returns:
        A tuple of (updated_tracks, updated_pending_tid, expired_tids).
        expired_tids is a list of tid values that were removed.
    """
    now = time.time()
    expired: list[int] = []
    new_pending = pending_tid

    for t in list(tracks.keys()):
        if now - tracks[t]["last"] > ttl_sec:
            if t == pending_tid:
                # Track expired while waiting for operator — clear pending
                new_pending = None
            expired.append(t)

    for t in expired:
        del tracks[t]

    return tracks, new_pending, expired


def finalize_track(
    tracks: Dict[int, Dict],
    tid: int,
    decision: str,
    counts: Dict[str, int],
    loop_start: float,
) -> tuple[Dict[int, Dict], Dict[str, int], float]:
    """Mark a track as done, update counts, and compute latency.

    Args:
        tracks: The current tracks dict.
        tid: The track ID to finalize.
        decision: The decision string ("AUTO", "MANUAL", etc.).
        counts: Mutable counts dict to update.
        loop_start: The time the current processing loop started.

    Returns:
        A tuple of (updated_tracks, updated_counts, latency).
    """
    trk = tracks.get(tid)
    if not trk or trk.get("done"):
        return tracks, counts, 0.0

    trk["done"] = True
    trk["dec"] = decision

    cls = trk.get("cls") or "Unknown"
    conf = float(trk.get("conf") or 0.0)

    # update counts
    if cls not in counts:
        counts[cls] = 0
    counts[cls] += 1

    latency = time.time() - loop_start if loop_start else 0.0

    return tracks, counts, latency


def init_track(
    tracks: Dict[int, Dict],
    tid: int,
) -> Dict[int, Dict]:
    """Initialize a new track entry.

    Args:
        tracks: The current tracks dict.
        tid: The track ID to initialize.

    Returns:
        The updated tracks dict.
    """
    if tid not in tracks:
        tracks[tid] = {
            "seen": 0,
            "cls": None,
            "conf": 0.0,
            "done": False,
            "last": time.time(),
        }
    return tracks
