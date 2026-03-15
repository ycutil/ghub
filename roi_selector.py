"""ROI 선택 GUI.

전체 화면 스크린샷 위에서 드래그로 ROI를 지정하고,
ROI 안에서 템플릿 아이콘 영역을 지정하여 저장한다.
"""

import tkinter as tk
from pathlib import Path

import cv2
import mss
import numpy as np
from PIL import Image, ImageTk

import config

TEMPLATES_DIR = config.BASE_DIR / "templates"


class RegionSelector:
    """스크린샷 위에서 사각형 영역을 선택하는 GUI."""

    def __init__(self, title: str, screenshot: np.ndarray):
        self._screenshot = screenshot
        self._title = title
        self._start = None
        self._rect_id = None
        self.result = None  # (x, y, w, h)

        self._root = tk.Tk()
        self._root.title(title)
        self._root.attributes("-fullscreen", True)
        self._root.attributes("-topmost", True)

        # numpy BGR → PIL RGB → PhotoImage
        img_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        self._tk_img = ImageTk.PhotoImage(pil_img)

        self._canvas = tk.Canvas(self._root, cursor="cross")
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.create_image(0, 0, anchor=tk.NW, image=self._tk_img)

        # 안내 텍스트
        self._canvas.create_text(
            screenshot.shape[1] // 2, 30,
            text=f"{title} — 드래그로 영역 선택 (ESC 취소)",
            fill="yellow", font=("맑은 고딕", 16, "bold"),
        )

        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._root.bind("<Escape>", lambda e: self._root.destroy())

    def _on_press(self, event):
        self._start = (event.x, event.y)
        if self._rect_id:
            self._canvas.delete(self._rect_id)
        self._rect_id = self._canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline="lime", width=2,
        )

    def _on_drag(self, event):
        if self._start and self._rect_id:
            self._canvas.coords(
                self._rect_id,
                self._start[0], self._start[1], event.x, event.y,
            )

    def _on_release(self, event):
        if not self._start:
            return
        x1, y1 = self._start
        x2, y2 = event.x, event.y
        # 정규화 (좌상→우하)
        left = min(x1, x2)
        top = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        if w > 5 and h > 5:
            self.result = (left, top, w, h)
            self._root.destroy()

    def run(self):
        self._root.mainloop()
        return self.result


def take_screenshot() -> np.ndarray:
    """전체 화면 스크린샷 (BGR)."""
    with mss.mss() as sct:
        monitor = sct.monitors[0]  # 전체 화면
        img = sct.grab(monitor)
        return np.array(img)[:, :, :3]  # BGRA → BGR


def main() -> None:
    print("[1/2] 전체 화면 캡처 중...")
    screenshot = take_screenshot()

    # 1단계: ROI 선택
    print("[1/2] ROI 영역을 선택하세요 (스킬 아이콘이 나타나는 영역).")
    selector = RegionSelector("1/2: ROI 영역 선택", screenshot)
    roi = selector.run()
    if roi is None:
        print("취소됨.")
        return
    roi_left, roi_top, roi_w, roi_h = roi
    print(f"  ROI: left={roi_left}, top={roi_top}, width={roi_w}, height={roi_h}")

    # ROI 영역 잘라내기
    roi_crop = screenshot[roi_top:roi_top + roi_h, roi_left:roi_left + roi_w]

    # 2단계: 템플릿 아이콘 선택
    print("[2/2] ROI 안에서 템플릿 아이콘 영역을 선택하세요.")
    selector2 = RegionSelector("2/2: 템플릿 아이콘 선택", roi_crop)
    icon = selector2.run()
    if icon is None:
        print("취소됨.")
        return
    ix, iy, iw, ih = icon

    # 템플릿 저장
    TEMPLATES_DIR.mkdir(exist_ok=True)
    template = roi_crop[iy:iy + ih, ix:ix + iw]
    tpl_path = TEMPLATES_DIR / "skill_icon.png"
    cv2.imwrite(str(tpl_path), template)
    print(f"  템플릿 저장: {tpl_path}")

    # config 저장
    cfg = config.load()
    cfg["roi"] = {
        "left": roi_left,
        "top": roi_top,
        "width": roi_w,
        "height": roi_h,
    }
    cfg["template_path"] = "templates/skill_icon.png"
    config.save(cfg)
    print(f"  설정 저장: {config.CONFIG_PATH}")
    print("\n완료! main.py를 실행하세요.")


if __name__ == "__main__":
    main()
