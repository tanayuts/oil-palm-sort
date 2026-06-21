"""Camera abstraction that handles live cameras, video files, and images.

Extracted from the original monolithic main.py (Phase 3 of the refactor).
Provides the SmartCam class which wraps cv2.VideoCapture with automatic
reconnection for live cameras and support for static image/video sources.
"""

from __future__ import annotations

import time
from typing import Optional

import cv2


class SmartCam:
    """Camera abstraction that handles live cameras, video files, and images."""

    def __init__(self, src: int | str = 0) -> None:
        self.cap: Optional[cv2.VideoCapture] = None
        self.set_source(src)

    def set_source(self, src: int | str) -> None:
        """Switch to a new camera source or media file.

        Args:
            src: Integer camera index or string path to a video/image file.
        """
        self.src = src
        self.is_image = False
        self.static_frame = None
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
        self.cap = None

        if isinstance(src, str) and src.lower().endswith((".jpg", ".png", ".jpeg")):
            self.is_image = True
            img = cv2.imread(src)
            self.static_frame = img if img is not None else None
            self.is_connected = self.static_frame is not None
        else:
            self.cap = (
                cv2.VideoCapture(self.src, cv2.CAP_DSHOW)
                if isinstance(self.src, int)
                else cv2.VideoCapture(self.src)
            )
            self.is_connected = self.cap.isOpened()

    def read(self) -> tuple[bool, Optional[cv2.Mat]]:
        """Read the next frame from the camera/source.

        Returns:
            A tuple (success, frame). frame is None on failure.
        """
        if self.is_image:
            return (
                (True, self.static_frame.copy())
                if self.static_frame is not None
                else (False, None)
            )

        if self.cap is None or not self.cap.isOpened():
            self.is_connected = False
            return False, None

        ret, frame = self.cap.read()

        if not ret and isinstance(self.src, str):  # Loop video
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()

        if not ret:
            self.is_connected = False
            return False, None

        self.is_connected = True
        return True, frame

    def reconnect(self) -> bool:
        """Attempt to reconnect a disconnected live camera.

        Returns:
            True if reconnection succeeded.
        """
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        time.sleep(0.2)
        self.cap = (
            cv2.VideoCapture(self.src, cv2.CAP_DSHOW)
            if isinstance(self.src, int)
            else cv2.VideoCapture(self.src)
        )
        self.is_connected = self.cap.isOpened()
        return self.is_connected

    def release(self) -> None:
        """Release the camera resource."""
        try:
            if self.cap:
                self.cap.release()
        except Exception:
            pass
