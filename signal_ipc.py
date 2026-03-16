"""ScrollLock 토글을 통한 IPC 모듈.

Python → ScrollLock ON → G-Hub Lua 감지 → 키 입력 + ScrollLock OFF
"""

import atexit
import ctypes
import time

VK_SCROLL = 0x91
KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.WinDLL("user32", use_last_error=True)


def _is_on() -> bool:
    return bool(user32.GetKeyState(VK_SCROLL) & 1)


def _toggle() -> None:
    user32.keybd_event(VK_SCROLL, 0x46, 0, 0)
    user32.keybd_event(VK_SCROLL, 0x46, KEYEVENTF_KEYUP, 0)


def ensure_off() -> None:
    if _is_on():
        _toggle()


def signal_skill(hold_ms: int = 0) -> None:
    """ScrollLock ON만 토글. OFF는 Lua가 처리."""
    if not _is_on():
        _toggle()


atexit.register(ensure_off)
