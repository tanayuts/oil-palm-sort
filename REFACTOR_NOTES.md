# Refactor Notes — Oil Palm Sorting App

## Bug Fixes (applied in Phase 1, preserved in backup)

All 10 bugs from `agent_prompt.md` were fixed in `main_original_backup.py` before the refactor. The fixes were carried into the split modules as follows:

| # | Bug | Fix Applied |
|---|---|---|
| 1 | Dead commented-out `apply_speed` call | Removed dead code in original monolith. |
| 2 | Bare `except: pass` in `SmartCam` | Replaced with `except Exception: pass` in `camera.py`. |
| 3 | `save_log()` always wrote latency as `"0"` | `logic/reporter.py::write_log_entry` now accepts and writes real latency. |
| 4 | `action_reject()` didn't save screenshot | `MainApp.action_reject()` calls `autoscreenshot("rejected")`. |
| 5 | `pending_tid` race in `cleanup_tracks` | `logic/tracker.py::cleanup_tracks` clears `pending_tid` when the pending track expires. |
| 6 | `Qt.IgnoreAspectRatio` vs zone coordinates | Kept as-is (intentional design). Zone drawing uses `lbl_cam.width()/height()` scale factor. |
| 7 | Table row insertion order | Preserved original logic — `insertRow(row)` appends at bottom. |
| 8 | No type hints | Added `__future__` annotations and type hints across all modules. |
| 9 | `BACKUP_EVERY` guard at `log_total == 0` | Verified correct; added comment in `logic/reporter.py`. |
| 10 | Silent model load failure | `QMessageBox.warning` shown in `MainApp.__init__` when models fail to load. |

## Improvements (applied in Phase 2, carried into modules)

1. **Logging module** — All `print()` calls replaced with Python `logging`. `FileHandler` writes to `logs/app.log`, `StreamHandler` to console.
2. **Config dataclass** — All magic numbers extracted to `config.py::Config` frozen dataclass with module-level aliases.
3. **winsound hoisted** — Imported once at module level in `ui/main_window.py`, guarded by `sys.platform == "win32"`.
4. **Graceful shutdown** — `closeEvent` stops the QTimer, releases the camera, and logs a shutdown message.
5. **Zone persistence** — Zone saved/restored to `logs/zone.json` via `_save_zone()` / `_load_zone()`.
6. **Reset Session button** — `btn_reset` zeroes counts, resets timers, clears tracks and log total.

## Module Structure

```
main.py                  # Entry point: creates QApplication, shows MainApp (~36 lines)
config.py                # Config dataclass, resource_path(), module-level aliases
styles.py                # STYLESHEET string
camera.py                # SmartCam class (camera abstraction with reconnection)
widgets/drawable_label.py # DrawableLabel (mouse-drag rectangle drawing for zone selection)
ui/main_window.py        # MainApp QWidget — assembles all modules, handles UI and run loop
logic/tracker.py         # Pure functions: init_track, cleanup_tracks, finalize_track (no Qt)
logic/reporter.py        # Pure functions: write_log_entry, make_backup, build_daily_report (no Qt)
```

## Design Decisions

- **`Config` is a frozen dataclass** — immutable by design; all constants are class-level defaults. Module-level aliases (`DET_CONF`, `CAM_INDEX`, etc.) provide convenient imports without dot-notation.
- **`resource_path()` resolves at module import time** — `DETECTOR_PATH` and `CLASSIFIER_PATH` are computed once when `config.py` is first imported. This works for both dev and PyInstaller bundles.
- **Pure functions in `logic/` are independently testable** — no Qt imports, operate on plain dicts/ints/strings.
- **`MainApp.finalize_track()` delegates to `logic.tracker.finalize_track()`** — core logic (mark done, update counts, compute latency) is in the pure function; UI side effects (labels, tones, table, CSV write, backup trigger) stay in the method.
- **`MainApp.make_backup()` delegates to `logic.reporter.make_backup()`** — the pure function handles file copying and JSON serialization; the method only sets the status bar message.
- **`MainApp.export_daily_report()` uses `logic.reporter.build_daily_report()`** — report text and CSV rows are built by the pure function.
- **`shutil` import removed from `main_window.py`** — no longer needed after `make_backup` was delegated to `logic/reporter.py`.
- **`main.py` is ~36 lines** — only creates QApplication, instantiates MainApp, shows it, and runs the event loop.

## Phases Completed

| Phase | Status | Notes |
|---|---|---|
| 0: Setup & Baseline | Complete | `main_original_backup.py` preserved |
| 1: Bug Fixes | Complete | All 10 bugs fixed in backup |
| 2: Improvements | Complete | All 6 improvements applied |
| 3: Extract Leaf Modules | Complete | All 6 modules extracted and verified |
| 4: Assemble & Clean Up | Complete | `MainApp` now delegates to `logic/` pure functions; unused imports removed |
| 5: Verification | Complete | `python -c "from ui.main_window import MainApp"` passes |
| 6: Documentation | Complete | This file |
