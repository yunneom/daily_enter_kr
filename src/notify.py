"""
Discord webhook 알림 헬퍼.

워크플로우 실패 / 인사이트 다이제스트 생성 / 게시 성공 등을 디스코드로 알림.
DISCORD_WEBHOOK_URL 환경변수 없으면 silent fail.
"""

import os
import requests
from typing import Optional


def notify_discord(content: str, webhook_url: Optional[str] = None,
                   username: Optional[str] = None,
                   embeds: Optional[list] = None) -> bool:
    """Discord 채널에 메시지 보냄. 환경변수 미설정 시 silently False.

    Args:
        content: 본문 (2000자 한도; 자동 잘림)
        webhook_url: 명시 안 하면 DISCORD_WEBHOOK_URL 환경변수 사용
        username: 봇 표시명 (예: "daily_enter_kr")
        embeds: Discord embed 객체 리스트 (선택)
    Returns: True 성공, False 실패/스킵
    """
    webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return False
    payload = {"content": content[:1990]}
    if username:
        payload["username"] = username
    if embeds:
        payload["embeds"] = embeds
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        return resp.ok
    except Exception:
        return False
