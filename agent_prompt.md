# Agent Prompt: Debug, Fix, Improve & Refactor — Oil Palm Sorting App

---

## Your Task

You are a senior Python engineer. Your job is to **debug, fix bugs, improve, and then refactor** a PySide6 desktop application for oil-palm fruit sorting using YOLO computer vision models. The entire application currently lives in a **single file: `main.py`** (≈1,006 lines). You must split it into a clean, maintainable multi-module project while also resolving all known issues.

Work in the project directory: `d:\Academic Project\`

---

## Project Overview

| Item | Detail |
|---|---|
| **App name** | Oil Palm Sorting (Production UI) |
| **Stack** | Python, PySide6, OpenCV, Ultralytics YOLO |
| **Purpose** | Real-time camera feed → YOLO object detection (ByteTrack) → YOLO classification → count Unripe / Ripe / Overripe fruits |
| **Modes** | Fully-automatic (high confidence) or semi-manual (operator confirms/rejects) |
| **Deployment** | Windows desktop; packaged with PyInstaller (`sys._MEIPASS`) |
| **Models** | `detector.pt` (object detector with tracking), `classify.pt` (fruit classifier) |
| **Requirements** | `ultralytics==8.4.72`, `opencv-python`, `PySide6`, `lapx` |

---

## Known Bugs & Issues to Fix

Fix **all** of the following before refactoring:

1. **Dead commented-out code (line 244–246):** `self.apply_speed(self.speed_level)` is commented out with an explanation comment that is confusing. Clean this up entirely — `apply_speed()` is already called correctly on line 277 after `setup_ui()`.

2. **Silent bare `except` blocks in `SmartCam`:** `set_source()` (line 146) and `reconnect()` (line 190) use bare `except: pass` which swallows all errors including `KeyboardInterrupt`. Replace with `except Exception:` and optionally log a warning.

3. **`save_log()` always writes latency as `"0"` (line 895):** The CSV column `Latency` is hardcoded to `"0"`. It should record actual latency — pass the real elapsed time from `run_loop()` and write it.

4. **`action_reject()` does not save image screenshot:** Confirmed items (`action_confirm`) trigger `finalize_track()` which calls `save_log()`, but rejected items skip taking an autoscreenshot. This is inconsistent; rejected items should also call `autoscreenshot("rejected")` so operators can review them.

5. **`cleanup_tracks()` O(n) dict mutation during iteration:** `for t in list(self.tracks.keys())` builds a full copy of keys. This is fine for small n, but the TTL check inside never resets `pending_tid` correctly if the pending track is already gone. Verify and fix the edge case where `pending_tid` is set but the track is already cleaned up before the operator responds.

6. **`display_frame()` uses `Qt.IgnoreAspectRatio` (line 982):** This stretches the frame to fill the label, which breaks the zone-coordinate mapping because `finish_drawing_zone()` assumes the frame fills the label exactly. This is intentional per the comment on line 980, but it conflicts with `finish_drawing_zone()` scaling which uses `lbl_cam.width()` vs `video_dims`. Audit this logic and ensure the coordinate mapping is truly correct, or switch to `Qt.KeepAspectRatio` with a proper offset calculation.

7. **`table` keeps only 10 rows but removes row 0 (oldest) in a potentially wrong order (lines 876–878):** The loop `if row > 9: removeRow(0)` is called before `insertRow(row)`. This causes `row` to be decremented but then `insertRow(row)` is called. Trace the logic and ensure the newest entry always appears at the bottom.

8. **No `__all__` or type hints anywhere:** All public functions lack type annotations. Add them where it adds clarity.

9. **`BACKUP_EVERY = 100` can trigger a backup on log_total == 0 check (line 836):** The guard is `if self.log_total > 0 and (self.log_total % BACKUP_EVERY == 0)`. This is correct but `log_total` is only incremented *after* `save_log()` is called, meaning a backup at exactly 100, 200, etc. is fine. Confirm this is bug-free and add a comment explaining the logic.

10. **Crash on model load failure is silently ignored (lines 257–262):** If models fail to load, the app continues in "UI Test Mode" but the user gets no visual indicator in the UI (only a console print). Add a visible `QMessageBox.warning` or a permanent status-bar warning so operators know the models are not loaded.

---

## Improvements to Make

After fixing bugs, apply these improvements:

1. **Add `logging` module support:** Replace all bare `print()` calls with Python's standard `logging` module. Configure a `FileHandler` writing to `logs/app.log` and a `StreamHandler` for console. Use appropriate log levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`).

