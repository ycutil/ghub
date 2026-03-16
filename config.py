"""JSON 설정 관리 모듈."""

import json
import sys
from pathlib import Path


def _base_dir() -> Path:
    """exe 실행 시 exe 위치, 스크립트 실행 시 스크립트 위치."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


BASE_DIR = _base_dir()
CONFIG_PATH = BASE_DIR / "config.json"

DEFAULTS = {
    "template_path": "templates/skill_icon.png",
    "roi": [1261, 470, 1292, 501],       # [x1, y1, x2, y2] 스킬 아이콘 영역
    "match_threshold": 0.5,    # 다중 템플릿 매칭 임계값
    "skill_key": "f1",
    "cooldown_ms": 2000,
    "capture_interval_ms": 10,
    "scrolllock_hold_ms": 50,     # ScrollLock 유지 시간 (50ms = Lua 10ms 폴링 x 5)
}


def load() -> dict:
    """설정 파일을 로드한다. 없으면 기본값으로 생성."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # 누락된 키에 기본값 채우기
        for key, val in DEFAULTS.items():
            cfg.setdefault(key, val)
        return cfg
    save(DEFAULTS)
    return dict(DEFAULTS)


def save(cfg: dict) -> None:
    """설정을 JSON 파일로 저장."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
