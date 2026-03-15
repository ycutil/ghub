"""ScrollLock 토글을 통한 IPC 모듈.

Python → ScrollLock ON/OFF → G-Hub Lua 폴링 → PressAndReleaseKey
"""

import atexit
import ctypes
import time

VK_SCROLL = 0x91
KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.WinDLL("user32", use_last_error=True)


def _is_on() -> bool:
    """ScrollLock 현재 상태 반환."""
    return bool(user32.GetKeyState(VK_SCROLL) & 1)


def _toggle() -> None:
    """ScrollLock 한 번 토글 (press + release)."""
    user32.keybd_event(VK_SCROLL, 0x46, 0, 0)
    user32.keybd_event(VK_SCROLL, 0x46, KEYEVENTF_KEYUP, 0)


def ensure_off() -> None:
    """ScrollLock이 ON이면 OFF로 전환."""
    if _is_on():
        _toggle()


def signal_skill(hold_ms: int = 120) -> None:
    """ScrollLock ON → hold_ms 유지 → OFF.

    Lua 폴링 간격(30ms)의 4배 마진으로 안정적 감지 보장.
    """
    if not _is_on():
        _toggle()
    time.sleep(hold_ms / 1000.0)
    if _is_on():
        _toggle()


# 프로세스 종료 시 ScrollLock OFF 보장
atexit.register(ensure_off)