2. **Extract all magic numbers and strings to a config dataclass or named constants:** Move `DET_CONF`, `CONF_GREEN`, `CONF_YELLOW`, `STABILITY_FRAMES`, `TRACK_TTL_SEC`, `BACKUP_EVERY`, `CAM_INDEX`, `DEFAULT_ZONE`, `SAVE_DIR`, `LOG_DIR` into a `config.py` module using a `dataclass` or `TypedDict` for grouping.

3. **Tone map should not import `winsound` every call (lines 506–516):** Import `winsound` once at the top of the module (guarded by `sys.platform == "win32"`) to avoid repeated import overhead in a hot path.

4. **Add graceful shutdown:** `closeEvent` only calls `cam.release()`. Add: stop the QTimer, flush any open CSV file handles, and log a shutdown message.

5. **Zone persistence:** Save and restore the user-drawn zone to/from a small JSON config file (e.g., `logs/zone.json`) so the zone is remembered between sessions.

6. **Add a "Reset Session" button** that zeroes `counts`, resets `session_started_at`, and resets `log_total`. Currently the only way to reset is to restart the app.

---

## Refactoring: Target File Structure

Split `main.py` into the following modules. Keep all imports clean and avoid circular imports.

```
d:\Academic Project\
├── main.py                  # Entry point only: creates QApplication, shows MainApp, sys.exit
├── config.py                # All constants, paths, and the AppConfig dataclass
├── styles.py                # STYLESHEET string and any style-helper functions
├── camera.py                # SmartCam class
├── widgets/
│   ├── __init__.py
│   └── drawable_label.py    # DrawableLabel(QLabel) custom widget
├── ui/
│   ├── __init__.py
│   └── main_window.py       # MainApp(QWidget) — the main window class
├── logic/
│   ├── __init__.py
│   ├── tracker.py           # Track lifecycle helpers: init_track, cleanup_tracks, finalize_track logic (pure functions or a TrackManager class)
│   └── reporter.py          # save_log, make_backup, export_daily_report logic
└── requirements.txt         # unchanged
```

**Rules for refactoring:**
- `main.py` must contain **only** the `if __name__ == "__main__":` block (≤10 lines).
- `MainApp` in `ui/main_window.py` should import from `config`, `styles`, `camera`, `widgets`, and `logic` — not define business logic itself.
- `logic/tracker.py` should be independently testable (no Qt imports).
- `logic/reporter.py` should be independently testable (no Qt imports, except for the `QFileDialog` call which can stay in `main_window.py`).
- All files must have a module-level docstring.
- `resource_path()` utility belongs in `config.py`.

---

## Constraints & Rules

- **Do NOT change the UI layout or visual appearance.** Pixel-for-pixel identical UI output is required.
- **Do NOT change the YOLO inference logic** unless it is part of a bug fix listed above.
- **Preserve all existing comments** (translate Thai-language comments to English equivalents if you wish, but do not delete them).
- **The app must still be PyInstaller-compatible** — `resource_path()` must remain functional.
- **All changes must be backward-compatible** with `requirements.txt` — do not add new dependencies.
- After refactoring, run a quick import check: `python -c "from ui.main_window import MainApp"` — it must succeed without errors.

---

## Deliverables

