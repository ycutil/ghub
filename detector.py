"""ROI 영역 다중 템플릿 매칭 기반 아이콘 감지 모듈.

애니메이션 스킬 아이콘을 여러 프레임 템플릿과 비교하여
가장 높은 유사도로 판정한다.
"""

import time
import cv2
import numpy as np
from pathlib import Path


def _ts() -> str:
    return time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"


class IconDetector:
    """다중 템플릿 매칭으로 스킬 아이콘 감지.

    ROI(31x31)와 템플릿(32x32)을 직접 비교.
    3개 템플릿 중 최대 유사도가 임계값 이상이면 감지.
    """

    def __init__(self, template_dir: str, threshold: float = 0.7):
        """
        Args:
            template_dir: 템플릿 이미지들이 있는 폴더 경로
            threshold: 매칭 임계값 (0.0~1.0)
        """
        self._threshold = threshold
        self._templates = []

        tpl_dir = Path(template_dir)
        # skill_1.png, skill_2.png, skill_3.png 로드
        for f in sorted(tpl_dir.glob("skill_*.png")):
            img = cv2.imread(str(f), cv2.IMREAD_COLOR)
            if img is not None:
                self._templates.append((f.name, img))
                print(f"[{_ts()}][DET] 템플릿 로드: {f.name} ({img.shape[1]}x{img.shape[0]})")

        if not self._templates:
            # 폴백: skill_icon.png
            fallback = tpl_dir / "skill_icon.png"
            if fallback.exists():
                img = cv2.imread(str(fallback), cv2.IMREAD_COLOR)
                if img is not None:
                    self._templates.append((fallback.name, img))
                    print(f"[{_ts()}][DET] 폴백 템플릿 로드: {fallback.name}")

        if not self._templates:
            raise FileNotFoundError(f"템플릿 이미지가 없습니다: {tpl_dir}")

        print(f"[{_ts()}][DET] 총 {len(self._templates)}개 템플릿, 임계값={threshold}")

    def detect(self, bgr_frame: np.ndarray) -> tuple[bool, float]:
        """ROI 프레임(BGR)과 모든 템플릿을 비교.

        Returns:
            (detected, best_score): 최대 유사도가 임계값 이상이면 detected=True
        """
        rh, rw = bgr_frame.shape[:2]
        best_score = -1.0

        for name, tpl in self._templates:
            th, tw = tpl.shape[:2]
            # ROI 크기에 맞춰 리사이즈
            if (th, tw) != (rh, rw):
                resized = cv2.resize(tpl, (rw, rh), interpolation=cv2.INTER_AREA)
            else:
                resized = tpl

            # 정규화 상관계수
            result = cv2.matchTemplate(bgr_frame, resized, cv2.TM_CCOEFF_NORMED)
            score = float(result[0][0])
            if score > best_score:
                best_score = score

        detected = best_score >= self._threshold
        return (detected, best_score)
