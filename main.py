"""오버레이 UI + 트레이 아이콘 + WinRT 창 캡처.
스킬 자동 발동 + 미니맵 적 탐지 + 투기장 매칭 알림.
"""

import ctypes
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import pystray

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


def _create_tray_icon_image(color="green"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if color == "green":
        fill = (68, 255, 68, 255)
    elif color == "red":
        fill = (255, 68, 68, 255)
    else:
        fill = (136, 136, 136, 255)
    draw.ellipse([8, 8, 56, 56], fill=fill)
    draw.text((20, 18), "AG", fill=(255, 255, 255, 255))
    return img


def detect_enemy_red(bgr_frame: np.ndarray, threshold: int = 3) -> tuple[bool, int]:
    """미니맵에서 빨간 삼각형(적) 탐지.

    서브샘플링 후 R>210, G<80, B<80 픽셀 수로 판정.
    Returns: (detected, red_pixel_count)
    """
    # 서브샘플링 (2픽셀 건너뛰기)
    sub = bgr_frame[::2, ::2]
    b = sub[:, :, 0].astype(np.int16)
    g = sub[:, :, 1].astype(np.int16)
    r = sub[:, :, 2].astype(np.int16)
    mask = (r > 210) & (g < 80) & (b < 80)
    count = int(np.count_nonzero(mask))
    return (count >= threshold, count)


class OverlayApp:
    """260x100 오버레이 창 + 트레이 아이콘."""

    BG_COLOR = "#1a1a2e"
    FLASH_COLOR = "#ff2222"
    ENEMY_COLOR = "#ff6600"

    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.85)
        self.root.geometry("260x100+50+50")
        self.root.configure(bg=self.BG_COLOR)
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

        self.active = False
        self.trigger_count = 0
        self.enemy_count = 0
        self._drag_x = 0
        self._drag_y = 0
        self._flashing = False
        self._cap = None
        self._visible = True

        self.root.bind("<Button-1>", self._on_press)
        self.root.bind("<B1-Motion>", self._on_drag)

        self._build_ui()

        self._stop_event = threading.Event()
        self._thread = None
        self._enemy_thread = None
        self._arena_thread = None

        self._tray = None
        self._setup_tray()

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
        self.btn.place(x=10, y=10, width=195, height=40)

        self.close_btn = tk.Button(
            self.root,
            text="✕",
            font=("Consolas", 12, "bold"),
            fg="#888888",
            bg="#2a2a3e",
            activeforeground="#ff4444",
            activebackground="#3a3a4e",
            bd=0, relief="flat", cursor="hand2",
            command=self._quit,
        )
        self.close_btn.place(x=210, y=10, width=40, height=40)

        self.status_label = tk.Label(
            self.root,
            text="대기 중",
            font=("Consolas", 10),
            fg="#888888",
            bg=self.BG_COLOR,
            anchor="w",
        )
        self.status_label.place(x=10, y=60, width=240, height=30)

    def _setup_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("보이기/숨기기", self._tray_toggle_visible),
            pystray.MenuItem("ON/OFF", self._tray_toggle_active),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", self._tray_quit),
        )
        self._tray = pystray.Icon(
            "aion_ghub",
            _create_tray_icon_image("gray"),
            "AION2 Auto-Skill",
            menu,
        )
        threading.Thread(target=self._tray.run, daemon=True).start()

    def _update_tray_icon(self, color=None):
        if self._tray:
            if color is None:
                color = "green" if self.active else "gray"
            self._tray.icon = _create_tray_icon_image(color)

    def _tray_toggle_visible(self):
        self.root.after(0, self._toggle_visible)

    def _toggle_visible(self):
        if self._visible:
            self.root.withdraw()
            self._visible = False
        else:
            self.root.deiconify()
            self._visible = True

    def _tray_toggle_active(self):
        self.root.after(0, self._toggle)

    def _tray_quit(self):
        self.root.after(0, self._quit)

    def _quit(self):
        if self.active:
            self._stop()
        if self._tray:
            self._tray.stop()
        self.root.destroy()

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
        self._update_tray_icon()

        cfg = config.load()
        self._cap = GameCapture(window_name=cfg.get("window_name", "AION2"))
        self._cap.start()

        if not self._cap.is_ready():
            self._status("게임 창을 찾을 수 없음!")
            self.active = False
            self.btn.config(text="▶ OFF", fg="#ff4444")
            self._update_tray_icon()
            return

        self._stop_event.clear()

        # 스킬 감시
        self._thread = threading.Thread(target=self._skill_loop, daemon=True)
        self._thread.start()

        # 적 탐지 (미니맵)
        if cfg.get("enemy_detect", True):
            self._enemy_thread = threading.Thread(
                target=self._enemy_loop, daemon=True)
            self._enemy_thread.start()

        # 투기장 매칭
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
        self._update_tray_icon()

    def _status(self, text: str):
        try:
            self.status_label.config(text=text)
        except tk.TclError:
            pass

    # ── 깜빡임 알림 ──
    def _flash_alert(self, msg: str, color=None):
        self._flashing = True
        flash_color = color or self.FLASH_COLOR
        self.root.after(0, self._status, msg)
        self._do_flash(0, flash_color)

    def _do_flash(self, count: int, flash_color: str = None):
        if flash_color is None:
            flash_color = self.FLASH_COLOR
        if not self._flashing or count >= 20:
            self._flashing = False
            try:
                self.root.configure(bg=self.BG_COLOR)
                self.status_label.configure(bg=self.BG_COLOR)
            except tk.TclError:
                pass
            return
        color = flash_color if count % 2 == 0 else self.BG_COLOR
        try:
            self.root.configure(bg=color)
            self.status_label.configure(bg=color)
            self.root.after(300, self._do_flash, count + 1, flash_color)
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
            elif not detected and not self._flashing:
                if int(now * 2) % 2 == 0:
                    self.root.after(0, self._status,
                        f"감시 중  score={score:.3f}  #{self.trigger_count}")

            sleep_time = interval_sec - (time.perf_counter() - loop_start)
            if sleep_time > 0:
                time.sleep(sleep_time)

    # ── 적 탐지 루프 (미니맵) ──
    def _enemy_loop(self):
        cfg = config.load()
        minimap_roi = cfg.get("minimap_roi", [1600, 80, 1880, 270])
        red_threshold = cfg.get("enemy_red_threshold", 3)
        cooldown_sec = cfg.get("enemy_cooldown_ms", 3000) / 1000.0
        last_alert = 0.0

        while not self._stop_event.is_set():
            frame = self._cap.grab_roi(minimap_roi)
            if frame is None:
                time.sleep(0.1)
                continue

            detected, red_count = detect_enemy_red(frame, red_threshold)
            now = time.perf_counter()

            if detected and (now - last_alert) >= cooldown_sec:
                last_alert = now
                self.enemy_count += 1
                self._update_tray_icon("red")
                self.root.after(0, self._flash_alert,
                    f"⚠ 적 발견! red={red_count}px", self.ENEMY_COLOR)
                # 5초 후 트레이 아이콘 복원
                self.root.after(5000, lambda: self._update_tray_icon())

            time.sleep(0.2)  # 200ms 간격

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