1. All new/modified files written to disk in `d:\Academic Project\`.
2. A brief `REFACTOR_NOTES.md` in the project root documenting:
   - Each bug found and the fix applied.
   - The new module structure with a one-line description of each file.
   - Any design decisions made.
3. The original `main.py` renamed to `main_original_backup.py` (do not delete it).



# Oil Palm Sorting App — Phased Execution Plan

This plan sequences the work in `agent_prompt.md` so bugs are fixed before code is
moved around. Each phase leaves the app in a working, testable state, rather than
mixing debugging and refactoring in the same step.

---

## Phase 0: Setup & Baseline

- Copy `main.py` to `main_original_backup.py` to preserve the original.
- Read the entire file once, fully, before touching anything.
- Manually run the app (or at minimum confirm it imports/launches) to establish a
  baseline of current behavior. "Pixel-for-pixel identical UI" is a hard
  constraint, so you need something to compare against later.
- Note current line numbers for each bug, since the prompt's line numbers may
  drift as edits are made.

---

## Phase 1: Bug Fixes (in `main.py`, still single-file)

Fix all 10 known bugs in place, one at a time, re-running the app after each fix
to catch regressions early.

| # | Bug | Fix |
|---|---|---|
| 1 | Dead commented-out code (line 244–246) | Remove the dead `self.apply_speed(self.speed_level)` line and its confusing comment |
| 2 | Bare `except: pass` in `SmartCam.set_source()` / `reconnect()` | Replace with `except Exception:` and log a warning |
| 3 | `save_log()` always writes latency as `"0"` | Pass real elapsed time from `run_loop()` and write actual value |
| 4 | `action_reject()` doesn't save a screenshot | Call `autoscreenshot("rejected")` for consistency with `action_confirm()` |
| 5 | `pending_tid` not reset if track is cleaned up before operator responds | Trace and fix the race condition in `cleanup_tracks()` — needs careful tracing |
| 6 | `Qt.IgnoreAspectRatio` conflicts with zone-coordinate mapping | Audit `finish_drawing_zone()` scaling logic; fix mapping or switch to `Qt.KeepAspectRatio` with offset calc — also tricky, test manually |
| 7 | Table row insertion order wrong (lines 876–878) | Trace `removeRow(0)` vs `insertRow(row)` ordering so newest entry lands at the bottom |
| 8 | No type hints anywhere | Add type hints where it adds clarity (low risk, do last in this phase) |
| 9 | `BACKUP_EVERY` guard at `log_total == 0` | Verify logic is correct; add explanatory comment only, no functional change |
| 10 | Silent failure on model load | Add visible `QMessageBox.warning` or permanent status-bar warning |

Doing this before refactoring keeps each fix a small, reviewable diff against the
original file, without debugging logic and import paths at the same time.

---

## Phase 2: Improvements (still single-file)

Layer the six improvements on top of the bug-fixed `main.py`:

1. Replace `print()` calls with the `logging` module (`FileHandler` → `logs/app.log`, `StreamHandler` → console; appropriate `DEBUG`/`INFO`/`WARNING`/`ERROR` levels).
2. Extract magic numbers/strings into a constants block or dict (a dry run for the real `config.py` split in Phase 3).
3. Hoist the `winsound` import to module level, guarded by `sys.platform == "win32"`.
4. Add graceful shutdown: stop the QTimer, flush open CSV file handles, log a shutdown message.
5. Add zone persistence: save/restore the drawn zone to `logs/zone.json`.
6. Add a "Reset Session" button that zeroes `counts`, resets `session_started_at`, and resets `log_total`.

Doing improvements before the file split avoids chasing new bugs across module
boundaries later.

---

## Phase 3: Refactor — Extract Leaf Modules First

Split out modules with the fewest dependencies first, so each step is
independently verifiable:

1. `config.py` — constants, `AppConfig`, `resource_path()`
2. `styles.py` — `STYLESHEET`
3. `logic/tracker.py` — pure functions, no Qt, easiest to unit-test in isolation
4. `logic/reporter.py` — same, mostly Qt-free
5. `camera.py` — `SmartCam`
6. `widgets/drawable_label.py` — `DrawableLabel`

After each extraction, update imports in the remaining monolith and confirm the
app still launches before moving to the next module.

---

## Phase 4: Refactor — Assemble `ui/main_window.py` and `main.py`

- Move `MainApp` into `ui/main_window.py`, wiring in imports from the
  now-extracted modules.
- Trim `main.py` down to the `if __name__ == "__main__":` block (≤10 lines).
- This is the highest-risk step for circular imports — do it last, once
  everything it depends on already exists independently.

---

## Phase 5: Verification

- Run the required import check: `python -c "from ui.main_window import MainApp"`.
- Launch the full app and manually compare against the Phase 0 baseline.
- Re-verify bugs 5 and 6 specifically still hold after the module split — moving
  tracker/zone logic across files is exactly where subtle behavior changes sneak
  in.

---

## Phase 6: Documentation

Write `REFACTOR_NOTES.md` last, once the actual fixes and structure are final:

- Each bug found and the fix applied.
- The new module structure with a one-line description of each file.
- Any design decisions made (e.g., dataclass vs. TypedDict for config, how
  circular imports were avoided).