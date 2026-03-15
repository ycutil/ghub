"""mss 기반 화면 캡처 모듈."""

import cv2
import numpy as np
import mss


class ScreenCapture:
    """ROI 영역 화면 캡처. mss 인스턴스를 재사용하여 오버헤드 최소화."""

    def __init__(self, roi: dict):
        """
        Args:
            roi: {"left": int, "top": int, "width": int, "height": int}
        """
        self._sct = mss.mss()
        self._monitor = {
            "left": roi["left"],
            "top": roi["top"],
            "width": roi["width"],
            "height": roi["height"],
        }

    def grab_gray(self) -> np.ndarray:
        """ROI 영역을 캡처하여 Grayscale로 반환."""
        img = self._sct.grab(self._monitor)
        # BGRA → BGR → Grayscale
        frame = np.array(img)[:, :, :3]
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    def close(self) -> None:
        self._sct.close()
