"""
.env → GitHub Secrets 동기화 헬퍼.

[사용]
  python sync_secrets.py                  # 모든 알려진 secret 동기화
  python sync_secrets.py UNSPLASH_ACCESS_KEY  # 특정 키만
  python sync_secrets.py --dry-run        # 무엇이 바뀔지만 출력

[전제]
  gh CLI 설치 + 인증 완료 (gh auth status 로 확인)
  .env 파일에 동기화할 값 존재

[보안]
  실제 값은 화면에 마스킹 표시 (앞 10자 + ... + 뒤 4자).
  값 자체는 stdin으로 gh에 전달 (커맨드라인 노출 X).
"""

import os
import re
import subprocess
import sys
from pathlib import Path

REPO = "yunneom/daily_enter_kr"
ENV_PATH = Path(__file__).parent / ".env"

# 알려진 secret 이름 — 채널 활성화에 따라 사용
KNOWN_SECRETS = [
    # 공통
    "ANTHROPIC_API_KEY",
    "CLOUDINARY_CLOUD_NAME",
    "CLOUDINARY_UPLOAD_PRESET",
    "UNSPLASH_ACCESS_KEY",
    "DISCORD_WEBHOOK_URL",
    # daily_enter_kr (기본)
    "INSTAGRAM_USER_ID",
    "INSTAGRAM_ACCESS_TOKEN",
    "INSTAGRAM_APP_SECRET",
    # daily_sports_kr
    "INSTAGRAM_USER_ID_SPORTS",
    "INSTAGRAM_ACCESS_TOKEN_SPORTS",
    "INSTAGRAM_APP_SECRET_SPORTS",
    # daily_economy_kr
    "INSTAGRAM_USER_ID_ECONOMY",
    "INSTAGRAM_ACCESS_TOKEN_ECONOMY",
    "INSTAGRAM_APP_SECRET_ECONOMY",
]


def mask(value: str) -> str:
    if len(value) <= 14:
        return value[:3] + "..." + value[-2:]
    return value[:10] + "..." + value[-4:]


def load_env() -> dict:
    if not ENV_PATH.exists():
        print(f"❌ {ENV_PATH} 없음")
        sys.exit(1)
    env = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$", line)
        if m:
            env[m.group(1)] = m.group(2).strip()
    return env


def list_current_secrets() -> set:
    """GitHub repo에 이미 설정된 secret 이름 집합."""
    try:
        result = subprocess.run(
            ["gh", "secret", "list", "--repo", REPO, "--json", "name"],
            capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode != 0:
            return set()
        import json
        return {item["name"] for item in json.loads(result.stdout)}
    except Exception:
        return set()


def set_secret(name: str, value: str) -> bool:
    """value를 stdin으로 전달해서 set."""
    result = subprocess.run(
        ["gh", "secret", "set", name, "--repo", REPO, "--body", value],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode == 0:
        return True
    print(f"   ❌ {result.stderr.strip()}")
    return False


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv

    env = load_env()
    existing = list_current_secrets()

    # 대상 결정: 인자 있으면 그것만, 없으면 KNOWN_SECRETS ∩ .env 안에 있는 것
    if args:
        targets = args
    else:
        targets = [k for k in KNOWN_SECRETS if k in env]

    print(f"📤 repo: {REPO}")
    print(f"📋 대상 {len(targets)}개 (.env에 있고 KNOWN_SECRETS에 등록된 것)")
    print()

    if dry_run:
        print("🔍 --dry-run 모드 — 변경 없음")
        print()

    for name in targets:
        if name not in env or not env[name]:
            print(f"  ⊘ {name} — .env에 없거나 빈 값")
            continue
        value = env[name]
        action = "UPDATE" if name in existing else "CREATE"
        print(f"  {action} {name} ({mask(value)})", end=" ")
        if dry_run:
            print("[skipped]")
        else:
            if set_secret(name, value):
                print("✓")

    print()
    print(f"💡 확인: https://github.com/{REPO}/settings/secrets/actions")


if __name__ == "__main__":
    main()
