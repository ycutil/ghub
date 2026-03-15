"""메인 루프: 캡처 → 감지 → ScrollLock 신호."""

import ctypes
import sys
import time
from pathlib import Path

import config
from capture import ScreenCapture
from detector import IconDetector
from signal_ipc import ensure_off, signal_skill


def _set_timer_resolution() -> None:
    """Windows 타이머 해상도를 1ms로 설정."""
    try:
        winmm = ctypes.WinDLL("winmm", use_last_error=True)
        winmm.timeBeginPeriod(1)
    except OSError:
        pass


def main() -> None:
    cfg = config.load()

    # 템플릿 존재 확인
    tpl_path = config.BASE_DIR / cfg["template_path"]
    if not tpl_path.exists():
        print(f"[오류] 템플릿 이미지가 없습니다: {tpl_path}")
        print("roi_selector.py를 먼저 실행하여 ROI와 템플릿을 설정하세요.")
        sys.exit(1)

    # 초기화
    _set_timer_resolution()
    ensure_off()

    cap = ScreenCapture(cfg["roi"])
    det = IconDetector(str(tpl_path), cfg["match_threshold"])

    cooldown_sec = cfg["cooldown_ms"] / 1000.0
    interval_sec = cfg["capture_interval_ms"] / 1000.0
    hold_ms = cfg["scrolllock_hold_ms"]
    last_trigger = 0.0

    print(f"[시작] ROI={cfg['roi']}, 스킬키={cfg['skill_key']}, 쿨다운={cfg['cooldown_ms']}ms")
    print("종료하려면 Ctrl+C를 누르세요.")

    try:
        while True:
            frame = cap.grab_gray()
            detected, confidence = det.detect(frame)

            now = time.perf_counter()
            if detected and (now - last_trigger) >= cooldown_sec:
                signal_skill(hold_ms)
                last_trigger = time.perf_counter()
                print(f"  [발동] confidence={confidence:.3f}")

            # 캡처 간격 유지
            elapsed = time.perf_counter() - now
            sleep_time = interval_sec - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[종료]")
    finally:
        ensure_off()
        cap.close()


if __name__ == "__main__":
    main()
