"""Application stylesheet (QSS).

Extracted from the original monolithic main.py (Phase 3 of the refactor).
The STYLESHEET string is applied to the root QWidget in MainApp.__init__.
"""

STYLESHEET = """
QWidget { background-color: #1e1e24; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
QFrame#Card { background-color: #2b2b36; border-radius: 14px; border: 1px solid #3a3a45; }
QLabel#CamDisplay { background-color: #000; border: 2px solid #444; border-radius: 10px; }
QLabel#Title { color: #a0a0ff; font-size: 16px; font-weight: bold; }
QLabel#ResultHuge { color: #fff; font-size: 44px; font-weight: 900; padding: 8px; }
QPushButton { background-color: #3e3e4a; color: white; border-radius: 10px; padding: 12px; font-weight: 900; border: none; }
QPushButton:hover { background-color: #4e4e5b; }
QPushButton#BtnConfirm { background-color: #2e7d32; }
QPushButton#BtnConfirm:hover { background-color: #388e3c; }
QPushButton#BtnReject { background-color: #c62828; }
QPushButton#BtnReject:hover { background-color: #d32f2f; }
QPushButton#BtnBrowse { background-color: #ff9800; color: black; }
QPushButton#BtnDraw { background-color: #0288d1; color: white; }
QPushButton#BtnDraw:checked { background-color: #01579b; border: 2px solid #81d4fa; }
QPushButton#BtnStartStop { background-color: #424242; }
QPushButton#BtnReport { background-color: #607d8b; }
QTableWidget { background-color: #2b2b36; gridline-color: #444; border: none; border-radius: 10px; }
QHeaderView::section { background-color: #333; color: #fff; border: none; padding: 6px; font-weight: 800; }
QSlider::groove:horizontal { height: 10px; border-radius: 5px; background: #444; }
QSlider::handle:horizontal { width: 18px; margin: -6px 0; border-radius: 9px; background: #ddd; }
"""
