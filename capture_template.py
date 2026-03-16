"""게임 화면에서 템플릿 이미지를 직접 캡처하는 도구.

사용법:
  1. 게임을 실행하고 스킬 아이콘이 보이는 상태로 만들기
  2. 이 스크립트 실행
  3. 전체 화면 스크린샷이 열림
  4. 마우스로 스킬 아이콘 영역을 드래그하여 선택
  5. Enter로 확정, ESC로 취소
  6. templates/skill_icon.png로 저장됨
"""

import sys
import cv2
import numpy as np
import mss
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def main():
    base = _base_dir()
    templates_dir = base / "templates"
    templates_dir.mkdir(exist_ok=True)
    save_path = templates_dir / "skill_icon.png"

    print("=" * 50)
    print(" 스킬 아이콘 템플릿 캡처 도구")
    print("=" * 50)
    print()
    print("1. 게임 화면에서 스킬 아이콘이 보이는 상태로 준비하세요")
    print("2. 준비되면 Enter를 누르세요 (3초 후 캡처)")
    input()

    import time
    for i in range(3, 0, -1):
        print(f"  {i}초 후 캡처...")
        time.sleep(1)

    # 캡처
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        img = sct.grab(monitor)
        frame = np.array(img)[:, :, :3]

    print(f"캡처 완료: {frame.shape[1]}x{frame.shape[0]}")

    # 전체 스크린샷 저장 (참고용)
    full_path = str(base / "debug_frames" / "full_screenshot.png")
    (base / "debug_frames").mkdir(exist_ok=True)
    cv2.imwrite(full_path, frame)
    print(f"전체 스크린샷 저장: {full_path}")

    # ROI 선택
    print()
    print("창이 열리면 스킬 아이콘 영역을 마우스로 드래그하세요")
    print("  - Enter/Space: 선택 확정")
    print("  - ESC: 취소")
    print()

    # 화면이 너무 크면 축소해서 표시
    h, w = frame.shape[:2]
    scale = 1.0
    if w > 1600 or h > 900:
        scale = min(1600 / w, 900 / h)
        display = cv2.resize(frame, (int(w * scale), int(h * scale)))
    else:
        display = frame.copy()

    window_name = "Drag to select skill icon, then press Enter"
    roi = cv2.selectROI(window_name, display, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()

    if roi[2] == 0 or roi[3] == 0:
        print("선택 취소됨")
        return

    # 원본 좌표로 변환
    x, y, rw, rh = roi
    x = int(x / scale)
    y = int(y / scale)
    rw = int(rw / scale)
    rh = int(rh / scale)

    # 크롭 및 저장
    cropped = frame[y:y+rh, x:x+rw]
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)

    cv2.imwrite(str(save_path), gray)
    print(f"\n템플릿 저장 완료: {save_path}")
    print(f"  크기: {gray.shape[1]}x{gray.shape[0]}")
    print(f"  픽셀 범위: min={gray.min()}, max={gray.max()}, mean={gray.mean():.1f}")
    print(f"\n이제 aion_ghub.exe를 실행하세요!")
    input("아무 키나 누르면 종료...")


if __name__ == "__main__":
    main()
