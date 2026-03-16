"""오버레이 UI + ROI 캡처 → 다중 템플릿 매칭 → ScrollLock 신호."""

import ctypes
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

import config
from capture import ScreenCapture
from detector import IconDetector
from signal_ipc import ensure_off, signal_skill, _is_on


def _ts() -> str:
    return time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"


def _set_timer_resolution() -> None:
    try:
        winmm = ctypes.WinDLL("winmm", use_last_error=True)
        winmm.timeBeginPeriod(1)
    except OSError:
        pass


class OverlayApp:
    """260x100 오버레이 창. 타이틀바 없음, 드래그 이동, ON/OFF 토글."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)          # 타이틀바 제거
        self.root.attributes("-topmost", True)     # 항상 위
        self.root.attributes("-alpha", 0.85)       # 약간 투명
        self.root.geometry("260x100+50+50")
        self.root.configure(bg="#1a1a2e")

        # 상태
        self.active = False
        self.trigger_count = 0
        self.last_score = 0.0
        self._drag_x = 0
        self._drag_y = 0

        # 드래그 바인딩
        self.root.bind("<Button-1>", self._on_press)
        self.root.bind("<B1-Motion>", self._on_drag)

        # UI 구성
        self._build_ui()

        # 감시 스레드
        self._stop_event = threading.Event()
        self._thread = None

    def _build_ui(self):
        # 토글 버튼
        self.btn = tk.Button(
            self.root,
            text="▶ OFF",
            font=("Consolas", 14, "bold"),
            fg="#ff4444",
            bg="#2a2a3e",
            activeforeground="#ff4444",
            activebackground="#3a3a4e",
            bd=0,
            relief="flat",
            cursor="hand2",
            command=self._toggle,
        )
        self.btn.place(x=10, y=10, width=240, height=40)

        # 상태 라벨
        self.status_label = tk.Label(
            self.root,
            text="대기 중",
            font=("Consolas", 10),
            fg="#888888",
            bg="#1a1a2e",
            anchor="w",
        )
        self.status_label.place(x=10, y=60, width=240, height=30)

    def _on_press(self, e):
        self._drag_x = e.x
        self._drag_y = e.y

    def _on_drag(self, e):
        x = self.root.winfo_x() + e.x - self._drag_x
        y = self.root.winfo_y() + e.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def _toggle(self):
        if self.active:
            self._stop()
        else:
            self._start()

    def _start(self):
        self.active = True
        self.btn.config(text="■ ON", fg="#44ff44")
        self._status("감시 시작...")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _stop(self):
        self.active = False
        self._stop_event.set()
        ensure_off()
        self.btn.config(text="▶ OFF", fg="#ff4444")
        self._status("대기 중")

    def _status(self, text: str):
        """스레드 안전 상태 업데이트."""
        try:
            self.status_label.config(text=text)
        except tk.TclError:
            pass

    def _loop(self):
        """감시 루프 (별도 스레드)."""
        cfg = config.load()
        roi = cfg["roi"]
        threshold = cfg["match_threshold"]

        cap = ScreenCapture(roi=roi)
        tpl_dir = str(config.BASE_DIR / "templates")
        det = IconDetector(template_dir=tpl_dir, threshold=threshold)

        cooldown_sec = cfg["cooldown_ms"] / 1000.0
        interval_sec = cfg["capture_interval_ms"] / 1000.0
        hold_ms = cfg["scrolllock_hold_ms"]
        last_trigger = 0.0

        while not self._stop_event.is_set():
            loop_start = time.perf_counter()

            frame = cap.grab_bgr()
            if frame is None:
                time.sleep(0.05)
                continue

            detected, score = det.detect(frame)
            self.last_score = score
            now = time.perf_counter()
            elapsed = now - last_trigger if last_trigger > 0 else float('inf')

            if detected and elapsed >= cooldown_sec:
                signal_skill(hold_ms)
                last_trigger = time.perf_counter()
                self.trigger_count += 1
                self.root.after(0, self._status,
                    f"발동 #{self.trigger_count}  score={score:.3f}")
            elif not detected:
                # 주기적 상태 업데이트 (0.5초마다)
                if int(now * 2) % 2 == 0:
                    self.root.after(0, self._status,
                        f"감시 중  score={score:.3f}  #{self.trigger_count}")

            sleep_time = interval_sec - (time.perf_counter() - loop_start)
            if sleep_time > 0:
                time.sleep(sleep_time)

        cap.close()

    def run(self):
        _set_timer_resolution()
        ensure_off()
        self.root.mainloop()


def main():
    app = OverlayApp()
    app.run()


if __name__ == "__main__":
    main()
