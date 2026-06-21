"""Oil Palm Sorting Application — Entry point.

All application logic lives in the ui/main_window module.
This file creates the QApplication, instantiates MainApp, and starts the event loop.
"""

import sys
import os
import logging

from config import LOG_DIR

# Configure logging before creating the app
logger = logging.getLogger("oil_palm_sort")
logger.setLevel(logging.DEBUG)

os.makedirs(LOG_DIR, exist_ok=True)
_fh = logging.FileHandler("logs/app.log", encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

_sh = logging.StreamHandler()
_sh.setLevel(logging.INFO)
_sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

logger.addHandler(_fh)
logger.addHandler(_sh)

from PySide6.QtWidgets import QApplication
from ui.main_window import MainApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainApp()
    w.show()
    sys.exit(app.exec())
