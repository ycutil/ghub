"""오버레이 UI + WinRT 창 캡처 → 다중 템플릿 매칭 → ScrollLock 신호.

게임이 다른 창에 가려져 있어도 동작.
투기장 매칭 감시 + 오버레이 깜빡임 알림.
"""

import ctypes
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

import config
from capture import GameCapture
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

    BG_COLOR = "#1a1a2e"
    FLASH_COLOR = "#ff2222"

    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.85)
        self.root.geometry("260x100+50+50")
        self.root.configure(bg=self.BG_COLOR)

        self.active = False
        self.trigger_count = 0
        self._drag_x = 0
        self._drag_y = 0
        self._flashing = False
        self._cap = None

        self.root.bind("<Button-1>", self._on_press)
        self.root.bind("<B1-Motion>", self._on_drag)

        self._build_ui()

        self._stop_event = threading.Event()
        self._thread = None
        self._arena_thread = None

    def _build_ui(self):
        self.btn = tk.Button(
            self.root,
            text="▶ OFF",
            font=("Consolas", 14, "bold"),
            fg="#ff4444",
            bg="#2a2a3e",
            activeforeground="#ff4444",
            activebackground="#3a3a4e",
            bd=0, relief="flat", cursor="hand2",
            command=self._toggle,
        )
        self.btn.place(x=10, y=10, width=240, height=40)

        self.status_label = tk.Label(
            self.root,
            text="대기 중",
            font=("Consolas", 10),
            fg="#888888",
            bg=self.BG_COLOR,
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
        self._status("게임 캡처 연결 중...")

        cfg = config.load()

        # WinRT 캡처 시작 (공유)
        self._cap = GameCapture(window_name=cfg.get("window_name", "AION2"))
        self._cap.start()

        if not self._cap.is_ready():
            self._status("게임 창을 찾을 수 없음!")
            self.active = False
            self.btn.config(text="▶ OFF", fg="#ff4444")
            return

        self._stop_event.clear()

        # 스킬 감시 스레드
        self._thread = threading.Thread(target=self._skill_loop, daemon=True)
        self._thread.start()

        # 투기장 매칭 감시 (설정에 arena_roi가 있으면)
        if cfg.get("arena_roi") and cfg.get("arena_template_path"):
            self._arena_thread = threading.Thread(
                target=self._arena_loop, daemon=True)
            self._arena_thread.start()

        self._status("감시 시작!")

    def _stop(self):
        self.active = False
        self._stop_event.set()
        ensure_off()
        if self._cap:
            self._cap.stop()
            self._cap = None
        self._flashing = False
        self.btn.config(text="▶ OFF", fg="#ff4444")
        self.root.configure(bg=self.BG_COLOR)
        self.status_label.configure(bg=self.BG_COLOR)
        self._status("대기 중")

    def _status(self, text: str):
        try:
            self.status_label.config(text=text)
        except tk.TclError:
            pass

    # ── 깜빡임 알림 ──
    def _flash_alert(self, msg: str):
        self._flashing = True
        self.root.after(0, self._status, msg)
        self._do_flash(0)

    def _do_flash(self, count: int):
        if not self._flashing or count >= 20:
            self._flashing = False
            try:
                self.root.configure(bg=self.BG_COLOR)
                self.status_label.configure(bg=self.BG_COLOR)
            except tk.TclError:
                pass
            return

        color = self.FLASH_COLOR if count % 2 == 0 else self.BG_COLOR
        try:
            self.root.configure(bg=color)
            self.status_label.configure(bg=color)
            self.root.after(500, self._do_flash, count + 1)
        except tk.TclError:
            pass

    # ── 스킬 감시 루프 ──
    def _skill_loop(self):
        cfg = config.load()
        roi = cfg["roi"]
        threshold = cfg["match_threshold"]

        tpl_dir = str(config.BASE_DIR / "templates")
        det = IconDetector(template_dir=tpl_dir, threshold=threshold)

        cooldown_sec = cfg["cooldown_ms"] / 1000.0
        interval_sec = cfg["capture_interval_ms"] / 1000.0
        hold_ms = cfg["scrolllock_hold_ms"]
        last_trigger = 0.0

        while not self._stop_event.is_set():
            loop_start = time.perf_counter()

            frame = self._cap.grab_roi(roi)
            if frame is None:
                time.sleep(0.05)
                continue

            detected, score = det.detect(frame)
            now = time.perf_counter()
            elapsed = now - last_trigger if last_trigger > 0 else float('inf')

            if detected and elapsed >= cooldown_sec:
                signal_skill(hold_ms)
                last_trigger = time.perf_counter()
                self.trigger_count += 1
                self.root.after(0, self._status,
                    f"발동 #{self.trigger_count}  score={score:.3f}")
            elif not detected:
                if int(now * 2) % 2 == 0:
                    self.root.after(0, self._status,
                        f"감시 중  score={score:.3f}  #{self.trigger_count}")

            sleep_time = interval_sec - (time.perf_counter() - loop_start)
            if sleep_time > 0:
                time.sleep(sleep_time)

    # ── 투기장 매칭 감시 루프 ──
    def _arena_loop(self):
        cfg = config.load()
        arena_roi = cfg["arena_roi"]
        arena_tpl = str(config.BASE_DIR / cfg["arena_template_path"])
        arena_threshold = cfg.get("arena_threshold", 0.5)

        import cv2
        tpl = cv2.imread(arena_tpl, cv2.IMREAD_COLOR)
        if tpl is None:
            return

        last_alert = 0.0
        alert_cooldown = 15.0

        while not self._stop_event.is_set():
            frame = self._cap.grab_roi(arena_roi)
            if frame is None:
                time.sleep(0.5)
                continue

            rh, rw = frame.shape[:2]
            th, tw = tpl.shape[:2]
            if (th, tw) != (rh, rw):
                resized = cv2.resize(tpl, (rw, rh), interpolation=cv2.INTER_AREA)
            else:
                resized = tpl

            result = cv2.matchTemplate(frame, resized, cv2.TM_CCOEFF_NORMED)
            score = float(result[0][0])

            now = time.perf_counter()
            if score >= arena_threshold and (now - last_alert) >= alert_cooldown:
                last_alert = now
                self.root.after(0, self._flash_alert,
                    f"⚔ 매칭 잡힘! score={score:.3f}")

            time.sleep(1.0)

    def run(self):
        _set_timer_resolution()
        ensure_off()
        self.root.mainloop()


def main():
    app = OverlayApp()
    app.run()


if __name__ == "__main__":
    main()
