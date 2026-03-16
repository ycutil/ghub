"""mss 기반 전체 화면 캡처 모듈."""

import cv2
import numpy as np
import mss


class ScreenCapture:
    """전체 화면 캡처. mss 인스턴스를 재사용하여 오버헤드 최소화."""

    def __init__(self):
        self._sct = mss.mss()
        self._monitor = self._sct.monitors[1]  # 주 모니터

    def grab_gray(self) -> np.ndarray:
        """전체 화면을 캡처하여 Grayscale로 반환."""
        img = self._sct.grab(self._monitor)
        frame = np.array(img)[:, :, :3]
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    def close(self) -> None:
        self._sct.close()
