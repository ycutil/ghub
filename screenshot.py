"""Delete 키를 누르면 전체 화면 캡처하는 도구.

캡처된 이미지는 debug_frames/screenshot_N.png로 저장됩니다.
ESC로 종료.
"""

import sys
import time
import ctypes
from pathlib import Path

import cv2
import numpy as np
import mss


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


VK_DELETE = 0x2E
VK_ESCAPE = 0x1B
user32 = ctypes.WinDLL("user32", use_last_error=True)


def is_key_pressed(vk: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def main():
    base = _base_dir()
    save_dir = base / "debug_frames"
    save_dir.mkdir(exist_ok=True)

    print("=" * 50)
    print(" 스크린샷 캡처 도구")
    print("=" * 50)
    print()
    print("  Delete  = 전체 화면 캡처")
    print("  ESC     = 종료")
    print()
    print(f"  저장 위치: {save_dir}")
    print()

    count = 0
    was_pressed = False

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        print(f"  모니터: {monitor['width']}x{monitor['height']}")
        print()
        print("대기 중...")

        while True:
            if is_key_pressed(VK_ESCAPE):
                print("\n종료.")
                break

            pressed = is_key_pressed(VK_DELETE)
            if pressed and not was_pressed:
                img = sct.grab(monitor)
                frame = np.array(img)[:, :, :3]
                count += 1
                filename = f"screenshot_{count}.png"
                path = str(save_dir / filename)
                cv2.imwrite(path, frame)
                print(f"  [{count}] 캡처 완료: {path}")

            was_pressed = pressed
            time.sleep(0.01)

    input("아무 키나 누르면 종료...")


if __name__ == "__main__":
    main()
