"""ROI 영역 색상 기반 아이콘 감지 모듈.

애니메이션이 있는 스킬 아이콘은 템플릿 매칭 대신
특정 색상(초록색)의 비율로 감지한다.
"""

import time
import cv2
import numpy as np


def _ts() -> str:
    return time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"


class IconDetector:
    """ROI 영역에서 초록색 비율로 스킬 아이콘 활성화를 감지."""

    # HSV 초록색 범위 (조정 가능)
    GREEN_LOW = np.array([35, 50, 50])
    GREEN_HIGH = np.array([90, 255, 255])

    def __init__(self, threshold: float = 0.3):
        """
        Args:
            threshold: 초록색 픽셀 비율 임계값 (0.0~1.0).
                       ROI 중 이 비율 이상이 초록색이면 감지됨.
        """
        self._threshold = threshold
        print(f"[{_ts()}][DET] 색상 감지 모드: 초록색 비율 >= {threshold:.0%} 이면 감지")
        print(f"[{_ts()}][DET] HSV 범위: H={self.GREEN_LOW[0]}-{self.GREEN_HIGH[0]}, "
              f"S={self.GREEN_LOW[1]}-{self.GREEN_HIGH[1]}, "
              f"V={self.GREEN_LOW[2]}-{self.GREEN_HIGH[2]}")

    def detect(self, bgr_frame: np.ndarray) -> tuple[bool, float]:
        """ROI 프레임(BGR)에서 초록색 비율로 감지.

        Returns:
            (detected, green_ratio): 초록색 비율이 임계값 이상이면 detected=True
        """
        hsv = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.GREEN_LOW, self.GREEN_HIGH)
        total_pixels = mask.shape[0] * mask.shape[1]
        green_pixels = np.count_nonzero(mask)
        ratio = green_pixels / total_pixels if total_pixels > 0 else 0.0

        detected = ratio >= self._threshold
        return (detected, ratio)
