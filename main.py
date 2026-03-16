"""메인 루프: ROI 캡처 → 다중 템플릿 매칭 → ScrollLock 신호."""

import ctypes
import sys
import time
from pathlib import Path

import config
from capture import ScreenCapture
from detector import IconDetector
from signal_ipc import ensure_off, signal_skill, _is_on

# ── 디버그 설정 ──
DEBUG_LOG_INTERVAL = 100    # N프레임마다 상태 로그
DEBUG_SAVE_FIRST = True     # 첫 프레임 저장


def _ts() -> str:
    return time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"


def _set_timer_resolution() -> None:
    try:
        winmm = ctypes.WinDLL("winmm", use_last_error=True)
        winmm.timeBeginPeriod(1)
        print(f"[{_ts()}][INIT] 타이머 해상도 1ms 설정 완료")
    except OSError as e:
        print(f"[{_ts()}][INIT][경고] 타이머 해상도 설정 실패: {e}")


def main() -> None:
    cfg = config.load()
    roi = cfg["roi"]
    threshold = cfg["match_threshold"]

    print(f"[{_ts()}][INIT] 설정 로드 완료:")
    print(f"  ROI: ({roi[0]},{roi[1]})-({roi[2]},{roi[3]}) = {roi[2]-roi[0]}x{roi[3]-roi[1]}px")
    print(f"  매칭 임계값: {threshold}")
    print(f"  스킬키: {cfg['skill_key']}, 쿨다운: {cfg['cooldown_ms']}ms")

    # 초기화
    _set_timer_resolution()
    ensure_off()
    print(f"[{_ts()}][INIT] ScrollLock: {'ON' if _is_on() else 'OFF'}")

    cap = ScreenCapture(roi=roi)
    tpl_dir = str(config.BASE_DIR / "templates")
    det = IconDetector(template_dir=tpl_dir, threshold=threshold)

    debug_dir = config.BASE_DIR / "debug_frames"
    debug_dir.mkdir(exist_ok=True)

    cooldown_sec = cfg["cooldown_ms"] / 1000.0
    interval_sec = cfg["capture_interval_ms"] / 1000.0
    hold_ms = cfg["scrolllock_hold_ms"]
    last_trigger = 0.0
    frame_count = 0
    trigger_count = 0
    max_score = 0.0

    print("=" * 60)
    print(f"[{_ts()}][시작] 감시 시작 (Ctrl+C로 종료)")
    print("=" * 60)

    try:
        while True:
            loop_start = time.perf_counter()

            # ── 캡처 (ROI, BGR) ──
            cap_start = time.perf_counter()
            frame = cap.grab_bgr()
            cap_ms = (time.perf_counter() - cap_start) * 1000

            if frame is None:
                time.sleep(0.1)
                continue

            # 첫 프레임 저장
            if DEBUG_SAVE_FIRST and frame_count == 0:
                import cv2
                cv2.imwrite(str(debug_dir / "roi_first.png"), frame)
                print(f"[{_ts()}][CAP] 첫 ROI: shape={frame.shape}, "
                      f"min={frame.min()}, max={frame.max()}, mean={frame.mean():.1f}")

            # ── 감지 (다중 템플릿 매칭) ──
            det_start = time.perf_counter()
            detected, score = det.detect(frame)
            det_ms = (time.perf_counter() - det_start) * 1000

            max_score = max(max_score, score)
            frame_count += 1

            # 주기적 로그
            if frame_count % DEBUG_LOG_INTERVAL == 0:
                print(f"[{_ts()}][#{frame_count}] score={score:.4f} "
                      f"(max={max_score:.4f}) cap={cap_ms:.1f}ms det={det_ms:.1f}ms "
                      f"발동={trigger_count}")

            # ── 발동 ──
            now = time.perf_counter()
            elapsed = now - last_trigger if last_trigger > 0 else float('inf')

            if detected:
                print(f"[{_ts()}][감지!] score={score:.4f} (임계={threshold})")

                if elapsed >= cooldown_sec:
                    signal_skill(hold_ms)
                    last_trigger = time.perf_counter()
                    trigger_count += 1
                    print(f"[{_ts()}][발동 #{trigger_count}] ScrollLock 신호 전송!")

                    # 발동 시 ROI 저장 (처음 5번)
                    if trigger_count <= 5:
                        import cv2
                        cv2.imwrite(str(debug_dir / f"roi_trigger_{trigger_count}.png"), frame)
                else:
                    remaining = cooldown_sec - elapsed
                    print(f"[{_ts()}][대기] 쿨다운 남은={remaining:.2f}s")

            # 간격 유지
            sleep_time = interval_sec - (time.perf_counter() - loop_start)
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print(f"\n[{_ts()}][종료] 프레임={frame_count}, 발동={trigger_count}, "
              f"max_score={max_score:.4f}")
    finally:
        ensure_off()
        cap.close()
        print(f"[{_ts()}][종료] 정리 완료")
        input("아무 키나 누르면 종료...")


if __name__ == "__main__":
    main()
