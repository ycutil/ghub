"""mss 기반 화면 캡처 모듈. ROI 영역만 BGR로 캡처."""

import time
import numpy as np
import mss


def _ts() -> str:
    return time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"


class ScreenCapture:
    """화면 캡처. ROI 영역만 BGR로 캡처."""

    def __init__(self, roi: list[int]):
        """
        Args:
            roi: [x1, y1, x2, y2] 캡처할 영역
        """
        self._sct = mss.mss()
        monitors = self._sct.monitors
        print(f"[{_ts()}][CAP] 감지된 모니터 수: {len(monitors) - 1}")
        self._primary = monitors[1]
        print(f"[{_ts()}][CAP] 주 모니터: {self._primary}")

        x1, y1, x2, y2 = roi
        self._monitor = {
            "left": self._primary["left"] + x1,
            "top": self._primary["top"] + y1,
            "width": x2 - x1,
            "height": y2 - y1,
        }
        print(f"[{_ts()}][CAP] ROI 캡처: ({x1},{y1})-({x2},{y2}) = {x2-x1}x{y2-y1}px")

    def monitor_info(self) -> dict:
        return dict(self._monitor)

    def grab_bgr(self) -> np.ndarray | None:
        """ROI를 BGR로 캡처."""
        try:
            img = self._sct.grab(self._monitor)
            # mss는 BGRA 반환 → BGR로 변환
            frame = np.array(img)[:, :, :3]
            return frame
        except Exception as e:
            print(f"[{_ts()}][CAP][오류] 캡처 예외: {type(e).__name__}: {e}")
            return None

    def close(self) -> None:
        self._sct.close()
        print(f"[{_ts()}][CAP] mss 인스턴스 닫힘")
