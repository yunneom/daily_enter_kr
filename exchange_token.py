"""
Instagram 단기 토큰(IGAA, 1시간) → 장기 토큰(60일) 교환

Instagram Business Login의 신버전 API 사용:
  GET https://graph.instagram.com/access_token
    ?grant_type=ig_exchange_token
    &client_secret={APP_SECRET}
    &access_token={short-lived IGAA token}

사용법:
  .env 파일에 다음 값이 있어야 합니다:
    INSTAGRAM_APP_SECRET=... (Meta 콘솔 → Instagram → API setup 의 Instagram 앱 secret)
    INSTAGRAM_ACCESS_TOKEN=IGAA... (단기 토큰)

  실행:
    python exchange_token.py

  결과:
    - 60일 유효한 장기 토큰을 출력
    - .env 파일의 INSTAGRAM_ACCESS_TOKEN을 자동 업데이트

장기 토큰 갱신:
  장기 토큰은 60일 유효하지만, 만료 전 언제든 refresh 가능:
    GET https://graph.instagram.com/refresh_access_token
      ?grant_type=ig_refresh_token
      &access_token={long-lived token}
  이 스크립트에 --refresh 옵션을 주면 갱신만 수행합니다.
"""

import sys
import re
from pathlib import Path
import requests


GRAPH_BASE = "https://graph.instagram.com"
ENV_PATH = Path(__file__).parent / ".env"


def load_env():
    env = {}
    if not ENV_PATH.exists():
        print(f"❌ {ENV_PATH} 파일이 없습니다.")
        sys.exit(1)
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$", line)
        if m:
            env[m.group(1)] = m.group(2).strip()
    return env


def update_env_value(key: str, new_value: str):
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    found = False
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = f"{key}={new_value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={new_value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def exchange_to_long_lived(app_secret: str, short_token: str) -> dict:
    """단기 IGAA 토큰 → 장기 IGAA 토큰 (60일).

    토큰이 이미 장기인 경우 (Meta 콘솔의 'Generate access tokens' 결과는
    이미 장기 토큰임) 'Session key invalid' 에러가 발생한다. 이때는
    자동으로 refresh 시도로 폴백.
    """
    print("[1/2] 단기 IGAA 토큰 → 장기 토큰(60일) 교환 시도...")
    resp = requests.get(
        f"{GRAPH_BASE}/access_token",
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": app_secret,
            "access_token": short_token,
        },
        timeout=15,
    )
    if resp.ok:
        data = resp.json()
        expires = data.get("expires_in", 0)
        print(f"   ✓ 장기 토큰 확보 (유효기간: 약 {expires/86400:.0f}일)")
        return data

    # 실패 처리 — 'Session key invalid' 이면 이미 장기 토큰일 가능성
    err_text = resp.text
    body = {}
    try:
        body = resp.json().get("error", {})
    except Exception:
        pass
    msg = body.get("message", err_text[:300])
    print(f"   ⚠️  교환 실패: {msg}")

    if "Session key invalid" in err_text or body.get("error_subcode") == 2207055:
        print("   → 토큰이 이미 장기일 가능성. refresh 모드로 폴백 시도...")
        return refresh_long_lived(short_token)

    print(f"   ❌ 교환 실패 (응답: {err_text[:300]})")
    sys.exit(1)


def refresh_long_lived(long_token: str) -> dict:
    """장기 토큰을 갱신 (만료 전 언제든 호출 가능, 60일 연장)"""
    print("[갱신] 장기 토큰 갱신 중...")
    resp = requests.get(
        f"{GRAPH_BASE}/refresh_access_token",
        params={
            "grant_type": "ig_refresh_token",
            "access_token": long_token,
        },
        timeout=15,
    )
    if not resp.ok:
        print(f"   ❌ 갱신 실패: HTTP {resp.status_code}")
        print(f"   응답: {resp.text}")
        sys.exit(1)
    data = resp.json()
    expires = data.get("expires_in", 0)
    print(f"   ✓ 갱신됨 (유효기간: 약 {expires/86400:.0f}일)")
    return data


def verify_token(token: str, ig_user_id: str = None):
    """토큰 유효성 확인 + 연결된 IG 사용자 정보 조회"""
    print("[2/2] 토큰 검증 + IG 사용자 정보 조회 중...")
    resp = requests.get(
        f"{GRAPH_BASE}/me",
        params={
            "fields": "user_id,username,account_type",
            "access_token": token,
        },
        timeout=15,
    )
    if not resp.ok:
        print(f"   ⚠️  토큰 검증 실패: {resp.text}")
        return
    info = resp.json()
    print(f"   ✓ 연결된 계정:")
    print(f"     - username: {info.get('username')}")
    print(f"     - account_type: {info.get('account_type')}")
    print(f"     - user_id: {info.get('user_id') or info.get('id')}")


def main():
    refresh_mode = "--refresh" in sys.argv

    env = load_env()
    # IGAA 토큰 교환에는 별도 'Instagram App Secret' 사용 (Facebook APP_SECRET 아님)
    ig_app_secret = env.get("INSTAGRAM_APP_SECRET") or env.get("APP_SECRET")
    current_token = env.get("INSTAGRAM_ACCESS_TOKEN")
    ig_user_id = env.get("INSTAGRAM_USER_ID")

    if not current_token:
        print("❌ .env에 INSTAGRAM_ACCESS_TOKEN 이 없습니다.")
        sys.exit(1)
    if not refresh_mode and not ig_app_secret:
        print("❌ .env에 INSTAGRAM_APP_SECRET 이 없습니다.")
        sys.exit(1)

    print(f"📁 .env 경로: {ENV_PATH}")
    print(f"   현재 토큰: {current_token[:12]}...{current_token[-6:]}")
    print()

    if refresh_mode:
        data = refresh_long_lived(current_token)
    else:
        data = exchange_to_long_lived(ig_app_secret, current_token)

    new_token = data["access_token"]
    verify_token(new_token, ig_user_id)

    print()
    print("=" * 60)
    print("✅ 완료")
    print("=" * 60)
    update_env_value("INSTAGRAM_ACCESS_TOKEN", new_token)
    print(f"💾 .env의 INSTAGRAM_ACCESS_TOKEN 이 갱신되었습니다.")
    print()
    if not refresh_mode:
        print("   이제 'python main.py' 를 실행하면 인스타 자동 게시까지 진행됩니다.")
        print("   60일 후 만료 전에 'python exchange_token.py --refresh' 로 갱신할 수 있습니다.")


if __name__ == "__main__":
    main()
