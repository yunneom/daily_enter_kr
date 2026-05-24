"""
배경 이미지 제공자 — Unsplash 검색으로 기사 컨텍스트와 어울리는 이미지 확보.

[작동]
1. 뉴스마다 Claude가 영문 visual_concept 쿼리 생성 (예: "concert lights stage")
2. Unsplash API로 search → 첫 결과 다운로드
3. 1080x1080 정사각 center-crop
4. make_card 가 이 이미지 위에 블러+오버레이+텍스트 합성

[저작권]
- Unsplash 라이센스: 상업적 사용 가능, attribution 불필요(권장)
- 무거운 블러로 transformative 강화

[비용]
- Unsplash API 무료 티어: 50req/hour, 5000req/month
- 일 9 카드 x 30일 = 270req/월 → 무료 한도 5% 사용

[사용]
- UNSPLASH_ACCESS_KEY 환경변수 설정 필요 (없으면 모든 호출이 None 반환 → 폴백)
- https://unsplash.com/developers 에서 무료 발급
"""

import os
import hashlib
from pathlib import Path
from typing import Optional
import requests


UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"
CACHE_DIR = Path(__file__).parent.parent / ".image_cache"
DOWNLOAD_TIMEOUT = 15
SEARCH_TIMEOUT = 10
MIN_IMAGE_SIDE = 800   # 이보다 작은 이미지는 무시 (1080x1080 카드에 적합 안 함)


def _query_cache_path(query: str) -> Path:
    """동일 쿼리는 같은 이미지를 재사용 (Unsplash API 호출 절약 + 결정론적)."""
    h = hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"{h}.jpg"


def search_and_download(query: str, access_key: str = None) -> Optional[Path]:
    """
    Unsplash 검색 + 첫 결과 다운로드. 캐시 적중 시 API 호출 안 함.

    Returns: 다운로드된 이미지 파일 경로, 실패 시 None.
    """
    if not query:
        return None

    access_key = access_key or os.environ.get("UNSPLASH_ACCESS_KEY")
    if not access_key:
        return None

    cache_path = _query_cache_path(query)
    if cache_path.exists() and cache_path.stat().st_size > 1024:
        return cache_path

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Unsplash search
    try:
        resp = requests.get(
            UNSPLASH_SEARCH_URL,
            params={
                "query": query,
                "per_page": 5,                # 작은 이미지/세로 비율 회피용 약간의 여유
                "orientation": "squarish",     # 정사각/근접 우선
                "content_filter": "high",       # 민감 콘텐츠 차단 (인스타 안전)
            },
            headers={"Authorization": f"Client-ID {access_key}"},
            timeout=SEARCH_TIMEOUT,
        )
        if not resp.ok:
            print(f"  ⚠️  Unsplash search 실패: HTTP {resp.status_code}")
            return None
        results = resp.json().get("results", [])
        if not results:
            return None
    except Exception as e:
        print(f"  ⚠️  Unsplash search 예외: {e}")
        return None

    # 적합한 첫 결과 찾기
    for hit in results:
        urls = hit.get("urls", {})
        width = hit.get("width", 0)
        height = hit.get("height", 0)
        if width < MIN_IMAGE_SIDE or height < MIN_IMAGE_SIDE:
            continue
        download_url = urls.get("regular") or urls.get("full") or urls.get("raw")
        if not download_url:
            continue

        try:
            img_resp = requests.get(download_url, timeout=DOWNLOAD_TIMEOUT)
            if not img_resp.ok or len(img_resp.content) < 1024:
                continue
            cache_path.write_bytes(img_resp.content)
            return cache_path
        except Exception as e:
            print(f"  ⚠️  Unsplash 다운로드 예외: {e}")
            continue

    return None


def clear_old_cache(max_files: int = 500):
    """캐시가 너무 커지면 오래된 파일 제거. 별도 cron으로 호출."""
    if not CACHE_DIR.exists():
        return
    files = sorted(CACHE_DIR.glob("*.jpg"), key=lambda p: p.stat().st_mtime)
    if len(files) > max_files:
        for f in files[: len(files) - max_files]:
            f.unlink(missing_ok=True)
