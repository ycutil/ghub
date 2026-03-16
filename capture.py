"""WinRT Graphics Capture 기반 창 캡처 모듈.

게임 창이 다른 창에 가려져 있어도 캡처 가능.
최소화 상태에서는 불가.
"""

import threading
import time
import numpy as np
from windows_capture import WindowsCapture, Frame, InternalCaptureControl


def _ts() -> str:
    return time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"


class GameCapture:
    """WinRT Graphics Capture로 게임 창 캡처.

    별도 스레드에서 프레임을 지속 수신하고,
    grab_roi()로 최신 프레임에서 ROI를 잘라 반환.
    """

    def __init__(self, window_name: str = "AION2"):
        self._window_name = window_name
        self._latest_frame = None
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._capture_thread = None
        self._running = False

    def start(self):
        """캡처 시작 (별도 스레드)."""
        self._running = True
        self._capture_thread = threading.Thread(
            target=self._run_capture, daemon=True)
        self._capture_thread.start()

        # 첫 프레임 대기 (최대 5초)
        if self._ready.wait(timeout=5.0):
            with self._lock:
                shape = self._latest_frame.shape if self._latest_frame is not None else None
            print(f"[{_ts()}][CAP] WinRT 캡처 시작됨: window='{self._window_name}', frame={shape}")
        else:
            print(f"[{_ts()}][CAP][경고] 첫 프레임 수신 대기 타임아웃")

    def _run_capture(self):
        """WinRT 캡처 루프."""
        capture = WindowsCapture(
            cursor_capture=False,
            draw_border=None,
            window_name=self._window_name,
        )

        app = self  # 클로저용

        @capture.event
        def on_frame_arrived(frame: Frame, capture_control: InternalCaptureControl):
            if not app._running:
                capture_control.stop()
                return
            # BGRA → BGR (alpha 채널 제거)
            buf = frame.frame_buffer
            bgr = np.array(buf[:, :, :3])
            with app._lock:
                app._latest_frame = bgr
            if not app._ready.is_set():
                app._ready.set()

        @capture.event
        def on_closed():
            app._running = False

        try:
            capture.start()
        except Exception as e:
            print(f"[{_ts()}][CAP][오류] WinRT 캡처 실패: {e}")
            self._running = False

    def grab_roi(self, roi: list[int]) -> np.ndarray | None:
        """최신 프레임에서 ROI 영역을 BGR로 반환.

        Args:
            roi: [x1, y1, x2, y2]

        Returns:
            BGR numpy array 또는 None
        """
        with self._lock:
            frame = self._latest_frame

        if frame is None:
            return None

        x1, y1, x2, y2 = roi
        h, w = frame.shape[:2]
        # 범위 체크
        if x2 > w or y2 > h:
            return None

        return frame[y1:y2, x1:x2].copy()

    def grab_full(self) -> np.ndarray | None:
        """전체 프레임 반환 (디버그용)."""
        with self._lock:
            frame = self._latest_frame
        if frame is None:
            return None
        return frame.copy()

    def stop(self):
        """캡처 중지."""
        self._running = False
        print(f"[{_ts()}][CAP] 캡처 중지됨")

    def is_ready(self) -> bool:
        return self._ready.is_set()
