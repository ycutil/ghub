"""미니맵 ROI 캡처 디버그 도구.

WinRT 캡처로 게임 창에서 미니맵 영역을 캡처해 저장.
Delete 키: 미니맵 ROI 캡처 + 빨간 픽셀 마스크 저장
ESC: 종료
"""

import ctypes
import sys
import time
from pathlib import Path

import cv2
import numpy as np

import config
from capture import GameCapture


VK_DELETE = 0x2E
VK_ESCAPE = 0x1B
user32 = ctypes.WinDLL("user32", use_last_error=True)


def is_key_pressed(vk: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def main():
    cfg = config.load()
    minimap_roi = cfg.get("minimap_roi", [1600, 80, 1880, 270])

    save_dir = config.BASE_DIR / "debug_frames"
    save_dir.mkdir(exist_ok=True)

    print("=" * 50)
    print(" 미니맵 ROI 디버그 캡처")
    print("=" * 50)
    print(f"  minimap_roi: {minimap_roi}")
    print(f"  크기: {minimap_roi[2]-minimap_roi[0]}x{minimap_roi[3]-minimap_roi[1]}")
    print(f"  저장 위치: {save_dir}")
    print()
    print("  Delete = 미니맵 캡처")
    print("  ESC    = 종료")
    print()

    cap = GameCapture(window_name=cfg.get("window_name", "AION2"))
    cap.start()

    if not cap.is_ready():
        print("게임 창을 찾을 수 없음!")
        input("아무 키나 누르면 종료...")
        return

    print("캡처 준비 완료. Delete 키를 누르세요.\n")

    count = 0
    was_pressed = False

    try:
        while True:
            if is_key_pressed(VK_ESCAPE):
                print("\n종료.")
                break

            pressed = is_key_pressed(VK_DELETE)
            if pressed and not was_pressed:
                # 미니맵 ROI 캡처
                frame = cap.grab_roi(minimap_roi)
                if frame is None:
                    print("  프레임 없음!")
                else:
                    count += 1

                    # 원본 저장
                    path_orig = str(save_dir / f"minimap_{count}.png")
                    cv2.imwrite(path_orig, frame)

                    # 빨간 마스크 시각화
                    sub = frame[::2, ::2]
                    b = sub[:, :, 0].astype(np.int16)
                    g = sub[:, :, 1].astype(np.int16)
                    r = sub[:, :, 2].astype(np.int16)
                    mask = (r > 210) & (g < 80) & (b < 80)
                    red_count = int(np.count_nonzero(mask))

                    # 마스크를 원본 크기로 확대해서 시각화
                    mask_vis = np.zeros_like(frame)
                    mask_full = np.repeat(np.repeat(
                        mask.astype(np.uint8), 2, axis=0), 2, axis=1)
                    h, w = frame.shape[:2]
                    mask_full = mask_full[:h, :w]
                    mask_vis[:, :, 2] = mask_full * 255  # 빨간색으로 표시

                    # 원본 + 마스크 오버레이
                    overlay = cv2.addWeighted(frame, 0.7, mask_vis, 0.5, 0)
                    path_mask = str(save_dir / f"minimap_{count}_mask.png")
                    cv2.imwrite(path_mask, overlay)

                    print(f"  [{count}] 저장: {path_orig}")
                    print(f"       마스크: {path_mask}")
                    print(f"       빨간 픽셀: {red_count}개 (threshold=3)")
                    print(f"       프레임 크기: {frame.shape[1]}x{frame.shape[0]}")

                # 전체 프레임도 저장 (ROI 위치 확인용)
                full = cap.grab_full()
                if full is not None:
                    x1, y1, x2, y2 = minimap_roi
                    cv2.rectangle(full, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(full, "minimap_roi", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    path_full = str(save_dir / f"fullframe_{count}.png")
                    cv2.imwrite(path_full, full)
                    print(f"       전체: {path_full} ({full.shape[1]}x{full.shape[0]})")
                print()

            was_pressed = pressed
            time.sleep(0.01)
    finally:
        cap.stop()

    input("아무 키나 누르면 종료...")


if __name__ == "__main__":
    main()
