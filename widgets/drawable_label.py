"""Custom QLabel that supports mouse-drag rectangle drawing for zone selection.

Extracted from the original monolithic main.py (Phase 3 of the refactor).
This widget is used by the main window to let operators draw the
"Active Zone" rectangle on the camera feed.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel


class DrawableLabel(QLabel):
    """QLabel that supports mouse-drag rectangle drawing for zone selection."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.drawing = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.current_rect = QRect()
        self.is_draw_mode = False
        self.on_zone_selected: Optional[Callable[[QRect], None]] = None

    def mousePressEvent(self, event) -> None:
        if self.is_draw_mode and event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.current_rect = QRect(self.start_point, self.end_point)
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self.drawing and self.is_draw_mode:
            self.end_point = event.pos()
            self.current_rect = QRect(self.start_point, self.end_point).normalized()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self.drawing and self.is_draw_mode and event.button() == Qt.LeftButton:
            self.drawing = False
            self.current_rect = QRect(self.start_point, event.pos()).normalized()
            if self.on_zone_selected:
                self.on_zone_selected(self.current_rect)
            self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.is_draw_mode and not self.current_rect.isNull():
            painter = QPainter(self)
            pen = QPen(QColor(0, 255, 255), 3, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(self.current_rect)
