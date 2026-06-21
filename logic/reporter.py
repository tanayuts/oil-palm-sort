"""Reporting helpers: save_log, make_backup, export_daily_report.

Extracted from the original monolithic main.py (Phase 3 of the refactor).
Most of this module is Qt-free — only the file-dialog calls remain in
main_window.py. The pure logic has been moved here for testability.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import time
from typing import Dict


def write_log_entry(
    csv_path: str,
    tid: int,
    cls: str,
    conf: float,
    status: str,
    latency: float,
) -> None:
    """Write a single log entry to the results CSV file.

    Args:
        csv_path: Path to the results CSV file.
        tid: Track ID.
        cls: Classification label.
        conf: Confidence score.
        status: Decision status (AUTO, MANUAL, REJECT, etc.).
        latency: Elapsed time for this detection.
    """
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            time.strftime("%Y-%m-%d %H:%M:%S"),
            tid,
            cls,
            f"{conf:.3f}",
            status,
            f"{latency:.4f}",
        ])


def make_backup(
    log_dir: str,
    csv_path: str,
    counts: Dict[str, int],
    speed_level: int,
    proc_skip: int,
    proc_imgsz: int,
    backup_every: int,
    log_total: int,
) -> tuple[str, str] | None:
    """Create backup copies of the CSV and a JSON stats snapshot.

    Args:
        log_dir: Directory to write backups into.
        csv_path: Path to the current results CSV.
        counts: Current fruit counts dict.
        speed_level: Current speed slider level.
        proc_skip: Current frame skip value.
        proc_imgsz: Current YOLO image size.
        backup_every: Backup frequency (e.g. 100).
        log_total: Total number of log entries written so far.

    Returns:
        A tuple of (backup_csv_path, backup_json_path) or None if no backup needed.
    """
    # log_total is incremented after save_log(), so the first backup
    # fires at exactly 100, then 200, 300, etc.
    if log_total <= 0 or (log_total % backup_every != 0):
        return None

    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_csv = os.path.join(log_dir, f"results_backup_{ts}.csv")
    backup_json = os.path.join(log_dir, f"stats_{ts}.json")

    try:
        shutil.copy2(csv_path, backup_csv)
    except Exception:
        pass
    try:
        payload = {
            "timestamp": ts,
            "counts": counts,
            "total": sum(counts.values()),
            "speed_level": speed_level,
            "proc_skip": proc_skip,
            "proc_imgsz": proc_imgsz,
        }
        with open(backup_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return backup_csv, backup_json


def build_daily_report(
    counts: Dict[str, int],
    session_started_at: float,
    day: str | None = None,
) -> tuple[str, list[str]]:
    """Build a daily report string and a CSV summary row list.

    Args:
        counts: Current fruit counts dict.
        session_started_at: Timestamp when the session started.
        day: Optional day string (YYYY-MM-DD). Defaults to today.

    Returns:
        A tuple of (report_text, csv_rows).
    """
    if day is None:
        day = time.strftime("%Y-%m-%d")

    total = sum(counts.values())
    dur = int(time.time() - session_started_at)

    lines = [
        f"Oil Palm Sorting - Daily Report ({day})",
        f"Session Duration: {dur // 60:02d}:{dur % 60:02d}",
        f"Total: {total}",
        "",
    ]

    for k, v in counts.items():
        pct = (v / total * 100.0) if total > 0 else 0.0
        lines.append(f"- {k}: {v} ({pct:.1f}%)")

    report_txt = "\n".join(lines)

    csv_rows: list[str] = [
        "date", "class", "count", "percent",
    ]
    for k, v in counts.items():
        pct = (v / total * 100.0) if total > 0 else 0.0
        csv_rows.extend([day, k, str(v), f"{pct:.1f}"])

    return report_txt, csv_rows
