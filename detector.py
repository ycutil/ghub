"""OpenCV 템플릿 매칭 기반 아이콘 감지 모듈."""

import cv2
import numpy as np


class IconDetector:
    """Grayscale 템플릿 매칭으로 스킬 활성화 아이콘을 감지."""

    def __init__(self, template_path: str, threshold: float = 0.8):
        self._template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if self._template is None:
            raise FileNotFoundError(f"템플릿 이미지를 찾을 수 없습니다: {template_path}")
        self._threshold = threshold

    def detect(self, gray_frame: np.ndarray) -> tuple[bool, float]:
        """프레임에서 아이콘 감지.

        Returns:
            (detected, confidence): 임계값 이상이면 detected=True
        """
        result = cv2.matchTemplate(gray_frame, self._template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        return (max_val >= self._threshold, float(max_val))
