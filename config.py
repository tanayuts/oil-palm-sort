"""Application configuration constants, paths, and resource helpers.

Extracted from the original monolithic main.py (Phase 3 of the refactor).
All magic numbers and strings live here so the rest of the codebase
remains clean and the target config.py split is a straight extraction.
"""

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Application configuration constants."""

    # Paths
    DETECTOR_PATH: str = "detector.pt"
    CLASSIFIER_PATH: str = "classify.pt"
    SAVE_DIR: str = "saved_images"
    ERROR_DIR: str = "saved_images/errors"
    LOG_DIR: str = "logs"
    CSV_PATH: str = "logs/results.csv"

    # Detection parameters
    CAM_INDEX: int = 0
    DET_CONF: float = 0.30
    CONF_GREEN: float = 0.90
    CONF_YELLOW: float = 0.70
    STABILITY_FRAMES: int = 3
    TRACK_TTL_SEC: float = 2.0

    # Session / logging
    BACKUP_EVERY: int = 100

    # Default zone (x1, y1, x2, y2)
    DEFAULT_ZONE: tuple[int, int, int, int] = (100, 100, 500, 400)


CFG = Config()


def resource_path(relative_path: str) -> str:
    """Get absolute path to a resource, supporting PyInstaller bundles."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# Resolve paths that depend on resource_path (PyInstaller compatibility)
DETECTOR_PATH = resource_path(CFG.DETECTOR_PATH)
CLASSIFIER_PATH = resource_path(CFG.CLASSIFIER_PATH)
SAVE_DIR = CFG.SAVE_DIR
ERROR_DIR = CFG.ERROR_DIR
LOG_DIR = CFG.LOG_DIR
CSV_PATH = CFG.CSV_PATH
BACKUP_EVERY = CFG.BACKUP_EVERY
CAM_INDEX = CFG.CAM_INDEX
DET_CONF = CFG.DET_CONF
CONF_GREEN = CFG.CONF_GREEN
CONF_YELLOW = CFG.CONF_YELLOW
STABILITY_FRAMES = CFG.STABILITY_FRAMES
TRACK_TTL_SEC = CFG.TRACK_TTL_SEC
DEFAULT_ZONE = CFG.DEFAULT_ZONE

# Ensure output directories exist
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(ERROR_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
