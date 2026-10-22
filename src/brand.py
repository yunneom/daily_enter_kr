"""채널 아이덴티티 — data/channel.json 단일 소스.

2026-10-22 재설정: 조회의 98.6%가 '만원으로 걸그룹 조합' 시리즈라 채널을 그
게임 포맷에 올인한다. 핸들/표시명은 여기서만 읽는다(코드에 하드코딩 금지).
"""
import json
from pathlib import Path

_PATH = Path(__file__).parent.parent / "data" / "channel.json"
try:
    _CFG = json.loads(_PATH.read_text(encoding="utf-8"))
except Exception:  # 설정 파일이 없어도 렌더는 돼야 한다
    _CFG = {}

HANDLE: str = (_CFG.get("handle") or "daily_enter_kr").lstrip("@")
DISPLAY_NAME: str = _CFG.get("display_name") or "만원으로 걸그룹 만들기"
TAGLINE: str = _CFG.get("tagline") or ""
IG_URL: str = f"https://www.instagram.com/{HANDLE}/"


def handle_tag() -> str:
    return f"@{HANDLE}"


def brand_line(suffix: str = "") -> str:
    """카드 푸터용 '@핸들 · 접미' 한 줄."""
    return f"{handle_tag()} · {suffix}" if suffix else handle_tag()
